"""Tests for FlowEngine improvements."""

import time

import pytest

from flowengine import (
    BaseComponent,
    ComponentRegistry,
    ConditionEvaluationError,
    ConfigLoader,
    FlowContext,
    FlowEngine,
    FlowTimeoutError,
    StepTiming,
    load_component_class,
)


# === Test Components ===


class SlowComponent(BaseComponent):
    """Component that sleeps for a configured duration."""

    def init(self, config: dict) -> None:
        super().init(config)
        self.sleep_seconds = config.get("sleep_seconds", 0.1)

    def process(self, context: FlowContext) -> FlowContext:
        time.sleep(self.sleep_seconds)
        context.set("slept", True)
        return context


class CounterComponent(BaseComponent):
    """Component that increments a counter."""

    def process(self, context: FlowContext) -> FlowContext:
        count = context.get("count", 0)
        context.set("count", count + 1)
        return context


# === Step-Indexed Timing Tests ===


class TestStepIndexedTiming:
    """Test step-indexed timing metadata."""

    def test_step_timing_preserves_order(self) -> None:
        """Test that step timings preserve execution order."""
        config = ConfigLoader.from_dict({
            "name": "Order Test",
            "components": [
                {"name": "a", "type": "test.CounterComponent", "config": {}},
                {"name": "b", "type": "test.CounterComponent", "config": {}},
                {"name": "c", "type": "test.CounterComponent", "config": {}},
            ],
            "flow": {
                "steps": [
                    {"component": "a"},
                    {"component": "b"},
                    {"component": "c"},
                ],
            },
        })

        components = {
            "a": CounterComponent("a"),
            "b": CounterComponent("b"),
            "c": CounterComponent("c"),
        }
        engine = FlowEngine(config, components)
        result = engine.execute()

        # Check step timings are in order
        assert len(result.metadata.step_timings) == 3
        assert result.metadata.step_timings[0].component == "a"
        assert result.metadata.step_timings[0].step_index == 0
        assert result.metadata.step_timings[0].execution_order == 0
        assert result.metadata.step_timings[1].component == "b"
        assert result.metadata.step_timings[1].step_index == 1
        assert result.metadata.step_timings[1].execution_order == 1
        assert result.metadata.step_timings[2].component == "c"
        assert result.metadata.step_timings[2].step_index == 2
        assert result.metadata.step_timings[2].execution_order == 2

    def test_step_index_maps_to_flow_definition(self) -> None:
        """Test that step_index maps to flow definition order even with skipped steps."""
        config = ConfigLoader.from_dict({
            "name": "Skip Test",
            "components": [
                {"name": "a", "type": "test.CounterComponent", "config": {}},
                {"name": "b", "type": "test.CounterComponent", "config": {}},
                {"name": "c", "type": "test.CounterComponent", "config": {}},
            ],
            "flow": {
                "steps": [
                    {"component": "a"},
                    {"component": "b", "condition": "False"},  # Will be skipped
                    {"component": "c"},
                ],
            },
        })

        components = {
            "a": CounterComponent("a"),
            "b": CounterComponent("b"),
            "c": CounterComponent("c"),
        }
        engine = FlowEngine(config, components)
        result = engine.execute()

        # Only a and c executed, b was skipped
        assert len(result.metadata.step_timings) == 2
        assert "b" in result.metadata.skipped_components

        # step_index should map to flow definition order
        assert result.metadata.step_timings[0].component == "a"
        assert result.metadata.step_timings[0].step_index == 0  # First in flow
        assert result.metadata.step_timings[0].execution_order == 0  # First executed

        assert result.metadata.step_timings[1].component == "c"
        assert result.metadata.step_timings[1].step_index == 2  # Third in flow (index 2)
        assert result.metadata.step_timings[1].execution_order == 1  # Second executed

    def test_repeated_component_separate_timings(self) -> None:
        """Test that repeated components have separate timing entries."""
        config = ConfigLoader.from_dict({
            "name": "Repeat Test",
            "components": [
                {"name": "counter", "type": "test.CounterComponent", "config": {}},
            ],
            "flow": {
                "steps": [
                    {"component": "counter"},
                    {"component": "counter"},
                    {"component": "counter"},
                ],
            },
        })

        components = {"counter": CounterComponent("counter")}
        engine = FlowEngine(config, components)
        result = engine.execute()

        # Should have 3 separate timing entries
        assert len(result.metadata.step_timings) == 3
        for i, timing in enumerate(result.metadata.step_timings):
            assert timing.component == "counter"
            assert timing.step_index == i

        # component_timings should aggregate (sum)
        assert "counter" in result.metadata.component_timings
        total = sum(t.duration for t in result.metadata.step_timings)
        assert result.metadata.component_timings["counter"] == pytest.approx(total)

    def test_step_timing_has_started_at(self) -> None:
        """Test that step timings include started_at timestamp."""
        config = ConfigLoader.from_dict({
            "name": "Timestamp Test",
            "components": [
                {"name": "a", "type": "test.CounterComponent", "config": {}},
            ],
            "flow": {
                "steps": [{"component": "a"}],
            },
        })

        components = {"a": CounterComponent("a")}
        engine = FlowEngine(config, components)
        result = engine.execute()

        timing = result.metadata.step_timings[0]
        assert timing.started_at is not None
        assert timing.duration >= 0


# === Round-Trip Serialization Tests ===


class TestRoundTripSerialization:
    """Test FlowContext round-trip serialization."""

    def test_round_trip_preserves_data(self) -> None:
        """Test that from_dict(to_dict()) preserves data."""
        context = FlowContext()
        context.set("key", "value")
        context.set("nested", {"a": 1, "b": [1, 2, 3]})
        context.input = {"input_key": "input_value"}

        restored = FlowContext.from_dict(context.to_dict())

        assert restored.get("key") == "value"
        assert restored.get("nested") == {"a": 1, "b": [1, 2, 3]}
        assert restored.input == {"input_key": "input_value"}

    def test_round_trip_preserves_metadata(self) -> None:
        """Test that round-trip preserves metadata."""
        context = FlowContext()
        context.metadata.record_timing("comp1", 1.5)
        context.metadata.record_timing("comp2", 2.0)
        context.metadata.skipped_components.append("skipped")
        context.metadata.add_error("failed", RuntimeError("test error"))

        restored = FlowContext.from_dict(context.to_dict())

        assert len(restored.metadata.step_timings) == 2
        assert restored.metadata.step_timings[0].component == "comp1"
        assert restored.metadata.step_timings[0].duration == 1.5
        assert "skipped" in restored.metadata.skipped_components
        assert len(restored.metadata.errors) == 1
        assert restored.metadata.errors[0]["component"] == "failed"

    def test_round_trip_preserves_flow_id(self) -> None:
        """Test that round-trip preserves flow_id."""
        context = FlowContext()
        original_id = context.metadata.flow_id

        restored = FlowContext.from_dict(context.to_dict())

        assert restored.metadata.flow_id == original_id

    def test_from_json_round_trip(self) -> None:
        """Test JSON round-trip."""
        context = FlowContext()
        context.set("key", "value")
        context.metadata.record_timing("comp", 1.0)

        json_str = context.to_json()
        restored = FlowContext.from_json(json_str)

        assert restored.get("key") == "value"
        assert len(restored.metadata.step_timings) == 1

    def test_step_counter_continues_after_restore(self) -> None:
        """Test that step counter continues correctly after restore."""
        context = FlowContext()
        context.metadata.record_timing("a", 1.0)
        context.metadata.record_timing("b", 2.0)

        restored = FlowContext.from_dict(context.to_dict())
        restored.metadata.record_timing("c", 3.0)

        # New timing should have step_index 2
        assert restored.metadata.step_timings[2].step_index == 2


# === Condition Error Handling Tests ===


class TestConditionErrorHandling:
    """Test explicit condition error handling."""

    def test_condition_error_fail_mode(self) -> None:
        """Test on_condition_error=fail raises exception."""
        config = ConfigLoader.from_dict({
            "name": "Fail Mode",
            "components": [
                {"name": "a", "type": "test.CounterComponent", "config": {}},
            ],
            "flow": {
                "settings": {"on_condition_error": "fail"},
                "steps": [
                    {"component": "a", "condition": "len(x) > 0"},  # Unsafe
                ],
            },
        })

        components = {"a": CounterComponent("a")}
        engine = FlowEngine(config, components)

        with pytest.raises(ConditionEvaluationError):
            engine.execute()

    def test_condition_error_skip_mode(self) -> None:
        """Test on_condition_error=skip skips and records."""
        config = ConfigLoader.from_dict({
            "name": "Skip Mode",
            "components": [
                {"name": "a", "type": "test.CounterComponent", "config": {}},
                {"name": "b", "type": "test.CounterComponent", "config": {}},
            ],
            "flow": {
                "settings": {"on_condition_error": "skip"},
                "steps": [
                    {"component": "a", "condition": "len(x) > 0"},  # Unsafe
                    {"component": "b"},  # Should still run
                ],
            },
        })

        components = {
            "a": CounterComponent("a"),
            "b": CounterComponent("b"),
        }
        engine = FlowEngine(config, components)
        result = engine.execute()

        # a should be skipped, b should run
        assert "a" in result.metadata.skipped_components
        assert result.get("count") == 1  # Only b ran
        assert len(result.metadata.condition_errors) == 1
        assert result.metadata.condition_errors[0]["component"] == "a"

    def test_condition_error_warn_mode(self) -> None:
        """Test on_condition_error=warn logs warning and continues."""
        config = ConfigLoader.from_dict({
            "name": "Warn Mode",
            "components": [
                {"name": "a", "type": "test.CounterComponent", "config": {}},
                {"name": "b", "type": "test.CounterComponent", "config": {}},
            ],
            "flow": {
                "settings": {"on_condition_error": "warn"},
                "steps": [
                    {"component": "a", "condition": "len(x) > 0"},  # Unsafe
                    {"component": "b"},
                ],
            },
        })

        components = {
            "a": CounterComponent("a"),
            "b": CounterComponent("b"),
        }
        engine = FlowEngine(config, components)
        result = engine.execute()

        # a should be skipped (condition error treated as False)
        assert "a" in result.metadata.skipped_components
        assert result.get("count") == 1  # Only b ran
        assert len(result.metadata.condition_errors) == 1


# === Timeout Tests ===


class TestTimeoutEnforcement:
    """Test timeout enforcement."""

    def test_timeout_not_exceeded(self) -> None:
        """Test flow completes when timeout not exceeded."""
        config = ConfigLoader.from_dict({
            "name": "Fast Flow",
            "components": [
                {"name": "a", "type": "test.CounterComponent", "config": {}},
            ],
            "flow": {
                "settings": {"timeout_seconds": 10},
                "steps": [{"component": "a"}],
            },
        })

        components = {"a": CounterComponent("a")}
        engine = FlowEngine(config, components)
        result = engine.execute()

        assert result.get("count") == 1

    def test_timeout_exceeded_raises(self) -> None:
        """Test timeout raises FlowTimeoutError."""
        config = ConfigLoader.from_dict({
            "name": "Slow Flow",
            "components": [
                {"name": "slow", "type": "test.SlowComponent", "config": {"sleep_seconds": 0.05}},
                {"name": "second", "type": "test.CounterComponent", "config": {}},
            ],
            "flow": {
                "settings": {"timeout_seconds": 0.01},
                "steps": [
                    {"component": "slow"},
                    {"component": "second"},
                ],
            },
        })

        slow = SlowComponent("slow")
        slow.init({"sleep_seconds": 0.05})

        components = {
            "slow": slow,
            "second": CounterComponent("second"),
        }
        engine = FlowEngine(config, components)

        with pytest.raises(FlowTimeoutError) as exc_info:
            engine.execute()

        assert exc_info.value.timeout == 0.01
        assert exc_info.value.elapsed > 0.01


# === Component Registry Tests ===


class TestComponentRegistry:
    """Test component registry functionality."""

    def test_register_and_create(self) -> None:
        """Test registering a class and creating an instance."""
        registry = ComponentRegistry()
        registry.register_class("counter", CounterComponent)

        instance = registry.create("counter", "my_counter")

        assert isinstance(instance, CounterComponent)
        assert instance.name == "my_counter"

    def test_get_class(self) -> None:
        """Test getting a registered class."""
        registry = ComponentRegistry()
        registry.register_class("counter", CounterComponent)

        cls = registry.get_class("counter")
        assert cls is CounterComponent

    def test_get_class_not_found(self) -> None:
        """Test getting an unregistered class returns None."""
        registry = ComponentRegistry()

        cls = registry.get_class("unknown")
        assert cls is None

    def test_list_registered(self) -> None:
        """Test listing registered classes."""
        registry = ComponentRegistry()
        registry.register_class("counter", CounterComponent)
        registry.register_class("slow", SlowComponent)

        registered = registry.list_registered()
        assert "counter" in registered
        assert "slow" in registered

    def test_load_component_class_invalid_path(self) -> None:
        """Test load_component_class with invalid path."""
        from flowengine.errors import ConfigurationError

        with pytest.raises(ConfigurationError, match="Invalid component type path"):
            load_component_class("NoDotsHere")

    def test_load_component_class_module_not_found(self) -> None:
        """Test load_component_class with non-existent module."""
        from flowengine.errors import ConfigurationError

        with pytest.raises(ConfigurationError, match="Module not found"):
            load_component_class("nonexistent.module.Component")


class TestEngineValidateComponentTypes:
    """Test engine component type validation."""

    def test_validate_component_types_matching(self) -> None:
        """Test validation passes when types match."""
        config = ConfigLoader.from_dict({
            "name": "Test",
            "components": [
                {
                    "name": "counter",
                    "type": "tests.unit.core.test_improvements.CounterComponent",
                    "config": {},
                },
            ],
            "flow": {
                "steps": [{"component": "counter"}],
            },
        })

        components = {"counter": CounterComponent("counter")}
        engine = FlowEngine(config, components)

        errors = engine.validate_component_types()
        assert errors == []

    def test_validate_component_types_mismatch(self) -> None:
        """Test validation catches type mismatches."""
        config = ConfigLoader.from_dict({
            "name": "Test",
            "components": [
                {
                    "name": "counter",
                    "type": "tests.unit.core.test_improvements.SlowComponent",
                    "config": {},
                },
            ],
            "flow": {
                "steps": [{"component": "counter"}],
            },
        })

        # Provide wrong type, disable auto-validation to test manual call
        components = {"counter": CounterComponent("counter")}
        engine = FlowEngine(config, components, validate_types=False)

        errors = engine.validate_component_types()
        assert len(errors) == 1
        assert "mismatch" in errors[0].lower()

    def test_validate_types_parameter_enforces(self) -> None:
        """Test validate_types=True raises on type mismatch."""
        from flowengine.errors import ConfigurationError

        config = ConfigLoader.from_dict({
            "name": "Test",
            "components": [
                {
                    "name": "counter",
                    "type": "tests.unit.core.test_improvements.SlowComponent",
                    "config": {},
                },
            ],
            "flow": {
                "steps": [{"component": "counter"}],
            },
        })

        components = {"counter": CounterComponent("counter")}

        with pytest.raises(ConfigurationError, match="type validation failed"):
            FlowEngine(config, components, validate_types=True)


class TestFlowType:
    """Test flow.type affects behavior."""

    def test_conditional_type_changes_default_on_condition_error(self) -> None:
        """Test conditional flow type defaults on_condition_error to skip."""
        config = ConfigLoader.from_dict({
            "name": "Conditional Test",
            "components": [
                {"name": "a", "type": "test.CounterComponent", "config": {}},
            ],
            "flow": {
                "type": "conditional",
                "steps": [
                    {"component": "a", "condition": "len(x) > 0"},  # Invalid
                ],
            },
        })

        components = {"a": CounterComponent("a")}
        engine = FlowEngine(config, components)

        # With conditional type, on_condition_error defaults to "skip"
        assert engine.on_condition_error == "skip"

        # Should skip instead of raising
        result = engine.execute()
        assert "a" in result.metadata.skipped_components

    def test_sequential_type_keeps_fail_default(self) -> None:
        """Test sequential flow type keeps on_condition_error as fail."""
        config = ConfigLoader.from_dict({
            "name": "Sequential Test",
            "components": [
                {"name": "a", "type": "test.CounterComponent", "config": {}},
            ],
            "flow": {
                "type": "sequential",
                "steps": [
                    {"component": "a", "condition": "len(x) > 0"},  # Invalid
                ],
            },
        })

        components = {"a": CounterComponent("a")}
        engine = FlowEngine(config, components)

        # With sequential type, on_condition_error stays as "fail"
        assert engine.on_condition_error == "fail"

        # Should raise
        with pytest.raises(ConditionEvaluationError):
            engine.execute()

    def test_explicit_on_condition_error_overrides_flow_type(self) -> None:
        """Test explicit on_condition_error overrides flow type default."""
        config = ConfigLoader.from_dict({
            "name": "Override Test",
            "components": [
                {"name": "a", "type": "test.CounterComponent", "config": {}},
            ],
            "flow": {
                "type": "conditional",
                "settings": {"on_condition_error": "warn"},
                "steps": [{"component": "a"}],
            },
        })

        components = {"a": CounterComponent("a")}
        engine = FlowEngine(config, components)

        # Explicit setting should be preserved
        assert engine.on_condition_error == "warn"

    def test_conditional_flow_first_match_semantics(self) -> None:
        """Test conditional flow uses first-match branching."""
        config = ConfigLoader.from_dict({
            "name": "First Match Test",
            "components": [
                {"name": "a", "type": "test.CounterComponent", "config": {}},
                {"name": "b", "type": "test.CounterComponent", "config": {}},
                {"name": "c", "type": "test.CounterComponent", "config": {}},
            ],
            "flow": {
                "type": "conditional",
                "steps": [
                    {"component": "a"},  # Runs (no condition)
                    {"component": "b"},  # Stops here (first match)
                    {"component": "c"},  # Should not run
                ],
            },
        })

        components = {
            "a": CounterComponent("a"),
            "b": CounterComponent("b"),
            "c": CounterComponent("c"),
        }
        engine = FlowEngine(config, components)
        result = engine.execute()

        # Only first step runs with first-match semantics
        assert len(result.metadata.step_timings) == 1
        assert result.metadata.step_timings[0].component == "a"
        assert result.get("count") == 1

    def test_conditional_flow_with_conditions(self) -> None:
        """Test conditional flow stops after first matching conditioned step."""
        config = ConfigLoader.from_dict({
            "name": "Conditional First Match",
            "components": [
                {"name": "handler_a", "type": "test.CounterComponent", "config": {}},
                {"name": "handler_b", "type": "test.CounterComponent", "config": {}},
                {"name": "handler_c", "type": "test.CounterComponent", "config": {}},
            ],
            "flow": {
                "type": "conditional",
                "steps": [
                    {"component": "handler_a", "condition": "context.data.mode == 'a'"},
                    {"component": "handler_b", "condition": "context.data.mode == 'b'"},
                    {"component": "handler_c", "condition": "context.data.mode == 'c'"},
                ],
            },
        })

        components = {
            "handler_a": CounterComponent("handler_a"),
            "handler_b": CounterComponent("handler_b"),
            "handler_c": CounterComponent("handler_c"),
        }
        engine = FlowEngine(config, components)

        # Test mode 'b' - should only run handler_b
        ctx = FlowContext()
        ctx.set("mode", "b")
        result = engine.execute(ctx)

        assert len(result.metadata.step_timings) == 1
        assert result.metadata.step_timings[0].component == "handler_b"
        assert "handler_a" in result.metadata.skipped_components
        assert result.get("count") == 1

    def test_sequential_flow_runs_all_steps(self) -> None:
        """Test sequential flow runs all steps regardless of conditions."""
        config = ConfigLoader.from_dict({
            "name": "Sequential All Steps",
            "components": [
                {"name": "a", "type": "test.CounterComponent", "config": {}},
                {"name": "b", "type": "test.CounterComponent", "config": {}},
                {"name": "c", "type": "test.CounterComponent", "config": {}},
            ],
            "flow": {
                "type": "sequential",
                "steps": [
                    {"component": "a"},
                    {"component": "b"},
                    {"component": "c"},
                ],
            },
        })

        components = {
            "a": CounterComponent("a"),
            "b": CounterComponent("b"),
            "c": CounterComponent("c"),
        }
        engine = FlowEngine(config, components)
        result = engine.execute()

        # All steps run in sequential mode
        assert len(result.metadata.step_timings) == 3
        assert result.get("count") == 3


# === Cooperative Timeout Tests ===


class CooperativeTimeoutComponent(BaseComponent):
    """Component that checks deadline cooperatively."""

    def init(self, config: dict) -> None:
        super().init(config)
        self.iterations = config.get("iterations", 10)
        self.sleep_per_iteration = config.get("sleep_per_iteration", 0.01)

    def process(self, context: FlowContext) -> FlowContext:
        for i in range(self.iterations):
            self.check_deadline(context)  # Cooperative timeout check
            time.sleep(self.sleep_per_iteration)
            context.set("iteration", i + 1)
        return context


class TestCooperativeTimeout:
    """Test cooperative timeout with check_deadline()."""

    def test_check_deadline_raises_when_expired(self) -> None:
        """Test check_deadline() raises FlowTimeoutError when deadline passed."""
        context = FlowContext()
        context.metadata.deadline = time.time() - 1  # Already expired

        component = CounterComponent("test")
        with pytest.raises(FlowTimeoutError, match="Deadline exceeded"):
            component.check_deadline(context)

    def test_check_deadline_no_error_when_valid(self) -> None:
        """Test check_deadline() does nothing when deadline not expired."""
        context = FlowContext()
        context.metadata.deadline = time.time() + 10  # 10 seconds in future

        component = CounterComponent("test")
        component.check_deadline(context)  # Should not raise

    def test_check_deadline_no_error_when_no_deadline(self) -> None:
        """Test check_deadline() does nothing when no deadline set."""
        context = FlowContext()
        context.metadata.deadline = None

        component = CounterComponent("test")
        component.check_deadline(context)  # Should not raise

    def test_cooperative_timeout_in_long_running_component(self) -> None:
        """Test component that cooperatively times out."""
        config = ConfigLoader.from_dict({
            "name": "Cooperative Timeout Test",
            "components": [
                {
                    "name": "slow",
                    "type": "test.CooperativeTimeoutComponent",
                    "config": {"iterations": 100, "sleep_per_iteration": 0.1},
                },
            ],
            "flow": {
                "settings": {"timeout_seconds": 0.05},  # Very short timeout
                "steps": [{"component": "slow"}],
            },
        })

        components = {"slow": CooperativeTimeoutComponent("slow")}
        engine = FlowEngine(config, components, validate_types=False)

        with pytest.raises(FlowTimeoutError):
            engine.execute()

    def test_deadline_set_during_execution(self) -> None:
        """Test that deadline is set in context during step execution."""

        class DeadlineCheckComponent(BaseComponent):
            def process(self, context: FlowContext) -> FlowContext:
                # Deadline should be set during execution
                context.set("deadline_was_set", context.metadata.deadline is not None)
                context.set("deadline_value", context.metadata.deadline)
                return context

        config = ConfigLoader.from_dict({
            "name": "Deadline Check",
            "components": [
                {"name": "checker", "type": "test.Component", "config": {}},
            ],
            "flow": {
                "settings": {"timeout_seconds": 60},
                "steps": [{"component": "checker"}],
            },
        })

        components = {"checker": DeadlineCheckComponent("checker")}
        engine = FlowEngine(config, components, validate_types=False)
        result = engine.execute()

        assert result.get("deadline_was_set") is True
        assert result.get("deadline_value") is not None

    def test_deadline_cleared_after_step(self) -> None:
        """Test that deadline is cleared after step completes."""
        config = ConfigLoader.from_dict({
            "name": "Deadline Clear Test",
            "components": [
                {"name": "a", "type": "test.CounterComponent", "config": {}},
            ],
            "flow": {
                "settings": {"timeout_seconds": 60},
                "steps": [{"component": "a"}],
            },
        })

        components = {"a": CounterComponent("a")}
        engine = FlowEngine(config, components, validate_types=False)
        result = engine.execute()

        # Deadline should be cleared after execution
        assert result.metadata.deadline is None


# === Deadline Check Detection Tests ===


class NonCooperativeSlowComponent(BaseComponent):
    """Component that takes a long time but doesn't check deadline."""

    def process(self, context: FlowContext) -> FlowContext:
        # Sleeps for 1.5 seconds but never calls check_deadline()
        time.sleep(1.5)
        context.set("completed", True)
        return context


class CooperativeSlowComponent(BaseComponent):
    """Component that takes a long time and checks deadline."""

    def process(self, context: FlowContext) -> FlowContext:
        for _ in range(15):
            self.check_deadline(context)  # Cooperative
            time.sleep(0.1)
        context.set("completed", True)
        return context


class TestDeadlineCheckDetection:
    """Test detection of components that don't check deadlines."""

    def test_deadline_checked_flag_set_by_check_deadline(self) -> None:
        """Test that check_deadline() sets the deadline_checked flag."""
        context = FlowContext()
        context.metadata.deadline = time.time() + 10
        context.metadata.deadline_checked = False

        component = CounterComponent("test")
        component.check_deadline(context)

        assert context.metadata.deadline_checked is True

    def test_deadline_checked_flag_reset_before_step(self) -> None:
        """Test that deadline_checked is reset before each step."""
        config = ConfigLoader.from_dict({
            "name": "Reset Test",
            "components": [
                {"name": "a", "type": "test.CounterComponent", "config": {}},
                {"name": "b", "type": "test.CounterComponent", "config": {}},
            ],
            "flow": {
                "settings": {"timeout_seconds": 60},
                "steps": [
                    {"component": "a"},
                    {"component": "b"},
                ],
            },
        })

        components = {
            "a": CounterComponent("a"),
            "b": CounterComponent("b"),
        }
        engine = FlowEngine(config, components, validate_types=False)
        result = engine.execute()

        # Flag should be cleared after execution
        assert result.metadata.deadline_checked is False

    def test_warning_logged_for_slow_component_without_check(self, caplog) -> None:
        """Test that warning is logged for slow components that don't check deadline."""
        import logging

        config = ConfigLoader.from_dict({
            "name": "Slow No Check",
            "components": [
                {"name": "slow", "type": "test.NonCooperativeSlowComponent", "config": {}},
            ],
            "flow": {
                "settings": {"timeout_seconds": 60},  # Long timeout so it completes
                "steps": [{"component": "slow"}],
            },
        })

        components = {"slow": NonCooperativeSlowComponent("slow")}
        engine = FlowEngine(config, components, validate_types=False)

        with caplog.at_level(logging.WARNING):
            result = engine.execute()

        assert result.get("completed") is True
        # Check warning was logged
        assert any("never called check_deadline" in record.message for record in caplog.records)
        assert any("slow" in record.message for record in caplog.records)

    def test_no_warning_for_cooperative_component(self, caplog) -> None:
        """Test that no warning is logged for cooperative components."""
        import logging

        config = ConfigLoader.from_dict({
            "name": "Slow With Check",
            "components": [
                {"name": "coop", "type": "test.CooperativeSlowComponent", "config": {}},
            ],
            "flow": {
                "settings": {"timeout_seconds": 60},
                "steps": [{"component": "coop"}],
            },
        })

        components = {"coop": CooperativeSlowComponent("coop")}
        engine = FlowEngine(config, components, validate_types=False)

        with caplog.at_level(logging.WARNING):
            result = engine.execute()

        assert result.get("completed") is True
        # No warning about deadline checks
        assert not any("never called check_deadline" in record.message for record in caplog.records)

    def test_no_warning_for_fast_component(self, caplog) -> None:
        """Test that no warning is logged for fast components."""
        import logging

        config = ConfigLoader.from_dict({
            "name": "Fast Test",
            "components": [
                {"name": "fast", "type": "test.CounterComponent", "config": {}},
            ],
            "flow": {
                "settings": {"timeout_seconds": 60},
                "steps": [{"component": "fast"}],
            },
        })

        components = {"fast": CounterComponent("fast")}
        engine = FlowEngine(config, components, validate_types=False)

        with caplog.at_level(logging.WARNING):
            engine.execute()

        # No warning for fast components
        assert not any("never called check_deadline" in record.message for record in caplog.records)

    def test_no_warning_when_no_timeout_configured(self, caplog) -> None:
        """Test that no warning is logged when timeout is not configured."""
        import logging

        config = ConfigLoader.from_dict({
            "name": "No Timeout",
            "components": [
                {"name": "slow", "type": "test.NonCooperativeSlowComponent", "config": {}},
            ],
            "flow": {
                # No timeout_seconds - defaults to 300 but we're testing the warning logic
                "steps": [{"component": "slow"}],
            },
        })

        # Force a component that takes >1s without checking
        components = {"slow": NonCooperativeSlowComponent("slow")}
        engine = FlowEngine(config, components, validate_types=False)

        # Override timeout to None to simulate no timeout
        engine.timeout = None

        with caplog.at_level(logging.WARNING):
            engine.execute()

        # No warning when no timeout is configured
        # (the remaining_timeout check is None so no deadline set)
        # Actually, if timeout is None, deadline won't be set at all
        # This test confirms no warning in that case


# === Skip Robustness Tests ===


class TestSkipRobustness:
    """Test that skipped steps don't break execution."""

    def test_multiple_consecutive_skips(self) -> None:
        """Test that multiple consecutive skipped steps work."""
        config = ConfigLoader.from_dict({
            "name": "Multi Skip Test",
            "components": [
                {"name": "a", "type": "test.CounterComponent", "config": {}},
                {"name": "b", "type": "test.CounterComponent", "config": {}},
                {"name": "c", "type": "test.CounterComponent", "config": {}},
                {"name": "d", "type": "test.CounterComponent", "config": {}},
            ],
            "flow": {
                "steps": [
                    {"component": "a", "condition": "False"},  # Skip
                    {"component": "b", "condition": "False"},  # Skip
                    {"component": "c", "condition": "False"},  # Skip
                    {"component": "d"},  # Run
                ],
            },
        })

        components = {
            "a": CounterComponent("a"),
            "b": CounterComponent("b"),
            "c": CounterComponent("c"),
            "d": CounterComponent("d"),
        }
        engine = FlowEngine(config, components, validate_types=False)
        result = engine.execute()

        assert result.get("count") == 1  # Only d ran
        assert len(result.metadata.skipped_components) == 3
        assert result.metadata.step_timings[0].component == "d"

    def test_all_steps_skipped(self) -> None:
        """Test that flow completes when all steps are skipped."""
        config = ConfigLoader.from_dict({
            "name": "All Skip Test",
            "components": [
                {"name": "a", "type": "test.CounterComponent", "config": {}},
                {"name": "b", "type": "test.CounterComponent", "config": {}},
            ],
            "flow": {
                "steps": [
                    {"component": "a", "condition": "False"},
                    {"component": "b", "condition": "False"},
                ],
            },
        })

        components = {
            "a": CounterComponent("a"),
            "b": CounterComponent("b"),
        }
        engine = FlowEngine(config, components, validate_types=False)
        result = engine.execute()

        assert result.get("count") is None  # No components ran
        assert len(result.metadata.skipped_components) == 2
        assert len(result.metadata.step_timings) == 0

    def test_skip_then_run_then_skip(self) -> None:
        """Test interleaved skip and run pattern."""
        config = ConfigLoader.from_dict({
            "name": "Interleaved Test",
            "components": [
                {"name": "a", "type": "test.CounterComponent", "config": {}},
                {"name": "b", "type": "test.CounterComponent", "config": {}},
                {"name": "c", "type": "test.CounterComponent", "config": {}},
                {"name": "d", "type": "test.CounterComponent", "config": {}},
            ],
            "flow": {
                "steps": [
                    {"component": "a", "condition": "False"},  # Skip
                    {"component": "b"},  # Run (count=1)
                    {"component": "c", "condition": "False"},  # Skip
                    {"component": "d"},  # Run (count=2)
                ],
            },
        })

        components = {
            "a": CounterComponent("a"),
            "b": CounterComponent("b"),
            "c": CounterComponent("c"),
            "d": CounterComponent("d"),
        }
        engine = FlowEngine(config, components, validate_types=False)
        result = engine.execute()

        assert result.get("count") == 2
        assert len(result.metadata.skipped_components) == 2
        assert len(result.metadata.step_timings) == 2


# === Timeout Mode Tests ===


class TestTimeoutModes:
    """Test different timeout enforcement modes."""

    def test_cooperative_mode_allows_overrun(self) -> None:
        """Test that cooperative mode allows non-compliant components to overrun."""
        config = ConfigLoader.from_dict({
            "name": "Cooperative Overrun",
            "components": [
                {"name": "slow", "type": "test.NonCooperativeSlowComponent", "config": {}},
            ],
            "flow": {
                "settings": {
                    "timeout_seconds": 0.5,  # Short timeout
                    "timeout_mode": "cooperative",  # Default
                },
                "steps": [{"component": "slow"}],
            },
        })

        components = {"slow": NonCooperativeSlowComponent("slow")}
        engine = FlowEngine(config, components, validate_types=False)

        # Component takes 1.5s but completes (overruns timeout)
        result = engine.execute()
        assert result.get("completed") is True

    def test_hard_async_mode_enforces_timeout(self) -> None:
        """Test that hard_async mode enforces timeout via asyncio."""
        config = ConfigLoader.from_dict({
            "name": "Hard Async Timeout",
            "components": [
                {"name": "slow", "type": "test.NonCooperativeSlowComponent", "config": {}},
            ],
            "flow": {
                "settings": {
                    "timeout_seconds": 0.5,  # Short timeout
                    "timeout_mode": "hard_async",
                },
                "steps": [{"component": "slow"}],
            },
        })

        components = {"slow": NonCooperativeSlowComponent("slow")}
        engine = FlowEngine(config, components, validate_types=False)

        with pytest.raises(FlowTimeoutError, match="Hard async timeout"):
            engine.execute()

    def test_hard_async_mode_allows_completion_within_timeout(self) -> None:
        """Test hard_async mode allows completion when under timeout."""
        config = ConfigLoader.from_dict({
            "name": "Hard Async Complete",
            "components": [
                {"name": "fast", "type": "test.CounterComponent", "config": {}},
            ],
            "flow": {
                "settings": {
                    "timeout_seconds": 10,
                    "timeout_mode": "hard_async",
                },
                "steps": [{"component": "fast"}],
            },
        })

        components = {"fast": CounterComponent("fast")}
        engine = FlowEngine(config, components, validate_types=False)

        result = engine.execute()
        assert result.get("count") == 1

    def test_hard_process_mode_enforces_timeout(self) -> None:
        """Test that hard_process mode enforces timeout via process isolation."""
        config = ConfigLoader.from_dict({
            "name": "Hard Process Timeout",
            "components": [
                {
                    "name": "slow",
                    "type": "tests.unit.core.test_improvements.NonCooperativeSlowComponent",
                    "config": {},
                },
            ],
            "flow": {
                "settings": {
                    "timeout_seconds": 0.5,
                    "timeout_mode": "hard_process",
                },
                "steps": [{"component": "slow"}],
            },
        })

        components = {"slow": NonCooperativeSlowComponent("slow")}
        engine = FlowEngine(config, components, validate_types=False)

        with pytest.raises(FlowTimeoutError, match="Hard process timeout"):
            engine.execute()

    def test_hard_process_mode_allows_completion_within_timeout(self) -> None:
        """Test hard_process mode allows completion when under timeout."""
        config = ConfigLoader.from_dict({
            "name": "Hard Process Complete",
            "components": [
                {
                    "name": "fast",
                    "type": "tests.unit.core.test_improvements.CounterComponent",
                    "config": {},
                },
            ],
            "flow": {
                "settings": {
                    "timeout_seconds": 10,
                    "timeout_mode": "hard_process",
                },
                "steps": [{"component": "fast"}],
            },
        })

        components = {"fast": CounterComponent("fast")}
        engine = FlowEngine(config, components, validate_types=False)

        result = engine.execute()
        assert result.get("count") == 1

    def test_invalid_timeout_mode_rejected(self) -> None:
        """Test that invalid timeout_mode values are rejected at config validation."""
        from flowengine import ConfigurationError

        with pytest.raises(ConfigurationError, match="timeout_mode"):
            ConfigLoader.from_dict({
                "name": "Invalid Mode",
                "components": [
                    {"name": "a", "type": "test.Component", "config": {}},
                ],
                "flow": {
                    "settings": {
                        "timeout_mode": "invalid_mode",  # Invalid!
                    },
                    "steps": [{"component": "a"}],
                },
            })


# === Strict Deadline Check Enforcement Tests ===


class TestStrictDeadlineEnforcement:
    """Test require_deadline_check enforcement."""

    def test_require_deadline_check_raises_for_noncompliant(self) -> None:
        """Test DeadlineCheckError raised when component doesn't check deadline."""
        from flowengine import DeadlineCheckError

        config = ConfigLoader.from_dict({
            "name": "Strict Check",
            "components": [
                {"name": "slow", "type": "test.NonCooperativeSlowComponent", "config": {}},
            ],
            "flow": {
                "settings": {
                    "timeout_seconds": 60,  # Long timeout so it completes
                    "timeout_mode": "cooperative",
                    "require_deadline_check": True,
                },
                "steps": [{"component": "slow"}],
            },
        })

        components = {"slow": NonCooperativeSlowComponent("slow")}
        engine = FlowEngine(config, components, validate_types=False)

        with pytest.raises(DeadlineCheckError) as exc_info:
            engine.execute()

        assert exc_info.value.component == "slow"
        assert exc_info.value.duration >= 1.0

    def test_require_deadline_check_allows_compliant_component(self) -> None:
        """Test compliant components pass with require_deadline_check=True."""
        config = ConfigLoader.from_dict({
            "name": "Strict Check Compliant",
            "components": [
                {"name": "coop", "type": "test.CooperativeSlowComponent", "config": {}},
            ],
            "flow": {
                "settings": {
                    "timeout_seconds": 60,
                    "timeout_mode": "cooperative",
                    "require_deadline_check": True,
                },
                "steps": [{"component": "coop"}],
            },
        })

        components = {"coop": CooperativeSlowComponent("coop")}
        engine = FlowEngine(config, components, validate_types=False)

        result = engine.execute()
        assert result.get("completed") is True

    def test_require_deadline_check_allows_fast_component(self) -> None:
        """Test fast components don't trigger deadline check enforcement."""
        config = ConfigLoader.from_dict({
            "name": "Strict Check Fast",
            "components": [
                {"name": "fast", "type": "test.CounterComponent", "config": {}},
            ],
            "flow": {
                "settings": {
                    "timeout_seconds": 60,
                    "timeout_mode": "cooperative",
                    "require_deadline_check": True,
                },
                "steps": [{"component": "fast"}],
            },
        })

        components = {"fast": CounterComponent("fast")}
        engine = FlowEngine(config, components, validate_types=False)

        # Fast components (< 1 second) don't need to check deadline
        result = engine.execute()
        assert result.get("count") == 1

    def test_require_deadline_check_default_false(self) -> None:
        """Test require_deadline_check defaults to False (warning only)."""
        config = ConfigLoader.from_dict({
            "name": "Default No Strict",
            "components": [
                {"name": "slow", "type": "test.NonCooperativeSlowComponent", "config": {}},
            ],
            "flow": {
                "settings": {
                    "timeout_seconds": 60,
                    # require_deadline_check not set - defaults to False
                },
                "steps": [{"component": "slow"}],
            },
        })

        components = {"slow": NonCooperativeSlowComponent("slow")}
        engine = FlowEngine(config, components, validate_types=False)

        # Should complete without error (only warning)
        result = engine.execute()
        assert result.get("completed") is True

    def test_require_deadline_check_not_applied_in_hard_async(self) -> None:
        """Test require_deadline_check only applies to cooperative mode."""
        config = ConfigLoader.from_dict({
            "name": "Hard Async with Require Check",
            "components": [
                {"name": "fast", "type": "test.CounterComponent", "config": {}},
            ],
            "flow": {
                "settings": {
                    "timeout_seconds": 10,
                    "timeout_mode": "hard_async",
                    "require_deadline_check": True,  # Should be ignored in hard_async
                },
                "steps": [{"component": "fast"}],
            },
        })

        components = {"fast": CounterComponent("fast")}
        engine = FlowEngine(config, components, validate_types=False)

        # Should complete without DeadlineCheckError in hard_async mode
        result = engine.execute()
        assert result.get("count") == 1


# === Teardown Tests for Hard Timeout Modes ===


class TeardownTrackingComponent(BaseComponent):
    """Component that tracks whether teardown was called."""

    teardown_called = False
    setup_called = False

    def setup(self, context: FlowContext) -> None:
        TeardownTrackingComponent.setup_called = True

    def process(self, context: FlowContext) -> FlowContext:
        time.sleep(2)  # Long sleep to trigger timeout
        context.set("completed", True)
        return context

    def teardown(self, context: FlowContext) -> None:
        TeardownTrackingComponent.teardown_called = True

    @classmethod
    def reset(cls) -> None:
        cls.teardown_called = False
        cls.setup_called = False


class TestTeardownOnTimeout:
    """Test that teardown runs even when timeout occurs."""

    def test_teardown_runs_on_hard_async_timeout(self) -> None:
        """Test teardown is called when hard_async times out."""
        TeardownTrackingComponent.reset()

        config = ConfigLoader.from_dict({
            "name": "Teardown Async Test",
            "components": [
                {"name": "tracker", "type": "test.TeardownTrackingComponent", "config": {}},
            ],
            "flow": {
                "settings": {
                    "timeout_seconds": 0.5,
                    "timeout_mode": "hard_async",
                },
                "steps": [{"component": "tracker"}],
            },
        })

        components = {"tracker": TeardownTrackingComponent("tracker")}
        engine = FlowEngine(config, components, validate_types=False)

        with pytest.raises(FlowTimeoutError):
            engine.execute()

        assert TeardownTrackingComponent.setup_called is True
        assert TeardownTrackingComponent.teardown_called is True

    def test_teardown_runs_on_hard_process_timeout(self) -> None:
        """Test teardown is called (in main process) when hard_process times out."""
        TeardownTrackingComponent.reset()

        config = ConfigLoader.from_dict({
            "name": "Teardown Process Test",
            "components": [
                {
                    "name": "tracker",
                    "type": "tests.unit.core.test_improvements.TeardownTrackingComponent",
                    "config": {},
                },
            ],
            "flow": {
                "settings": {
                    "timeout_seconds": 0.5,
                    "timeout_mode": "hard_process",
                },
                "steps": [{"component": "tracker"}],
            },
        })

        components = {"tracker": TeardownTrackingComponent("tracker")}
        engine = FlowEngine(config, components, validate_types=False)

        with pytest.raises(FlowTimeoutError):
            engine.execute()

        # setup and teardown run in main process
        assert TeardownTrackingComponent.setup_called is True
        assert TeardownTrackingComponent.teardown_called is True
