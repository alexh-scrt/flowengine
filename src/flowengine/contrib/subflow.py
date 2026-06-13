"""SubflowComponent — run a nested flow as a single component.

Composition is essential once agents build non-trivial workers: a parent flow
delegates to a research subflow, a verification subflow, a report subflow. This
component loads another flow (by path or inline) and runs it against a child
context, mapping selected keys in and out.

YAML::

    components:
      - name: literature_review
        type: flowengine.contrib.subflow.SubflowComponent
        config:
          path: ./subflows/literature-review.yaml
          inputs: {query: topic}        # parent 'query' -> child 'topic'
          outputs: [summary, citations] # copy these child keys back to parent
          namespace: lit                # optional: prefix copied outputs

The component derives its :class:`ComponentMeta` from the nested flow's declared
``inputs``/``outputs``, so subflows participate in semantic validation and the
component catalog like any other component.
"""

from __future__ import annotations

import contextvars
from typing import Any, Optional

from flowengine.agent.meta import ComponentMeta, IOFieldSpec
from flowengine.core.component import BaseComponent
from flowengine.core.context import FlowContext
from flowengine.errors import ComponentError, ConfigurationError

# Guards against unbounded recursion (a subflow that includes itself).
_DEPTH: contextvars.ContextVar[int] = contextvars.ContextVar("subflow_depth", default=0)


class SubflowComponent(BaseComponent):
    """Execute a nested flow as a component."""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._sub_config = None
        self._max_depth = 25
        self._input_map: dict[str, str] = {}
        self._output_map: Optional[dict[str, str]] = None
        self._namespace: Optional[str] = None

    def init(self, config: dict[str, Any]) -> None:
        super().init(config)
        from flowengine.config.loader import ConfigLoader

        path = config.get("path")
        inline = config.get("flow") or config.get("config")
        if path:
            self._sub_config = ConfigLoader.load(path)
        elif isinstance(inline, dict) and "components" in inline:
            self._sub_config = ConfigLoader.from_dict(inline)
        else:
            raise ConfigurationError(
                f"SubflowComponent '{self.name}' requires a 'path' to a flow file "
                "or an inline 'flow' mapping."
            )

        self._max_depth = int(config.get("max_depth", 25))
        self._input_map = _as_mapping(config.get("inputs"))
        out = config.get("outputs")
        self._output_map = _as_mapping(out) if out is not None else None
        self._namespace = config.get("namespace")

    def get_meta(self) -> Optional[ComponentMeta]:
        """Derive metadata from the nested flow's declared contract."""
        if self._sub_config is None:
            return None
        cfg = self._sub_config
        return ComponentMeta(
            name=f"subflow:{cfg.name}",
            description=cfg.description or f"Nested flow '{cfg.name}'",
            version=cfg.version,
            inputs={k: IOFieldSpec(**v.model_dump()) for k, v in cfg.inputs.items()},
            outputs={k: IOFieldSpec(**v.model_dump()) for k, v in cfg.outputs.items()},
            tags=["subflow"],
        )

    def process(self, context: FlowContext) -> FlowContext:
        from flowengine.core.engine import FlowEngine

        if self._sub_config is None:
            raise ComponentError(self.name, "SubflowComponent was not initialized.")

        depth = _DEPTH.get()
        if depth >= self._max_depth:
            raise ComponentError(
                self.name,
                f"Subflow recursion exceeded max_depth={self._max_depth}.",
            )

        child = FlowContext()
        # Map inputs from the parent context into the child context.
        if self._input_map:
            for parent_key, child_key in self._input_map.items():
                child.set(child_key, context.get(parent_key))
        else:
            # Default: forward the entire parent data namespace.
            for key, value in context.data.to_dict().items():
                child.set(key, value)

        engine = FlowEngine.from_config(self._sub_config)
        token = _DEPTH.set(depth + 1)
        try:
            result = engine.execute(child)
        finally:
            _DEPTH.reset(token)

        # Map outputs from the child back into the parent.
        produced = result.data.to_dict()
        if self._output_map is not None:
            for child_key, parent_key in self._output_map.items():
                context.set(self._ns(parent_key), produced.get(child_key))
        else:
            for key, value in produced.items():
                context.set(self._ns(key), value)
        return context

    def _ns(self, key: str) -> str:
        return f"{self._namespace}_{key}" if self._namespace else key


def _as_mapping(value: Any) -> dict[str, str]:
    """Normalize a mapping config into a {source: target} dict.

    Accepts a dict (used as-is) or a list of names (identity mapping).
    """
    if value is None:
        return {}
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items()}
    if isinstance(value, list):
        return {str(k): str(k) for k in value}
    raise ConfigurationError(
        f"Subflow input/output mapping must be a dict or list, got {type(value).__name__}"
    )
