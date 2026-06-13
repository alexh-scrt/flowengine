"""FlowTool — expose a whole flow as a callable tool.

A worker flow should itself be callable as a tool by a parent agent. ``FlowTool``
wraps a flow, derives a tool schema from its declared ``inputs``/``outputs``, and
runs it on demand. This is the bridge:

    FlowEngine YAML → executable worker agent → tool callable by a parent agent

Example::

    tool = FlowTool.from_yaml("research-worker.yaml")
    schema = tool.tool_schema()            # feed to an LLM's tool-use API
    result = tool.call(query="...")        # {"answer": ..., "citations": [...]}
"""

from __future__ import annotations

import re
from typing import Any, Optional

from flowengine.config.registry import ComponentRegistry
from flowengine.config.schema import FlowConfig
from flowengine.core.context import FlowContext


def _sanitize_tool_name(name: str) -> str:
    """Turn a human flow name into a tool-call-safe identifier."""
    cleaned = re.sub(r"[^0-9a-zA-Z_]+", "_", name.strip()).strip("_").lower()
    return cleaned or "flow_tool"


class FlowTool:
    """A flow wrapped as a callable, schema-bearing tool."""

    def __init__(
        self,
        config: FlowConfig,
        registry: Optional[ComponentRegistry] = None,
    ) -> None:
        self.config = config
        self._registry = registry

    # ── constructors ──────────────────────────────────────────────────────

    @classmethod
    def from_config(
        cls, config: FlowConfig, registry: Optional[ComponentRegistry] = None
    ) -> "FlowTool":
        return cls(config, registry=registry)

    @classmethod
    def from_yaml(
        cls,
        path_or_text: str,
        registry: Optional[ComponentRegistry] = None,
        is_text: bool = False,
    ) -> "FlowTool":
        """Build a tool from a YAML file path, or from YAML text if ``is_text``."""
        from flowengine.config.loader import ConfigLoader

        config = (
            ConfigLoader.loads(path_or_text)
            if is_text
            else ConfigLoader.load(path_or_text)
        )
        return cls(config, registry=registry)

    # ── tool schema ───────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return _sanitize_tool_name(self.config.name)

    def tool_schema(self) -> dict[str, Any]:
        """Return a JSON tool definition derived from the flow's input contract."""
        properties: dict[str, Any] = {}
        required: list[str] = []
        for key, spec in self.config.inputs.items():
            properties[key] = spec.to_json_schema()
            if spec.required:
                required.append(key)
        parameters: dict[str, Any] = {"type": "object", "properties": properties}
        if required:
            parameters["required"] = required
        return {
            "name": self.name,
            "description": self.config.description or f"Runs the '{self.config.name}' flow.",
            "parameters": parameters,
        }

    # ── invocation ────────────────────────────────────────────────────────

    def call(self, **inputs: Any) -> dict[str, Any]:
        """Run the flow with keyword inputs and return its declared outputs."""
        return self.invoke(inputs)

    def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Run the flow with a dict of inputs and return its outputs.

        Outputs are narrowed to the flow's declared ``outputs`` when present;
        otherwise the full result data is returned.
        """
        from flowengine.core.engine import FlowEngine

        engine = FlowEngine.from_config(self.config, registry=self._registry)
        context = FlowContext()
        for key, value in inputs.items():
            context.set(key, value)
        result = engine.execute(context)
        data = result.data.to_dict()
        if self.config.outputs:
            return {key: data.get(key) for key in self.config.outputs}
        return data

    def run_with_trace(self, inputs: dict[str, Any]):
        """Run the flow and return an :class:`~flowengine.agent.trace.AgentTrace`."""
        from flowengine.agent.trace import AgentTrace
        from flowengine.core.engine import FlowEngine

        engine = FlowEngine.from_config(self.config, registry=self._registry)
        context = FlowContext()
        for key, value in inputs.items():
            context.set(key, value)
        result = engine.execute(context)
        return AgentTrace.from_context(result, self.config)
