"""Tests for the ExecutionPolicy sandbox + risk model."""

import pytest

from flowengine.agent.compiler import FlowCompiler
from flowengine.agent.issues import IssueCode
from flowengine.agent.policy import ExecutionPolicy
from flowengine.config.registry import ComponentRegistry
from flowengine.config.schema import FlowConfig

from .conftest import SearchComponent, ShellComponent, SummarizeComponent


@pytest.fixture
def registry():
    reg = ComponentRegistry()
    reg.register_class("web_search", SearchComponent)
    reg.register_class("llm_summarizer", SummarizeComponent)
    reg.register_class("shell_exec", ShellComponent)
    return reg


def _cfg(component_type, **settings):
    return FlowConfig.model_validate(
        {
            "name": "t",
            "components": [{"name": "c", "type": component_type}],
            "flow": {
                "type": "sequential",
                "settings": settings,
                "steps": [{"component": "c"}],
            },
        }
    )


def test_denied_component(registry):
    policy = ExecutionPolicy(denied_components=["shell_exec"])
    issues = policy.evaluate(_cfg("shell_exec"), registry=registry)
    assert any(i.code == IssueCode.DENIED_COMPONENT for i in issues)


def test_not_allowlisted(registry):
    policy = ExecutionPolicy(allowed_components=["web_search"])
    issues = policy.evaluate(_cfg("shell_exec"), registry=registry)
    assert any(i.code == IssueCode.NOT_ALLOWLISTED for i in issues)


def test_allowlisted_passes(registry):
    policy = ExecutionPolicy(allowed_components=["web_search"])
    issues = policy.evaluate(_cfg("web_search"), registry=registry)
    assert not issues


def test_high_risk_blocked(registry):
    policy = ExecutionPolicy()
    issues = policy.evaluate(_cfg("shell_exec"), registry=registry)
    assert any(i.code == IssueCode.RISK_EXCEEDS_POLICY for i in issues)


def test_high_risk_allowed_when_flag_set(registry):
    policy = ExecutionPolicy(allow_high_risk=True)
    issues = policy.evaluate(_cfg("shell_exec"), registry=registry)
    assert not any(i.code == IssueCode.RISK_EXCEEDS_POLICY for i in issues)


def test_approval_required_by_effect(registry):
    policy = ExecutionPolicy(require_approval_for=["execute_code"])
    issues = policy.evaluate(_cfg("shell_exec"), registry=registry)
    assert any(i.code == IssueCode.APPROVAL_REQUIRED for i in issues)


def test_approved_component_passes(registry):
    policy = ExecutionPolicy(
        require_approval_for=["execute_code"], allow_high_risk=True, approved=["shell_exec"]
    )
    issues = policy.evaluate(_cfg("shell_exec"), registry=registry)
    assert not issues


def test_max_iterations_cap(registry):
    policy = ExecutionPolicy(max_iterations=5)
    issues = policy.evaluate(_cfg("web_search", max_iterations=50), registry=registry)
    cap = [i for i in issues if i.code == IssueCode.RISK_EXCEEDS_POLICY]
    assert cap
    assert cap[0].repair.yaml_patch[0].value == 5


def test_apply_to_config_tightens_settings(registry):
    policy = ExecutionPolicy(max_runtime_seconds=30, max_iterations=3)
    config = _cfg("web_search", timeout_seconds=300.0, max_iterations=10)
    tightened = policy.apply_to_config(config)
    assert tightened.flow.settings.timeout_seconds == 30
    assert tightened.flow.settings.max_iterations == 3
    assert tightened.flow.settings.on_max_iterations == "exit"
    # Original untouched.
    assert config.flow.settings.timeout_seconds == 300.0


def test_max_component_calls_acyclic(registry):
    policy = ExecutionPolicy(max_component_calls=1)
    config = FlowConfig.model_validate(
        {
            "name": "t",
            "components": [
                {"name": "a", "type": "web_search"},
                {"name": "b", "type": "llm_summarizer"},
            ],
            "flow": {
                "type": "sequential",
                "steps": [{"component": "a"}, {"component": "b"}],
            },
        }
    )
    issues = policy.evaluate(config, registry=registry)
    assert any(i.code == IssueCode.RISK_EXCEEDS_POLICY for i in issues)


def test_compiler_integrates_policy(registry):
    yaml_text = """
name: t
components:
  - {name: c, type: shell_exec}
flow:
  type: sequential
  steps:
    - component: c
"""
    policy = ExecutionPolicy(denied_components=["shell_exec"])
    result = FlowCompiler.compile_yaml(yaml_text, registry=registry, policy=policy)
    assert result.valid is False
    assert any(e.code == IssueCode.DENIED_COMPONENT for e in result.errors)
