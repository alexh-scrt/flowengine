"""JSON Schema export for the FlowEngine YAML format.

Agents can use these schemas for *constrained generation* — "produce only YAML
that conforms to this schema". The flow schema is the canonical contract; the
component and graph schemas are convenience subsets.
"""

from __future__ import annotations

from typing import Any, Literal

from flowengine.agent.meta import ComponentMeta
from flowengine.config.schema import ComponentConfig, FlowConfig, FlowDefinition

SchemaKind = Literal["flow", "component", "graph", "component-meta"]

_MODELS = {
    "flow": FlowConfig,
    "component": ComponentConfig,
    "graph": FlowDefinition,
    "component-meta": ComponentMeta,
}


def export_json_schema(kind: SchemaKind = "flow") -> dict[str, Any]:
    """Return the JSON Schema for one document kind.

    Args:
        kind: One of ``flow`` (whole flow), ``component`` (a component entry),
            ``graph`` (graph flow definition), or ``component-meta`` (a
            capability manifest).
    """
    model = _MODELS.get(kind)
    if model is None:
        raise ValueError(
            f"Unknown schema kind '{kind}'. Expected one of {sorted(_MODELS)}."
        )
    schema = model.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema.setdefault("title", f"flowengine-{kind}")
    return schema


def export_all_schemas() -> dict[str, dict[str, Any]]:
    """Return ``{kind: schema}`` for every supported document kind."""
    return {kind: export_json_schema(kind) for kind in _MODELS}  # type: ignore[arg-type]
