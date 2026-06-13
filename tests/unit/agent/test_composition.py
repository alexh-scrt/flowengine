"""Tests for FlowTool (flow-as-tool) and SubflowComponent (nested flows)."""

import pytest

from flowengine.agent.tool import FlowTool
from flowengine.config.loader import ConfigLoader
from flowengine.contrib.subflow import SubflowComponent
from flowengine.core.context import FlowContext

# Importable type paths so FlowEngine.from_config can load + type-validate them.
_SEARCH = "tests.unit.agent.conftest.SearchComponent"
_SUMMARIZE = "tests.unit.agent.conftest.SummarizeComponent"

WORKER_YAML = f"""
name: research-worker
description: Researches a question and returns an answer.
inputs:
  query: {{type: string, required: true}}
outputs:
  answer: {{type: string}}
components:
  - {{name: search, type: {_SEARCH}}}
  - {{name: summarize, type: {_SUMMARIZE}}}
flow:
  type: sequential
  steps:
    - component: search
    - component: summarize
"""


# ── FlowTool ──


def test_tool_schema():
    tool = FlowTool.from_yaml(WORKER_YAML, is_text=True)
    schema = tool.tool_schema()
    assert schema["name"] == "research_worker"
    assert schema["parameters"]["properties"]["query"]["type"] == "string"
    assert schema["parameters"]["required"] == ["query"]
    assert "Researches" in schema["description"]


def test_tool_call_returns_declared_outputs():
    tool = FlowTool.from_yaml(WORKER_YAML, is_text=True)
    result = tool.call(query="what is FlowEngine?")
    assert set(result.keys()) == {"answer"}
    assert result["answer"] == "summary"


def test_tool_run_with_trace():
    tool = FlowTool.from_yaml(WORKER_YAML, is_text=True)
    trace = tool.run_with_trace({"query": "x"})
    assert trace.status == "completed"
    assert trace.outputs == {"answer": "summary"}


def test_tool_name_sanitization():
    config = ConfigLoader.loads(WORKER_YAML.replace("research-worker", "My Cool Flow!"))
    tool = FlowTool.from_config(config)
    assert tool.name == "my_cool_flow"


# ── SubflowComponent ──


def test_subflow_runs_nested_flow(tmp_path):
    sub_yaml = """
name: inner
inputs:
  topic: {type: string}
outputs:
  message: {type: string}
components:
  - name: log
    type: flowengine.contrib.logging.LoggingComponent
    config: {message: "inner ran"}
flow:
  type: sequential
  steps:
    - component: log
"""
    sub = tmp_path / "inner.yaml"
    sub.write_text(sub_yaml)

    comp = SubflowComponent("sub")
    comp.init({"path": str(sub), "inputs": {"q": "topic"}})
    ctx = FlowContext()
    ctx.set("q", "hello")
    comp.process(ctx)
    # Child ran without error; subflow meta derived from declared contract.
    meta = comp.get_meta()
    assert meta is not None
    assert "topic" in meta.inputs
    assert meta.tags == ["subflow"]


def test_subflow_output_namespacing(tmp_path):
    sub_yaml = """
name: inner
outputs:
  result: {type: string}
components:
  - name: log
    type: flowengine.contrib.logging.LoggingComponent
    config: {message: x}
flow:
  type: sequential
  steps:
    - component: log
"""
    sub = tmp_path / "inner.yaml"
    sub.write_text(sub_yaml)
    comp = SubflowComponent("sub")
    comp.init({"path": str(sub), "outputs": {"result": "answer"}, "namespace": "lit"})
    ctx = FlowContext()
    result = comp.process(ctx)
    # Output mapped child 'result' -> parent 'answer', namespaced to 'lit_answer'.
    assert result.has("lit_answer")


def test_subflow_requires_path_or_flow():
    from flowengine.errors import ConfigurationError

    comp = SubflowComponent("sub")
    with pytest.raises(ConfigurationError):
        comp.init({})


def test_subflow_meta_none_before_init():
    comp = SubflowComponent("sub")
    assert comp.get_meta() is None
