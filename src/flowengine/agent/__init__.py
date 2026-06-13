"""Agent-native API for FlowEngine.

This package turns FlowEngine YAML into an *Agent Workflow IR*: a constrained
language that AI agents can generate, validate, run, observe, and repair. See
``design/v0.5.0_agent_native.md`` for the full design.

Public surface (Phase 1 — Foundation):

* :class:`ComponentMeta`, :class:`PortSpec`, :class:`IOFieldSpec` — capability manifests.
* :class:`FlowIssue`, :class:`RepairSuggestion`, :class:`JsonPatchOp`, :class:`IssueCode`
  — machine-readable validation feedback.
* :func:`validate_semantics` — checks beyond schema (ports, reachability, contract, risk).
* :class:`FlowCompiler`, :class:`CompileResult` — the generate→validate→repair entry point.

Note: ``meta`` and ``issues`` are imported eagerly (they are lightweight and are
imported by ``config.schema``). ``compiler`` and ``semantic`` are imported lazily
via module ``__getattr__`` to avoid an import cycle with ``config.schema``.
"""

from typing import TYPE_CHECKING, Any

# Lightweight, dependency-free models — safe to import eagerly. These are also
# imported by flowengine.config.schema, so they must not pull in config.* here.
from flowengine.agent.issues import (
    FlowIssue,
    IssueCode,
    JsonPatchOp,
    RepairSuggestion,
    Severity,
)
from flowengine.agent.meta import (
    KNOWN_EFFECTS,
    ComponentMeta,
    IOFieldSpec,
    PortSpec,
    RiskLevel,
)

if TYPE_CHECKING:  # for type-checkers / IDEs only
    from flowengine.agent.catalog import build_catalog, catalog_from_classes
    from flowengine.agent.compiler import CompileResult, FlowCompiler
    from flowengine.agent.normalize import normalize_config, normalize_yaml
    from flowengine.agent.patch import apply_patch
    from flowengine.agent.plan import Branch, FlowPlan, explain
    from flowengine.agent.schema_export import export_all_schemas, export_json_schema
    from flowengine.agent.semantic import (
        build_meta_map,
        resolve_component_meta,
        validate_semantics,
    )
    from flowengine.agent.policy import ExecutionPolicy
    from flowengine.agent.replay import (
        InMemoryRunStore,
        RunRecord,
        RunStore,
        replay,
    )
    from flowengine.agent.templates import get_template, list_templates
    from flowengine.agent.tool import FlowTool
    from flowengine.agent.trace import AgentTrace, StepTrace

# Names resolved lazily to break the config.schema <-> agent import cycle.
_LAZY = {
    "ExecutionPolicy": "flowengine.agent.policy",
    "FlowTool": "flowengine.agent.tool",
    "RunRecord": "flowengine.agent.replay",
    "RunStore": "flowengine.agent.replay",
    "InMemoryRunStore": "flowengine.agent.replay",
    "replay": "flowengine.agent.replay",
    "list_templates": "flowengine.agent.templates",
    "get_template": "flowengine.agent.templates",
    "FlowCompiler": "flowengine.agent.compiler",
    "CompileResult": "flowengine.agent.compiler",
    "validate_semantics": "flowengine.agent.semantic",
    "resolve_component_meta": "flowengine.agent.semantic",
    "build_meta_map": "flowengine.agent.semantic",
    "explain": "flowengine.agent.plan",
    "FlowPlan": "flowengine.agent.plan",
    "Branch": "flowengine.agent.plan",
    "AgentTrace": "flowengine.agent.trace",
    "StepTrace": "flowengine.agent.trace",
    "normalize_yaml": "flowengine.agent.normalize",
    "normalize_config": "flowengine.agent.normalize",
    "build_catalog": "flowengine.agent.catalog",
    "catalog_from_classes": "flowengine.agent.catalog",
    "export_json_schema": "flowengine.agent.schema_export",
    "export_all_schemas": "flowengine.agent.schema_export",
    "apply_patch": "flowengine.agent.patch",
}


def __getattr__(name: str) -> Any:
    module_path = _LAZY.get(name)
    if module_path is None:
        raise AttributeError(f"module 'flowengine.agent' has no attribute '{name}'")
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, name)


__all__ = [
    # meta
    "ComponentMeta",
    "IOFieldSpec",
    "PortSpec",
    "RiskLevel",
    "KNOWN_EFFECTS",
    # issues
    "FlowIssue",
    "IssueCode",
    "RepairSuggestion",
    "JsonPatchOp",
    "Severity",
    # semantic (lazy)
    "validate_semantics",
    "resolve_component_meta",
    "build_meta_map",
    # compiler (lazy)
    "FlowCompiler",
    "CompileResult",
    # plan / trace / normalize / catalog / schema / patch (lazy)
    "explain",
    "FlowPlan",
    "Branch",
    "AgentTrace",
    "StepTrace",
    "normalize_yaml",
    "normalize_config",
    "build_catalog",
    "catalog_from_classes",
    "export_json_schema",
    "export_all_schemas",
    "apply_patch",
    # policy (lazy)
    "ExecutionPolicy",
    # tool (lazy)
    "FlowTool",
    # replay (lazy)
    "RunRecord",
    "RunStore",
    "InMemoryRunStore",
    "replay",
    # templates (lazy)
    "list_templates",
    "get_template",
]
