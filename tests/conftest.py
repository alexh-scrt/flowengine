"""Pytest fixtures for FlowEngine tests."""

import pytest

from flowengine import BaseComponent, FlowContext


class EchoComponent(BaseComponent):
    """Simple test component that echoes input to output."""

    def process(self, context: FlowContext) -> FlowContext:
        message = context.get("input_message", "default")
        context.set("output_message", f"Echo: {message}")
        return context


class FailingComponent(BaseComponent):
    """Test component that always fails."""

    def process(self, context: FlowContext) -> FlowContext:
        raise RuntimeError("Intentional failure")


class CounterComponent(BaseComponent):
    """Test component that increments a counter."""

    def process(self, context: FlowContext) -> FlowContext:
        count = context.get("count", 0)
        context.set("count", count + 1)
        return context


class ConfigurableComponent(BaseComponent):
    """Test component with configuration validation."""

    def init(self, config: dict) -> None:
        super().init(config)
        self.multiplier = config.get("multiplier", 1)
        self.required_field = config.get("required_field")

    def validate_config(self) -> list[str]:
        errors = super().validate_config()
        if self.required_field is None:
            errors.append("required_field is required")
        return errors

    def process(self, context: FlowContext) -> FlowContext:
        value = context.get("value", 0)
        context.set("result", value * self.multiplier)
        return context


@pytest.fixture
def flow_context() -> FlowContext:
    """Create a fresh FlowContext for testing."""
    return FlowContext()


@pytest.fixture
def echo_component() -> EchoComponent:
    """Create an EchoComponent for testing."""
    component = EchoComponent("echo")
    component.init({})
    return component


@pytest.fixture
def failing_component() -> FailingComponent:
    """Create a FailingComponent for testing."""
    component = FailingComponent("failing")
    component.init({})
    return component


@pytest.fixture
def counter_component() -> CounterComponent:
    """Create a CounterComponent for testing."""
    component = CounterComponent("counter")
    component.init({})
    return component


@pytest.fixture
def simple_flow_yaml() -> str:
    """Simple flow configuration YAML for testing."""
    return """
name: "Test Flow"
version: "1.0"
description: "A simple test flow"

components:
  - name: echo
    type: tests.conftest.EchoComponent
    config: {}

flow:
  type: sequential
  settings:
    fail_fast: true
    timeout_seconds: 60
  steps:
    - component: echo
      description: "Echo the input"
"""


@pytest.fixture
def conditional_flow_yaml() -> str:
    """Conditional flow configuration YAML for testing."""
    return """
name: "Conditional Flow"
version: "1.0"

components:
  - name: counter
    type: tests.conftest.CounterComponent
    config: {}
  - name: echo
    type: tests.conftest.EchoComponent
    config: {}

flow:
  type: conditional
  steps:
    - component: counter
      description: "Increment counter"
    - component: echo
      description: "Echo if count > 0"
      condition: "context.data.count > 0"
"""
