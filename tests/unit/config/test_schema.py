"""Tests for FlowEngine config schema module."""

import pytest
from pydantic import ValidationError

from flowengine.config.schema import (
    ComponentConfig,
    FlowConfig,
    FlowDefinition,
    FlowSettings,
    StepConfig,
)


class TestComponentConfig:
    """Tests for ComponentConfig model."""

    def test_valid_config(self) -> None:
        """Test valid component configuration."""
        config = ComponentConfig(
            name="test_component",
            type="myapp.TestComponent",
            config={"key": "value"},
        )

        assert config.name == "test_component"
        assert config.type == "myapp.TestComponent"
        assert config.config == {"key": "value"}

    def test_minimal_config(self) -> None:
        """Test minimal configuration (required fields only)."""
        config = ComponentConfig(
            name="test",
            type="myapp.Test",
        )

        assert config.name == "test"
        assert config.config == {}

    def test_missing_name_raises(self) -> None:
        """Test missing name raises validation error."""
        with pytest.raises(ValidationError):
            ComponentConfig(type="myapp.Test")  # type: ignore

    def test_missing_type_raises(self) -> None:
        """Test missing type raises validation error."""
        with pytest.raises(ValidationError):
            ComponentConfig(name="test")  # type: ignore


class TestFlowSettings:
    """Tests for FlowSettings model."""

    def test_defaults(self) -> None:
        """Test default values."""
        settings = FlowSettings()

        assert settings.fail_fast is True
        assert settings.timeout_seconds == 300.0

    def test_custom_values(self) -> None:
        """Test custom values."""
        settings = FlowSettings(
            fail_fast=False,
            timeout_seconds=60.0,
        )

        assert settings.fail_fast is False
        assert settings.timeout_seconds == 60.0

    def test_timeout_must_be_positive(self) -> None:
        """Test timeout must be positive."""
        with pytest.raises(ValidationError):
            FlowSettings(timeout_seconds=0)

        with pytest.raises(ValidationError):
            FlowSettings(timeout_seconds=-1)


class TestStepConfig:
    """Tests for StepConfig model."""

    def test_minimal_step(self) -> None:
        """Test minimal step configuration."""
        step = StepConfig(component="my_component")

        assert step.component == "my_component"
        assert step.description is None
        assert step.condition is None
        assert step.on_error == "fail"

    def test_full_step(self) -> None:
        """Test full step configuration."""
        step = StepConfig(
            component="my_component",
            description="Process data",
            condition="context.data.ready == True",
            on_error="skip",
        )

        assert step.component == "my_component"
        assert step.description == "Process data"
        assert step.condition == "context.data.ready == True"
        assert step.on_error == "skip"

    def test_on_error_values(self) -> None:
        """Test valid on_error values."""
        for value in ["fail", "skip", "continue"]:
            step = StepConfig(component="test", on_error=value)  # type: ignore
            assert step.on_error == value

    def test_invalid_on_error(self) -> None:
        """Test invalid on_error raises error."""
        with pytest.raises(ValidationError):
            StepConfig(component="test", on_error="invalid")  # type: ignore


class TestFlowDefinition:
    """Tests for FlowDefinition model."""

    def test_minimal_definition(self) -> None:
        """Test minimal flow definition."""
        flow = FlowDefinition(
            steps=[StepConfig(component="test")],
        )

        assert flow.type == "sequential"
        assert flow.settings.fail_fast is True
        assert len(flow.steps) == 1

    def test_conditional_type(self) -> None:
        """Test conditional flow type."""
        flow = FlowDefinition(
            type="conditional",
            steps=[StepConfig(component="test")],
        )

        assert flow.type == "conditional"

    def test_custom_settings(self) -> None:
        """Test custom settings."""
        flow = FlowDefinition(
            settings=FlowSettings(fail_fast=False, timeout_seconds=120),
            steps=[StepConfig(component="test")],
        )

        assert flow.settings.fail_fast is False
        assert flow.settings.timeout_seconds == 120

    def test_multiple_steps(self) -> None:
        """Test multiple steps."""
        flow = FlowDefinition(
            steps=[
                StepConfig(component="step1"),
                StepConfig(component="step2"),
                StepConfig(component="step3"),
            ],
        )

        assert len(flow.steps) == 3

    def test_empty_steps_raises(self) -> None:
        """Test empty steps raises error."""
        with pytest.raises(ValidationError):
            FlowDefinition(steps=[])


class TestFlowConfig:
    """Tests for FlowConfig model."""

    def test_minimal_config(self) -> None:
        """Test minimal flow configuration."""
        config = FlowConfig(
            name="Test Flow",
            components=[
                ComponentConfig(name="test", type="myapp.Test"),
            ],
            flow=FlowDefinition(
                steps=[StepConfig(component="test")],
            ),
        )

        assert config.name == "Test Flow"
        assert config.version == "1.0"
        assert len(config.components) == 1
        assert len(config.steps) == 1

    def test_full_config(self) -> None:
        """Test full flow configuration."""
        config = FlowConfig(
            name="Full Flow",
            version="2.0",
            description="A comprehensive flow",
            components=[
                ComponentConfig(name="comp1", type="myapp.Comp1"),
                ComponentConfig(name="comp2", type="myapp.Comp2"),
            ],
            flow=FlowDefinition(
                type="conditional",
                settings=FlowSettings(fail_fast=False),
                steps=[
                    StepConfig(component="comp1"),
                    StepConfig(component="comp2", condition="context.data.x > 0"),
                ],
            ),
        )

        assert config.name == "Full Flow"
        assert config.version == "2.0"
        assert config.description == "A comprehensive flow"
        assert len(config.components) == 2

    def test_unique_component_names(self) -> None:
        """Test component names must be unique."""
        with pytest.raises(ValidationError, match="[Dd]uplicate"):
            FlowConfig(
                name="Test",
                components=[
                    ComponentConfig(name="same", type="myapp.Test"),
                    ComponentConfig(name="same", type="myapp.Test2"),
                ],
                flow=FlowDefinition(steps=[StepConfig(component="same")]),
            )

    def test_step_references_valid_component(self) -> None:
        """Test steps must reference defined components."""
        with pytest.raises(ValidationError, match="undefined component"):
            FlowConfig(
                name="Test",
                components=[
                    ComponentConfig(name="comp1", type="myapp.Test"),
                ],
                flow=FlowDefinition(
                    steps=[StepConfig(component="nonexistent")],
                ),
            )

    def test_settings_shortcut(self) -> None:
        """Test settings property shortcut."""
        config = FlowConfig(
            name="Test",
            components=[ComponentConfig(name="test", type="myapp.Test")],
            flow=FlowDefinition(
                settings=FlowSettings(timeout_seconds=60),
                steps=[StepConfig(component="test")],
            ),
        )

        assert config.settings.timeout_seconds == 60

    def test_steps_shortcut(self) -> None:
        """Test steps property shortcut."""
        config = FlowConfig(
            name="Test",
            components=[ComponentConfig(name="test", type="myapp.Test")],
            flow=FlowDefinition(
                steps=[
                    StepConfig(component="test"),
                ],
            ),
        )

        assert len(config.steps) == 1
        assert config.steps[0].component == "test"

    def test_get_component_config(self) -> None:
        """Test get_component_config method."""
        config = FlowConfig(
            name="Test",
            components=[
                ComponentConfig(name="comp1", type="myapp.Test1", config={"key": "value1"}),
                ComponentConfig(name="comp2", type="myapp.Test2", config={"key": "value2"}),
            ],
            flow=FlowDefinition(
                steps=[StepConfig(component="comp1")],
            ),
        )

        comp1 = config.get_component_config("comp1")
        assert comp1 is not None
        assert comp1.config == {"key": "value1"}

        comp2 = config.get_component_config("comp2")
        assert comp2 is not None
        assert comp2.config == {"key": "value2"}

        missing = config.get_component_config("nonexistent")
        assert missing is None
