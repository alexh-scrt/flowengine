"""Tests for FlowEngine component module."""

import pytest

from flowengine import BaseComponent, FlowContext


class SimpleComponent(BaseComponent):
    """Simple test component implementation."""

    def process(self, context: FlowContext) -> FlowContext:
        context.set("processed", True)
        return context


class ConfiguredComponent(BaseComponent):
    """Component with config-dependent behavior."""

    def init(self, config: dict) -> None:
        super().init(config)
        self.prefix = config.get("prefix", "")

    def validate_config(self) -> list[str]:
        errors = super().validate_config()
        if "required" not in self.config:
            errors.append("'required' config key is missing")
        return errors

    def process(self, context: FlowContext) -> FlowContext:
        message = context.get("message", "")
        context.set("result", f"{self.prefix}{message}")
        return context


class LifecycleTrackingComponent(BaseComponent):
    """Component that tracks lifecycle method calls."""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.lifecycle_calls: list[str] = []

    def init(self, config: dict) -> None:
        super().init(config)
        self.lifecycle_calls.append("init")

    def setup(self, context: FlowContext) -> None:
        self.lifecycle_calls.append("setup")

    def process(self, context: FlowContext) -> FlowContext:
        self.lifecycle_calls.append("process")
        return context

    def teardown(self, context: FlowContext) -> None:
        self.lifecycle_calls.append("teardown")


class TestBaseComponent:
    """Tests for BaseComponent class."""

    def test_init(self) -> None:
        """Test component initialization."""
        comp = SimpleComponent("test")
        assert comp.name == "test"
        assert comp.config == {}
        assert not comp.is_initialized

    def test_name_property(self) -> None:
        """Test name property is read-only."""
        comp = SimpleComponent("my_component")
        assert comp.name == "my_component"

    def test_init_method(self) -> None:
        """Test init method sets config and initialized flag."""
        comp = SimpleComponent("test")
        comp.init({"key": "value"})

        assert comp.is_initialized
        assert comp.config == {"key": "value"}

    def test_process_abstract(self) -> None:
        """Test process method must be implemented."""
        with pytest.raises(TypeError):
            BaseComponent("test")  # type: ignore

    def test_process_execution(self) -> None:
        """Test process method execution."""
        comp = SimpleComponent("test")
        comp.init({})

        ctx = FlowContext()
        result = comp.process(ctx)

        assert result.get("processed") is True

    def test_setup_default(self) -> None:
        """Test setup method has default implementation."""
        comp = SimpleComponent("test")
        comp.init({})
        ctx = FlowContext()

        # Should not raise
        comp.setup(ctx)

    def test_teardown_default(self) -> None:
        """Test teardown method has default implementation."""
        comp = SimpleComponent("test")
        comp.init({})
        ctx = FlowContext()

        # Should not raise
        comp.teardown(ctx)

    def test_validate_config_default(self) -> None:
        """Test validate_config returns empty list by default."""
        comp = SimpleComponent("test")
        comp.init({})

        errors = comp.validate_config()
        assert errors == []

    def test_validate_config_custom(self) -> None:
        """Test custom validate_config implementation."""
        comp = ConfiguredComponent("test")
        comp.init({})  # Missing 'required' key

        errors = comp.validate_config()
        assert len(errors) == 1
        assert "required" in errors[0]

    def test_validate_config_passes(self) -> None:
        """Test validate_config when config is valid."""
        comp = ConfiguredComponent("test")
        comp.init({"required": "value"})

        errors = comp.validate_config()
        assert errors == []

    def test_health_check_default(self) -> None:
        """Test health_check returns initialization status."""
        comp = SimpleComponent("test")
        assert not comp.health_check()

        comp.init({})
        assert comp.health_check()

    def test_repr(self) -> None:
        """Test string representation."""
        comp = SimpleComponent("my_component")
        repr_str = repr(comp)

        assert "SimpleComponent" in repr_str
        assert "my_component" in repr_str

    def test_lifecycle_order(self) -> None:
        """Test lifecycle methods are called in correct order."""
        comp = LifecycleTrackingComponent("test")
        ctx = FlowContext()

        comp.init({})
        comp.setup(ctx)
        comp.process(ctx)
        comp.teardown(ctx)

        assert comp.lifecycle_calls == ["init", "setup", "process", "teardown"]

    def test_config_access_in_process(self) -> None:
        """Test config is accessible in process method."""
        comp = ConfiguredComponent("test")
        comp.init({"prefix": "Hello, ", "required": True})

        ctx = FlowContext()
        ctx.set("message", "World")
        result = comp.process(ctx)

        assert result.get("result") == "Hello, World"

    def test_multiple_components_independent(self) -> None:
        """Test multiple component instances are independent."""
        comp1 = SimpleComponent("comp1")
        comp2 = SimpleComponent("comp2")

        comp1.init({"key1": "value1"})
        comp2.init({"key2": "value2"})

        assert comp1.config == {"key1": "value1"}
        assert comp2.config == {"key2": "value2"}
        assert comp1.name != comp2.name
