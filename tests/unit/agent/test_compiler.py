"""Tests for FlowCompiler.compile_yaml and the CompileResult contract."""

import pytest

from flowengine.agent.compiler import CompileResult, FlowCompiler
from flowengine.agent.issues import IssueCode
from flowengine.config.registry import ComponentRegistry

from .conftest import (
    PlainComponent,
    SearchComponent,
    ShellComponent,
    SummarizeComponent,
)


@pytest.fixture
def registry():
    reg = ComponentRegistry()
    reg.register_class("web_search", SearchComponent)
    reg.register_class("llm_summarizer", SummarizeComponent)
    reg.register_class("shell_exec", ShellComponent)
    reg.register_class("plain", PlainComponent)
    return reg


VALID_GRAPH = """
name: research-worker
version: "1.0"
inputs:
  query:
    type: string
    required: true
outputs:
  answer:
    type: string
components:
  - name: search
    type: web_search
  - name: summarize
    type: llm_summarizer
flow:
  type: graph
  settings:
    max_iterations: 3
  nodes:
    - id: search
      component: search
    - id: summarize
      component: summarize
  edges:
    - source: search
      target: summarize
      port: success
    - source: summarize
      target: search
      port: revise
"""


def test_valid_flow_compiles(registry):
    result = FlowCompiler.compile_yaml(VALID_GRAPH, registry=registry)
    assert isinstance(result, CompileResult)
    assert result.valid is True
    assert result.flow_config is not None
    assert result.flow_config.name == "research-worker"
    assert result.normalized_yaml is not None
    assert not result.errors


def test_yaml_parse_error():
    result = FlowCompiler.compile_yaml("name: [unterminated")
    assert result.valid is False
    assert result.errors[0].code == IssueCode.YAML_PARSE_ERROR


def test_non_mapping_top_level():
    result = FlowCompiler.compile_yaml("- just\n- a list")
    assert result.valid is False
    assert result.errors[0].code == IssueCode.SCHEMA_INVALID


def test_missing_required_field():
    result = FlowCompiler.compile_yaml("version: '1.0'\ncomponents: []\n")
    assert result.valid is False
    codes = {e.code for e in result.errors}
    assert IssueCode.MISSING_FIELD in codes or IssueCode.INVALID_VALUE in codes


def test_unknown_component_with_suggestion(registry):
    yaml_text = """
name: t
components:
  - name: s
    type: web_serch
flow:
  type: sequential
  steps:
    - component: s
"""
    result = FlowCompiler.compile_yaml(yaml_text, registry=registry)
    assert result.valid is False
    unknown = [e for e in result.errors if e.code == IssueCode.UNKNOWN_COMPONENT]
    assert unknown
    assert "web_search" in (unknown[0].suggestion or "")
    # Repair patch points at the type field and proposes the correct value.
    assert unknown[0].repair is not None
    assert unknown[0].repair.yaml_patch[0].value == "web_search"


def test_undeclared_port_is_error(registry):
    yaml_text = """
name: t
components:
  - name: search
    type: web_search
  - name: summarize
    type: llm_summarizer
flow:
  type: graph
  nodes:
    - id: search
      component: search
    - id: summarize
      component: summarize
  edges:
    - source: search
      target: summarize
      port: nonsense
"""
    result = FlowCompiler.compile_yaml(yaml_text, registry=registry)
    assert result.valid is False
    assert any(e.code == IssueCode.UNDECLARED_PORT for e in result.errors)


def test_high_risk_component_warns(registry):
    yaml_text = """
name: t
components:
  - name: sh
    type: shell_exec
flow:
  type: sequential
  steps:
    - component: sh
"""
    result = FlowCompiler.compile_yaml(yaml_text, registry=registry)
    # Risk is a warning, not a hard error — flow still compiles.
    assert result.valid is True
    assert any(w.code == IssueCode.APPROVAL_REQUIRED for w in result.warnings)


def test_to_dict_shape(registry):
    result = FlowCompiler.compile_yaml(VALID_GRAPH, registry=registry)
    d = result.to_dict()
    assert set(d.keys()) == {"valid", "errors", "warnings", "normalized_yaml"}


def test_no_registry_skips_unknown_component_check():
    # Without a registry or known list, symbolic types must not be flagged unknown.
    yaml_text = """
name: t
components:
  - name: s
    type: some_symbolic_thing
flow:
  type: sequential
  steps:
    - component: s
"""
    result = FlowCompiler.compile_yaml(yaml_text)
    assert not any(e.code == IssueCode.UNKNOWN_COMPONENT for e in result.errors)
