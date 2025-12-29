"""Tests for FlowEngine logging component."""

import logging

import pytest

from flowengine import FlowContext
from flowengine.contrib.logging import LoggingComponent


class TestLoggingComponent:
    """Tests for LoggingComponent class."""

    @pytest.fixture
    def component(self) -> LoggingComponent:
        """Create a logging component instance."""
        comp = LoggingComponent("logger")
        comp.init({})
        return comp

    @pytest.fixture
    def context(self) -> FlowContext:
        """Create a context with test data."""
        ctx = FlowContext()
        ctx.set("user", {"name": "Alice", "active": True})
        ctx.set("count", 42)
        return ctx

    def test_init_defaults(self) -> None:
        """Test default configuration."""
        comp = LoggingComponent("logger")
        comp.init({})

        assert comp.level == "info"
        assert comp.message == "Context state"
        assert comp.log_data is True
        assert comp.log_metadata is False
        assert comp.keys is None

    def test_init_custom_config(self) -> None:
        """Test custom configuration."""
        comp = LoggingComponent("logger")
        comp.init({
            "level": "debug",
            "message": "Custom message",
            "log_data": False,
            "log_metadata": True,
            "keys": ["user", "count"],
        })

        assert comp.level == "debug"
        assert comp.message == "Custom message"
        assert comp.log_data is False
        assert comp.log_metadata is True
        assert comp.keys == ["user", "count"]

    def test_validate_config_valid(self) -> None:
        """Test validation with valid config."""
        comp = LoggingComponent("logger")
        comp.init({"level": "info"})

        errors = comp.validate_config()
        assert errors == []

    def test_validate_config_invalid_level(self) -> None:
        """Test validation with invalid log level."""
        comp = LoggingComponent("logger")
        comp.init({"level": "invalid"})

        errors = comp.validate_config()
        assert len(errors) == 1
        assert "level" in errors[0].lower()

    def test_validate_all_valid_levels(self) -> None:
        """Test all valid log levels."""
        for level in ["debug", "info", "warning", "error"]:
            comp = LoggingComponent("logger")
            comp.init({"level": level})
            errors = comp.validate_config()
            assert errors == [], f"Failed for level: {level}"

    def test_process_returns_context(
        self, component: LoggingComponent, context: FlowContext
    ) -> None:
        """Test process returns the context unchanged."""
        result = component.process(context)

        assert result is context
        assert result.get("user") == {"name": "Alice", "active": True}
        assert result.get("count") == 42

    def test_process_logs_message(
        self, component: LoggingComponent, context: FlowContext, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test process logs the message."""
        with caplog.at_level(logging.INFO):
            component.process(context)

        assert "Context state" in caplog.text

    def test_process_logs_data(
        self, context: FlowContext, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test process logs context data."""
        comp = LoggingComponent("logger")
        comp.init({"level": "info", "log_data": True})

        with caplog.at_level(logging.INFO):
            comp.process(context)

        assert "Data:" in caplog.text
        assert "user" in caplog.text
        assert "count" in caplog.text

    def test_process_logs_specific_keys(
        self, context: FlowContext, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test process logs only specified keys."""
        comp = LoggingComponent("logger")
        comp.init({"level": "info", "keys": ["user"]})

        with caplog.at_level(logging.INFO):
            comp.process(context)

        assert "user" in caplog.text
        # count should not be in output since we only specified "user"

    def test_process_logs_metadata(
        self, context: FlowContext, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test process logs execution metadata."""
        context.metadata.record_timing("comp1", 1.5)
        context.metadata.skipped_components.append("skipped")

        comp = LoggingComponent("logger")
        comp.init({"level": "info", "log_metadata": True, "log_data": False})

        with caplog.at_level(logging.INFO):
            comp.process(context)

        assert "Metadata:" in caplog.text
        assert "flow_id" in caplog.text

    def test_process_no_data(
        self, context: FlowContext, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test process with log_data=False."""
        comp = LoggingComponent("logger")
        comp.init({"level": "info", "log_data": False})

        with caplog.at_level(logging.INFO):
            comp.process(context)

        assert "Context state" in caplog.text
        assert "Data:" not in caplog.text

    def test_different_log_levels(
        self, context: FlowContext, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test logging at different levels."""
        for level in ["debug", "info", "warning", "error"]:
            comp = LoggingComponent(f"logger_{level}")
            comp.init({"level": level, "message": f"Test {level}"})

            with caplog.at_level(getattr(logging, level.upper())):
                comp.process(context)

            assert f"Test {level}" in caplog.text
            caplog.clear()
