"""Tests for FlowEngine engine module."""

import pytest

from flowengine import (
    BaseComponent,
    ComponentError,
    ConfigLoader,
    FlowConfig,
    FlowContext,
    FlowEngine,
    FlowExecutionError,
)


class IncrementComponent(BaseComponent):
    """Component that increments a counter."""

    def process(self, context: FlowContext) -> FlowContext:
        count = context.get("count", 0)
        context.set("count", count + 1)
        return context


class FailingComponent(BaseComponent):
    """Component that always fails."""

    def process(self, context: FlowContext) -> FlowContext:
        raise RuntimeError("Intentional failure")


class SetupTeardownComponent(BaseComponent):
    """Component that tracks setup/teardown calls."""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.setup_called = False
        self.teardown_called = False

    def setup(self, context: FlowContext) -> None:
        self.setup_called = True
        context.set(f"{self.name}_setup", True)

    def process(self, context: FlowContext) -> FlowContext:
        context.set(f"{self.name}_process", True)
        return context

    def teardown(self, context: FlowContext) -> None:
        self.teardown_called = True
        context.set(f"{self.name}_teardown", True)


class TestFlowEngine:
    """Tests for FlowEngine class."""

    @pytest.fixture
    def simple_config(self) -> FlowConfig:
        """Create a simple flow configuration."""
        return ConfigLoader.from_dict(
            {
                "name": "Simple Flow",
                "components": [
                    {"name": "inc", "type": "test.IncrementComponent", "config": {}},
                ],
                "flow": {
                    "steps": [{"component": "inc"}],
                },
            }
        )

    @pytest.fixture
    def multi_step_config(self) -> FlowConfig:
        """Create a multi-step flow configuration."""
        return ConfigLoader.from_dict(
            {
                "name": "Multi-Step Flow",
                "components": [
                    {"name": "inc1", "type": "test.IncrementComponent", "config": {}},
                    {"name": "inc2", "type": "test.IncrementComponent", "config": {}},
                    {"name": "inc3", "type": "test.IncrementComponent", "config": {}},
                ],
                "flow": {
                    "steps": [
                        {"component": "inc1"},
                        {"component": "inc2"},
                        {"component": "inc3"},
                    ],
                },
            }
        )

    @pytest.fixture
    def conditional_config(self) -> FlowConfig:
        """Create a conditional flow configuration."""
        return ConfigLoader.from_dict(
            {
                "name": "Conditional Flow",
                "components": [
                    {"name": "inc", "type": "test.IncrementComponent", "config": {}},
                ],
                "flow": {
                    "steps": [
                        {
                            "component": "inc",
                            "condition": "context.data.run_increment == True",
                        },
                    ],
                },
            }
        )

    def test_init(self, simple_config: FlowConfig) -> None:
        """Test engine initialization."""
        components = {"inc": IncrementComponent("inc")}
        engine = FlowEngine(simple_config, components)

        assert engine.config == simple_config
        assert engine.fail_fast is True
        assert engine.timeout == 300.0

    def test_init_missing_component(self, simple_config: FlowConfig) -> None:
        """Test error when referenced component is missing."""
        with pytest.raises(FlowExecutionError, match="Component not found"):
            FlowEngine(simple_config, {})

    def test_execute_simple(self, simple_config: FlowConfig) -> None:
        """Test simple flow execution."""
        components = {"inc": IncrementComponent("inc")}
        engine = FlowEngine(simple_config, components)

        context = FlowContext()
        result = engine.execute(context)

        assert result.get("count") == 1
        assert result.metadata.completed_at is not None
        assert "inc" in result.metadata.component_timings

    def test_execute_multi_step(self, multi_step_config: FlowConfig) -> None:
        """Test multi-step flow execution."""
        components = {
            "inc1": IncrementComponent("inc1"),
            "inc2": IncrementComponent("inc2"),
            "inc3": IncrementComponent("inc3"),
        }
        engine = FlowEngine(multi_step_config, components)

        result = engine.execute()

        assert result.get("count") == 3
        assert len(result.metadata.component_timings) == 3

    def test_execute_with_input_data(self, simple_config: FlowConfig) -> None:
        """Test execution with input data."""
        components = {"inc": IncrementComponent("inc")}
        engine = FlowEngine(simple_config, components)

        result = engine.execute(input_data={"initial": "data"})

        assert result.input == {"initial": "data"}

    def test_execute_conditional_true(self, conditional_config: FlowConfig) -> None:
        """Test conditional execution when condition is true."""
        components = {"inc": IncrementComponent("inc")}
        engine = FlowEngine(conditional_config, components)

        context = FlowContext()
        context.set("run_increment", True)
        result = engine.execute(context)

        assert result.get("count") == 1
        assert "inc" not in result.metadata.skipped_components

    def test_execute_conditional_false(self, conditional_config: FlowConfig) -> None:
        """Test conditional execution when condition is false."""
        components = {"inc": IncrementComponent("inc")}
        engine = FlowEngine(conditional_config, components)

        context = FlowContext()
        context.set("run_increment", False)
        result = engine.execute(context)

        assert result.get("count") is None
        assert "inc" in result.metadata.skipped_components

    def test_execute_error_fail_fast(self) -> None:
        """Test error handling with fail_fast=True."""
        config = ConfigLoader.from_dict(
            {
                "name": "Failing Flow",
                "components": [
                    {"name": "fail", "type": "test.FailingComponent", "config": {}},
                ],
                "flow": {
                    "settings": {"fail_fast": True},
                    "steps": [{"component": "fail"}],
                },
            }
        )

        components = {"fail": FailingComponent("fail")}
        engine = FlowEngine(config, components)

        with pytest.raises(ComponentError, match="Intentional failure"):
            engine.execute()

    def test_execute_error_continue(self) -> None:
        """Test error handling with on_error=continue."""
        config = ConfigLoader.from_dict(
            {
                "name": "Continue Flow",
                "components": [
                    {"name": "fail", "type": "test.FailingComponent", "config": {}},
                    {"name": "inc", "type": "test.IncrementComponent", "config": {}},
                ],
                "flow": {
                    "settings": {"fail_fast": False},
                    "steps": [
                        {"component": "fail", "on_error": "continue"},
                        {"component": "inc"},
                    ],
                },
            }
        )

        components = {
            "fail": FailingComponent("fail"),
            "inc": IncrementComponent("inc"),
        }
        engine = FlowEngine(config, components)

        result = engine.execute()

        # Should continue despite failure
        assert result.get("count") == 1
        assert len(result.metadata.errors) == 1
        assert result.metadata.errors[0]["component"] == "fail"

    def test_execute_error_skip(self) -> None:
        """Test error handling with on_error=skip."""
        config = ConfigLoader.from_dict(
            {
                "name": "Skip Flow",
                "components": [
                    {"name": "fail", "type": "test.FailingComponent", "config": {}},
                ],
                "flow": {
                    "settings": {"fail_fast": False},
                    "steps": [
                        {"component": "fail", "on_error": "skip"},
                    ],
                },
            }
        )

        components = {"fail": FailingComponent("fail")}
        engine = FlowEngine(config, components)

        result = engine.execute()

        assert "fail" in result.metadata.skipped_components
        assert len(result.metadata.errors) == 1

    def test_setup_teardown_called(self) -> None:
        """Test setup and teardown are called."""
        config = ConfigLoader.from_dict(
            {
                "name": "Lifecycle Flow",
                "components": [
                    {"name": "comp", "type": "test.SetupTeardownComponent", "config": {}},
                ],
                "flow": {"steps": [{"component": "comp"}]},
            }
        )

        component = SetupTeardownComponent("comp")
        engine = FlowEngine(config, {"comp": component})

        result = engine.execute()

        assert component.setup_called
        assert component.teardown_called
        assert result.get("comp_setup") is True
        assert result.get("comp_process") is True
        assert result.get("comp_teardown") is True

    def test_teardown_called_on_error(self) -> None:
        """Test teardown is called even when process fails."""

        class FailInProcess(BaseComponent):
            def __init__(self, name: str) -> None:
                super().__init__(name)
                self.teardown_called = False

            def process(self, context: FlowContext) -> FlowContext:
                raise RuntimeError("fail")

            def teardown(self, context: FlowContext) -> None:
                self.teardown_called = True

        config = ConfigLoader.from_dict(
            {
                "name": "Teardown Test",
                "components": [
                    {"name": "fail", "type": "test.FailInProcess", "config": {}},
                ],
                "flow": {"steps": [{"component": "fail"}]},
            }
        )

        component = FailInProcess("fail")
        engine = FlowEngine(config, {"fail": component})

        with pytest.raises(ComponentError):
            engine.execute()

        assert component.teardown_called

    def test_validate(self) -> None:
        """Test validate method."""
        config = ConfigLoader.from_dict(
            {
                "name": "Validation Test",
                "components": [
                    {"name": "inc", "type": "test.IncrementComponent", "config": {}},
                ],
                "flow": {"steps": [{"component": "inc"}]},
            }
        )

        components = {"inc": IncrementComponent("inc")}
        engine = FlowEngine(config, components)

        errors = engine.validate()
        assert errors == []

    def test_validate_missing_component(self) -> None:
        """Test validate catches missing components."""
        config = ConfigLoader.from_dict(
            {
                "name": "Missing Component",
                "components": [
                    {"name": "inc", "type": "test.IncrementComponent", "config": {}},
                ],
                "flow": {"steps": [{"component": "inc"}]},
            }
        )

        components = {"inc": IncrementComponent("inc")}
        engine = FlowEngine(config, components)

        # Manually add a step referencing non-existent component
        engine.config.flow.steps.append(
            type(engine.config.flow.steps[0])(component="missing")
        )

        errors = engine.validate()
        assert any("missing" in e for e in errors)

    def test_dry_run(self, multi_step_config: FlowConfig) -> None:
        """Test dry_run method."""
        components = {
            "inc1": IncrementComponent("inc1"),
            "inc2": IncrementComponent("inc2"),
            "inc3": IncrementComponent("inc3"),
        }
        engine = FlowEngine(multi_step_config, components)

        steps = engine.dry_run()
        assert steps == ["inc1", "inc2", "inc3"]

    def test_dry_run_with_conditions(self, conditional_config: FlowConfig) -> None:
        """Test dry_run respects conditions."""
        components = {"inc": IncrementComponent("inc")}
        engine = FlowEngine(conditional_config, components)

        # Without condition met
        context = FlowContext()
        context.set("run_increment", False)
        steps = engine.dry_run(context)
        assert steps == []

        # With condition met
        context.set("run_increment", True)
        steps = engine.dry_run(context)
        assert steps == ["inc"]

    def test_timing_recorded(self, simple_config: FlowConfig) -> None:
        """Test execution timing is recorded."""
        components = {"inc": IncrementComponent("inc")}
        engine = FlowEngine(simple_config, components)

        result = engine.execute()

        assert "inc" in result.metadata.component_timings
        assert result.metadata.component_timings["inc"] >= 0
