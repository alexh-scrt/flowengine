"""Component capability catalog.

A machine-readable listing of the building blocks an agent may compose. Each
entry is derived from a component's :class:`~flowengine.agent.meta.ComponentMeta`
and tells the agent what the component consumes, produces, which ports it exposes,
and how risky/costly it is. This is where NeuroCore skills and FlowEngine
components meet (``flowengine components --json``).
"""

from __future__ import annotations

from typing import Any, Optional

from flowengine.agent.meta import ComponentMeta
from flowengine.config.registry import ComponentRegistry


def _entry_for(type_name: str, component_class: type) -> dict[str, Any]:
    """Build one catalog entry for a registered component class."""
    meta: Optional[ComponentMeta] = getattr(component_class, "meta", None)
    if not isinstance(meta, ComponentMeta):
        # Try a dynamically-derived meta (e.g. NeuroCore skills).
        try:
            probed = component_class("__catalog_probe__").get_meta()
            if isinstance(probed, ComponentMeta):
                meta = probed
        except Exception:
            meta = None

    if isinstance(meta, ComponentMeta):
        entry = meta.to_catalog_entry()
        entry["type"] = type_name
        return entry

    return {
        "type": type_name,
        "name": type_name,
        "description": "",
        "inputs": {},
        "outputs": {},
        "ports": [],
        "tags": [],
        "cost": None,
        "risk_level": "low",
        "effects": [],
        "requires_approval": False,
        "requires_llm": False,
        "safe_for_agents": True,
        "has_metadata": False,
    }


def build_catalog(registry: ComponentRegistry) -> list[dict[str, Any]]:
    """Build the full component catalog from a registry, sorted by type name."""
    entries = [
        _entry_for(name, cls)
        for name, cls in sorted(registry._classes.items())
    ]
    return entries


def catalog_from_classes(
    classes: dict[str, type],
) -> list[dict[str, Any]]:
    """Build a catalog from an explicit ``{type_name: class}`` mapping."""
    return [_entry_for(name, cls) for name, cls in sorted(classes.items())]
