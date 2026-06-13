"""Tests for Phase 2 tooling: plan, trace, normalize, catalog, schema, patch."""

import pytest

from flowengine.agent.catalog import build_catalog
from flowengine.agent.normalize import normalize_yaml
from flowengine.agent.patch import JsonPatchError, apply_patch
from flowengine.agent.plan import explain
from flowengine.agent.schema_export import export_all_schemas, export_json_schema
from flowengine.agent.trace import AgentTrace
from flowengine.config.loader import ConfigLoader
from flowengine.config.registry import ComponentRegistry
from flowengine.config.schema import FlowConfig
from flowengine.core.context import FlowContext
from flowengine.core.engine import FlowEngine

from .conftest import SearchComponent, SummarizeComponent


@pytest.fixture
def registry():
    reg = ComponentRegistry()
    reg.register_class("web_search", SearchComponent)
    reg.register_class("llm_summarizer", SummarizeComponent)
    return reg


GRAPH_YAML = """
name: research
inputs:
  query: {type: string, required: true}
outputs:
  answer: {type: string}
components:
  - {name: search, type: web_search}
  - {name: summarize, type: llm_summarizer}
flow:
  type: graph
  settings: {max_iterations: 3}
  nodes:
    - {id: search, component: search}
    - {id: summarize, component: summarize}
  edges:
    - {source: search, target: summarize, port: success}
    - {source: summarize, target: search, port: revise}
"""


# ── plan ──


def test_explain_graph(registry):
    config = ConfigLoader.loads(GRAPH_YAML)
    plan = explain(config, registry=registry)
    assert plan.flow_type == "graph"
    assert plan.possible_cycles is True
    assert plan.max_iterations == 3
    assert "search" in plan.execution_order
    assert plan.context_inputs == ["query"]
    assert plan.context_outputs == ["answer"]
    ports = {(b.source, b.port, b.target) for b in plan.branches}
    assert ("search", "success", "summarize") in ports


def test_explain_sequential_derives_io_from_meta(registry):
    config = FlowConfig.model_validate(
        {
            "name": "t",
            "components": [
                {"name": "search", "type": "web_search"},
                {"name": "summarize", "type": "llm_summarizer"},
            ],
            "flow": {
                "type": "sequential",
                "steps": [{"component": "search"}, {"component": "summarize"}],
            },
        }
    )
    plan = explain(config, registry=registry)
    # search consumes query (no producer) -> an input; search_results is produced.
    assert "query" in plan.context_inputs
    assert "search_results" not in plan.context_inputs
    assert set(plan.context_outputs) == {"search_results", "answer"}


# ── trace ──


def test_agent_trace_from_run(registry):
    config = ConfigLoader.loads(GRAPH_YAML)
    components = {
        "search": SearchComponent("search"),
        "summarize": SummarizeComponent("summarize"),
    }
    engine = FlowEngine(config, components, validate_types=False)
    result = engine.execute(FlowContext())
    trace = AgentTrace.from_context(result, config)
    assert trace.status == "completed"
    assert trace.run_id
    # Outputs narrowed to declared contract keys.
    assert set(trace.outputs.keys()) == {"answer"}
    assert any(s.component == "search" for s in trace.steps)


# ── normalize ──


def test_normalize_is_idempotent():
    once = normalize_yaml(GRAPH_YAML)
    twice = normalize_yaml(once)
    assert once == twice


def test_normalize_orders_top_level_keys():
    out = normalize_yaml(GRAPH_YAML)
    lines = [ln for ln in out.splitlines() if ln and not ln.startswith(" ")]
    keys = [ln.split(":")[0] for ln in lines]
    assert keys[0] == "name"
    assert keys.index("components") < keys.index("flow")


# ── catalog ──


def test_build_catalog(registry):
    catalog = build_catalog(registry)
    by_type = {e["type"]: e for e in catalog}
    assert by_type["web_search"]["outputs"] == {"search_results": {"type": "array"}}
    assert by_type["web_search"]["safe_for_agents"] is True
    assert by_type["llm_summarizer"]["requires_llm"] is True


# ── schema export ──


def test_export_json_schema_kinds():
    for kind in ("flow", "component", "graph", "component-meta"):
        schema = export_json_schema(kind)
        assert "$schema" in schema
        assert "properties" in schema


def test_export_all_schemas():
    alls = export_all_schemas()
    assert set(alls) == {"flow", "component", "graph", "component-meta"}


def test_export_json_schema_unknown_kind():
    with pytest.raises(ValueError):
        export_json_schema("nope")  # type: ignore[arg-type]


# ── patch ──


def test_apply_patch_replace():
    doc = {"components": [{"type": "web_serch"}]}
    patched = apply_patch(
        doc, [{"op": "replace", "path": "/components/0/type", "value": "web_search"}]
    )
    assert patched["components"][0]["type"] == "web_search"
    # Original untouched.
    assert doc["components"][0]["type"] == "web_serch"


def test_apply_patch_add_and_remove():
    doc = {"flow": {"settings": {}}}
    doc = apply_patch(
        doc, [{"op": "add", "path": "/flow/settings/max_iterations", "value": 5}]
    )
    assert doc["flow"]["settings"]["max_iterations"] == 5
    doc = apply_patch(doc, [{"op": "remove", "path": "/flow/settings/max_iterations"}])
    assert "max_iterations" not in doc["flow"]["settings"]


def test_apply_patch_array_append():
    doc = {"items": [1, 2]}
    doc = apply_patch(doc, [{"op": "add", "path": "/items/-", "value": 3}])
    assert doc["items"] == [1, 2, 3]


def test_apply_patch_invalid_pointer():
    with pytest.raises(JsonPatchError):
        apply_patch({}, [{"op": "add", "path": "nopointer", "value": 1}])
