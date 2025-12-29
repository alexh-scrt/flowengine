"""Integration tests for FlowEngine flows."""

import pytest

from flowengine import (
    BaseComponent,
    ConfigLoader,
    FlowContext,
    FlowEngine,
    ComponentError,
)


# === Test Components ===


class AddComponent(BaseComponent):
    """Component that adds a value to count."""

    def init(self, config: dict) -> None:
        super().init(config)
        self.amount = config.get("amount", 1)

    def process(self, context: FlowContext) -> FlowContext:
        count = context.get("count", 0)
        context.set("count", count + self.amount)
        return context


class MultiplyComponent(BaseComponent):
    """Component that multiplies count by a value."""

    def init(self, config: dict) -> None:
        super().init(config)
        self.factor = config.get("factor", 2)

    def process(self, context: FlowContext) -> FlowContext:
        count = context.get("count", 0)
        context.set("count", count * self.factor)
        return context


class SetStatusComponent(BaseComponent):
    """Component that sets a status value."""

    def init(self, config: dict) -> None:
        super().init(config)
        self.status = config.get("status", "complete")

    def process(self, context: FlowContext) -> FlowContext:
        context.set("status", self.status)
        return context


class FailOnConditionComponent(BaseComponent):
    """Component that fails based on context condition."""

    def process(self, context: FlowContext) -> FlowContext:
        if context.get("should_fail"):
            raise RuntimeError("Condition triggered failure")
        context.set("passed", True)
        return context


class DataTransformComponent(BaseComponent):
    """Component that transforms input data."""

    def process(self, context: FlowContext) -> FlowContext:
        if context.input:
            context.set("transformed", {
                "original": context.input,
                "processed": True,
            })
        return context


# === Integration Tests ===


class TestSimpleFlow:
    """Test simple sequential flow execution."""

    def test_single_step_flow(self) -> None:
        """Test flow with single step."""
        config = ConfigLoader.from_dict({
            "name": "Single Step",
            "components": [
                {"name": "add", "type": "test.AddComponent", "config": {"amount": 5}},
            ],
            "flow": {
                "steps": [{"component": "add"}],
            },
        })

        components = {"add": AddComponent("add")}
        engine = FlowEngine(config, components)

        result = engine.execute()

        assert result.get("count") == 5

    def test_multi_step_sequential(self) -> None:
        """Test flow with multiple sequential steps."""
        config = ConfigLoader.from_dict({
            "name": "Multi Step",
            "components": [
                {"name": "add1", "type": "test.AddComponent", "config": {"amount": 10}},
                {"name": "multiply", "type": "test.MultiplyComponent", "config": {"factor": 3}},
                {"name": "add2", "type": "test.AddComponent", "config": {"amount": 5}},
            ],
            "flow": {
                "steps": [
                    {"component": "add1"},
                    {"component": "multiply"},
                    {"component": "add2"},
                ],
            },
        })

        components = {
            "add1": AddComponent("add1"),
            "multiply": MultiplyComponent("multiply"),
            "add2": AddComponent("add2"),
        }
        engine = FlowEngine(config, components)

        result = engine.execute()

        # 0 + 10 = 10, 10 * 3 = 30, 30 + 5 = 35
        assert result.get("count") == 35


class TestConditionalFlow:
    """Test conditional flow execution."""

    def test_condition_true(self) -> None:
        """Test step executes when condition is true."""
        config = ConfigLoader.from_dict({
            "name": "Conditional",
            "components": [
                {"name": "add", "type": "test.AddComponent", "config": {"amount": 10}},
            ],
            "flow": {
                "steps": [
                    {
                        "component": "add",
                        "condition": "context.data.run == True",
                    },
                ],
            },
        })

        components = {"add": AddComponent("add")}
        engine = FlowEngine(config, components)

        context = FlowContext()
        context.set("run", True)
        result = engine.execute(context)

        assert result.get("count") == 10
        assert "add" not in result.metadata.skipped_components

    def test_condition_false(self) -> None:
        """Test step skipped when condition is false."""
        config = ConfigLoader.from_dict({
            "name": "Conditional",
            "components": [
                {"name": "add", "type": "test.AddComponent", "config": {"amount": 10}},
            ],
            "flow": {
                "steps": [
                    {
                        "component": "add",
                        "condition": "context.data.run == True",
                    },
                ],
            },
        })

        components = {"add": AddComponent("add")}
        engine = FlowEngine(config, components)

        context = FlowContext()
        context.set("run", False)
        result = engine.execute(context)

        assert result.get("count") is None
        assert "add" in result.metadata.skipped_components

    def test_conditional_chain(self) -> None:
        """Test chain of conditional steps."""
        config = ConfigLoader.from_dict({
            "name": "Conditional Chain",
            "components": [
                {"name": "add", "type": "test.AddComponent", "config": {"amount": 10}},
                {"name": "multiply", "type": "test.MultiplyComponent", "config": {"factor": 2}},
                {"name": "status", "type": "test.SetStatusComponent", "config": {"status": "done"}},
            ],
            "flow": {
                "steps": [
                    {"component": "add"},
                    {
                        "component": "multiply",
                        "condition": "context.data.count > 5",
                    },
                    {
                        "component": "status",
                        "condition": "context.data.count > 15",
                    },
                ],
            },
        })

        components = {
            "add": AddComponent("add"),
            "multiply": MultiplyComponent("multiply"),
            "status": SetStatusComponent("status"),
        }
        engine = FlowEngine(config, components)

        result = engine.execute()

        # 0 + 10 = 10, 10 > 5 so multiply: 10 * 2 = 20, 20 > 15 so status
        assert result.get("count") == 20
        assert result.get("status") == "done"


class TestErrorHandling:
    """Test error handling in flows."""

    def test_fail_fast(self) -> None:
        """Test fail_fast stops execution on error."""
        config = ConfigLoader.from_dict({
            "name": "Fail Fast",
            "components": [
                {"name": "fail", "type": "test.FailOnConditionComponent", "config": {}},
                {"name": "add", "type": "test.AddComponent", "config": {"amount": 10}},
            ],
            "flow": {
                "settings": {"fail_fast": True},
                "steps": [
                    {"component": "fail"},
                    {"component": "add"},
                ],
            },
        })

        components = {
            "fail": FailOnConditionComponent("fail"),
            "add": AddComponent("add"),
        }
        engine = FlowEngine(config, components)

        context = FlowContext()
        context.set("should_fail", True)

        with pytest.raises(ComponentError):
            engine.execute(context)

    def test_on_error_continue(self) -> None:
        """Test on_error=continue continues after error."""
        config = ConfigLoader.from_dict({
            "name": "Continue on Error",
            "components": [
                {"name": "fail", "type": "test.FailOnConditionComponent", "config": {}},
                {"name": "add", "type": "test.AddComponent", "config": {"amount": 10}},
            ],
            "flow": {
                "settings": {"fail_fast": False},
                "steps": [
                    {"component": "fail", "on_error": "continue"},
                    {"component": "add"},
                ],
            },
        })

        components = {
            "fail": FailOnConditionComponent("fail"),
            "add": AddComponent("add"),
        }
        engine = FlowEngine(config, components)

        context = FlowContext()
        context.set("should_fail", True)
        result = engine.execute(context)

        # Should continue to add step
        assert result.get("count") == 10
        assert len(result.metadata.errors) == 1
        assert result.metadata.errors[0]["component"] == "fail"

    def test_on_error_skip(self) -> None:
        """Test on_error=skip marks component as skipped."""
        config = ConfigLoader.from_dict({
            "name": "Skip on Error",
            "components": [
                {"name": "fail", "type": "test.FailOnConditionComponent", "config": {}},
            ],
            "flow": {
                "settings": {"fail_fast": False},
                "steps": [
                    {"component": "fail", "on_error": "skip"},
                ],
            },
        })

        components = {"fail": FailOnConditionComponent("fail")}
        engine = FlowEngine(config, components)

        context = FlowContext()
        context.set("should_fail", True)
        result = engine.execute(context)

        assert "fail" in result.metadata.skipped_components


class TestInputData:
    """Test input data handling."""

    def test_input_passed_to_context(self) -> None:
        """Test input_data is available in context."""
        config = ConfigLoader.from_dict({
            "name": "Input Test",
            "components": [
                {"name": "transform", "type": "test.DataTransformComponent", "config": {}},
            ],
            "flow": {
                "steps": [{"component": "transform"}],
            },
        })

        components = {"transform": DataTransformComponent("transform")}
        engine = FlowEngine(config, components)

        result = engine.execute(input_data={"key": "value"})

        assert result.input == {"key": "value"}
        assert result.get("transformed") == {
            "original": {"key": "value"},
            "processed": True,
        }


class TestMetadata:
    """Test execution metadata tracking."""

    def test_timing_recorded(self) -> None:
        """Test component timings are recorded."""
        config = ConfigLoader.from_dict({
            "name": "Timing Test",
            "components": [
                {"name": "add1", "type": "test.AddComponent", "config": {}},
                {"name": "add2", "type": "test.AddComponent", "config": {}},
            ],
            "flow": {
                "steps": [
                    {"component": "add1"},
                    {"component": "add2"},
                ],
            },
        })

        components = {
            "add1": AddComponent("add1"),
            "add2": AddComponent("add2"),
        }
        engine = FlowEngine(config, components)

        result = engine.execute()

        assert "add1" in result.metadata.component_timings
        assert "add2" in result.metadata.component_timings
        assert result.metadata.component_timings["add1"] >= 0
        assert result.metadata.component_timings["add2"] >= 0

    def test_completion_time_set(self) -> None:
        """Test completion time is set after execution."""
        config = ConfigLoader.from_dict({
            "name": "Completion Test",
            "components": [
                {"name": "add", "type": "test.AddComponent", "config": {}},
            ],
            "flow": {
                "steps": [{"component": "add"}],
            },
        })

        components = {"add": AddComponent("add")}
        engine = FlowEngine(config, components)

        result = engine.execute()

        assert result.metadata.completed_at is not None
        assert result.metadata.total_duration is not None
        assert result.metadata.total_duration >= 0


class TestComplexFlow:
    """Test complex flow scenarios."""

    def test_full_pipeline(self) -> None:
        """Test a realistic multi-stage pipeline."""
        yaml_config = """
name: "Data Pipeline"
version: "1.0"
description: "A complete data processing pipeline"

components:
  - name: init
    type: test.AddComponent
    config:
      amount: 100

  - name: validate
    type: test.SetStatusComponent
    config:
      status: validated

  - name: transform
    type: test.MultiplyComponent
    config:
      factor: 2

  - name: finalize
    type: test.SetStatusComponent
    config:
      status: complete

flow:
  type: sequential
  settings:
    fail_fast: false
    timeout_seconds: 60

  steps:
    - component: init
      description: "Initialize data"

    - component: validate
      description: "Validate input"
      condition: "context.data.count > 0"

    - component: transform
      description: "Transform data"
      condition: "context.data.status == 'validated'"

    - component: finalize
      description: "Finalize processing"
"""
        config = ConfigLoader.loads(yaml_config)

        components = {
            "init": AddComponent("init"),
            "validate": SetStatusComponent("validate"),
            "transform": MultiplyComponent("transform"),
            "finalize": SetStatusComponent("finalize"),
        }
        engine = FlowEngine(config, components)

        result = engine.execute()

        # 0 + 100 = 100, status = validated, 100 * 2 = 200, status = complete
        assert result.get("count") == 200
        assert result.get("status") == "complete"
        assert len(result.metadata.component_timings) == 4
        assert len(result.metadata.skipped_components) == 0

    def test_dry_run_matches_execution(self) -> None:
        """Test dry_run predicts actual execution based on initial context."""
        config = ConfigLoader.from_dict({
            "name": "Dry Run Test",
            "components": [
                {"name": "add", "type": "test.AddComponent", "config": {}},
                {"name": "multiply", "type": "test.MultiplyComponent", "config": {}},
            ],
            "flow": {
                "steps": [
                    {"component": "add"},
                    {
                        "component": "multiply",
                        "condition": "context.data.run_multiply == True",
                    },
                ],
            },
        })

        components = {
            "add": AddComponent("add"),
            "multiply": MultiplyComponent("multiply"),
        }
        engine = FlowEngine(config, components)

        # Test with condition false
        context = FlowContext()
        context.set("run_multiply", False)

        dry_run_steps = engine.dry_run(context)
        assert dry_run_steps == ["add"]

        # Test with condition true
        context.set("run_multiply", True)
        dry_run_steps = engine.dry_run(context)
        assert dry_run_steps == ["add", "multiply"]

        # Actual execution matches dry run
        result = engine.execute(context)
        executed_steps = list(result.metadata.component_timings.keys())
        assert dry_run_steps == executed_steps
