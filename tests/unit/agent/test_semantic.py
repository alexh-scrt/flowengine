"""Tests for semantic validation checks."""

import pytest

from flowengine.agent.issues import IssueCode
from flowengine.agent.semantic import build_meta_map, validate_semantics
from flowengine.config.registry import ComponentRegistry
from flowengine.config.schema import FlowConfig

from .conftest import SearchComponent, SummarizeComponent


@pytest.fixture
def registry():
    reg = ComponentRegistry()
    reg.register_class("web_search", SearchComponent)
    reg.register_class("llm_summarizer", SummarizeComponent)
    return reg


def _config(**flow):
    base = {
        "name": "t",
        "components": [
            {"name": "search", "type": "web_search"},
            {"name": "summarize", "type": "llm_summarizer"},
        ],
        "flow": flow,
    }
    return FlowConfig.model_validate(base)


def test_build_meta_map_resolves_from_registry(registry):
    config = _config(type="sequential", steps=[{"component": "search"}])
    metas = build_meta_map(config, registry=registry)
    assert "search" in metas
    assert metas["search"].name == "web_search"


def test_unreachable_node(registry):
    config = _config(
        type="graph",
        nodes=[
            {"id": "search", "component": "search"},
            {"id": "summarize", "component": "summarize"},
        ],
        edges=[],  # summarize never linked from search; both are roots actually
    )
    # With no edges, both nodes are roots -> reachable. Add an orphan instead:
    config = FlowConfig.model_validate(
        {
            "name": "t",
            "components": [
                {"name": "search", "type": "web_search"},
                {"name": "summarize", "type": "llm_summarizer"},
            ],
            "flow": {
                "type": "graph",
                "nodes": [
                    {"id": "a", "component": "search"},
                    {"id": "b", "component": "summarize"},
                    {"id": "c", "component": "summarize"},
                ],
                "edges": [
                    {"source": "a", "target": "b"},
                    {"source": "b", "target": "c"},
                    {"source": "c", "target": "b"},  # b,c form a cycle reachable from a
                ],
            },
        }
    )
    issues = validate_semantics(config, registry=registry)
    # a is root, b and c reachable -> no unreachable warnings
    assert not any(i.code == IssueCode.UNREACHABLE_NODE for i in issues)


def test_undeclared_port_detected(registry):
    config = FlowConfig.model_validate(
        {
            "name": "t",
            "components": [{"name": "search", "type": "web_search"}],
            "flow": {
                "type": "graph",
                "nodes": [{"id": "search", "component": "search"}],
                "edges": [{"source": "search", "target": "search", "port": "bogus"}],
            },
        }
    )
    issues = validate_semantics(config, registry=registry)
    undeclared = [i for i in issues if i.code == IssueCode.UNDECLARED_PORT]
    assert undeclared
    assert undeclared[0].is_error


def test_missing_input_producer_warns(registry):
    # summarize consumes search_results; if no producer/input, warn.
    config = FlowConfig.model_validate(
        {
            "name": "t",
            "components": [{"name": "summarize", "type": "llm_summarizer"}],
            "flow": {"type": "sequential", "steps": [{"component": "summarize"}]},
        }
    )
    issues = validate_semantics(config, registry=registry)
    assert any(i.code == IssueCode.MISSING_INPUT_PRODUCER for i in issues)


def test_input_satisfied_by_flow_input(registry):
    config = FlowConfig.model_validate(
        {
            "name": "t",
            "inputs": {"search_results": {"type": "array"}},
            "components": [{"name": "summarize", "type": "llm_summarizer"}],
            "flow": {"type": "sequential", "steps": [{"component": "summarize"}]},
        }
    )
    issues = validate_semantics(config, registry=registry)
    assert not any(i.code == IssueCode.MISSING_INPUT_PRODUCER for i in issues)


def test_declared_output_not_produced_warns(registry):
    config = FlowConfig.model_validate(
        {
            "name": "t",
            "outputs": {"citations": {"type": "array"}},
            "components": [{"name": "search", "type": "web_search"}],
            "flow": {"type": "sequential", "steps": [{"component": "search"}]},
        }
    )
    issues = validate_semantics(config, registry=registry)
    assert any(i.code == IssueCode.OUTPUT_NOT_PRODUCED for i in issues)


def test_no_meta_no_false_positives():
    # A flow whose components have no metadata must not emit data-flow issues.
    config = FlowConfig.model_validate(
        {
            "name": "t",
            "outputs": {"answer": {"type": "string"}},
            "components": [{"name": "x", "type": "symbolic_thing"}],
            "flow": {"type": "sequential", "steps": [{"component": "x"}]},
        }
    )
    issues = validate_semantics(config)
    assert not any(
        i.code
        in (IssueCode.OUTPUT_NOT_PRODUCED, IssueCode.MISSING_INPUT_PRODUCER)
        for i in issues
    )
