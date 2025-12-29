"""Tests for FlowEngine context module."""

import json

import pytest

from flowengine import DotDict, FlowContext
from flowengine.core.context import ExecutionMetadata


class TestDotDict:
    """Tests for DotDict class."""

    def test_init_empty(self) -> None:
        """Test initialization with no data."""
        d = DotDict()
        assert d.to_dict() == {}

    def test_init_with_data(self) -> None:
        """Test initialization with data."""
        d = DotDict({"key": "value"})
        assert d.to_dict() == {"key": "value"}

    def test_attribute_access(self) -> None:
        """Test accessing values as attributes."""
        d = DotDict({"user": {"name": "Alice"}})
        assert d.user.name == "Alice"

    def test_attribute_set(self) -> None:
        """Test setting values as attributes."""
        d = DotDict()
        d.user = {"name": "Bob"}
        assert d.user.name == "Bob"

    def test_nested_dict_wrapping(self) -> None:
        """Test nested dicts are wrapped as DotDict."""
        d = DotDict({"a": {"b": {"c": 1}}})
        assert d.a.b.c == 1
        assert isinstance(d.a, DotDict)
        assert isinstance(d.a.b, DotDict)

    def test_to_dict(self) -> None:
        """Test conversion to regular dict."""
        d = DotDict({"x": 1, "y": 2})
        result = d.to_dict()
        assert result == {"x": 1, "y": 2}
        assert isinstance(result, dict)
        assert not isinstance(result, DotDict)

    def test_get_with_default(self) -> None:
        """Test get method with default value."""
        d = DotDict({"exists": "value"})
        assert d.get("exists") == "value"
        assert d.get("missing", "default") == "default"
        assert d.get("missing") is None

    def test_contains(self) -> None:
        """Test 'in' operator."""
        d = DotDict({"key": "value"})
        assert "key" in d
        assert "missing" not in d

    def test_keys_values_items(self) -> None:
        """Test keys(), values(), items() methods."""
        d = DotDict({"a": 1, "b": 2})
        assert set(d.keys()) == {"a", "b"}
        assert set(d.values()) == {1, 2}
        assert set(d.items()) == {("a", 1), ("b", 2)}

    def test_update(self) -> None:
        """Test update method."""
        d = DotDict({"a": 1})
        d.update({"b": 2, "c": 3})
        assert d.to_dict() == {"a": 1, "b": 2, "c": 3}

    def test_equality(self) -> None:
        """Test equality comparison."""
        d1 = DotDict({"a": 1})
        d2 = DotDict({"a": 1})
        d3 = DotDict({"a": 2})

        assert d1 == d2
        assert d1 != d3
        assert d1 == {"a": 1}
        assert d1 != "not a dict"

    def test_repr(self) -> None:
        """Test string representation."""
        d = DotDict({"key": "value"})
        assert "DotDict" in repr(d)
        assert "key" in repr(d)

    def test_missing_attribute_returns_none(self) -> None:
        """Test accessing missing attribute returns None."""
        d = DotDict({"key": "value"})
        assert d.missing is None

    def test_dotdict_assignment_unwraps(self) -> None:
        """Test assigning DotDict unwraps to regular dict."""
        d = DotDict()
        inner = DotDict({"nested": "value"})
        d.outer = inner
        assert d._data["outer"] == {"nested": "value"}


class TestExecutionMetadata:
    """Tests for ExecutionMetadata class."""

    def test_init_defaults(self) -> None:
        """Test default values on initialization."""
        meta = ExecutionMetadata()
        assert meta.flow_id is not None
        assert meta.started_at is not None
        assert meta.completed_at is None
        assert meta.component_timings == {}
        assert meta.skipped_components == []
        assert meta.errors == []

    def test_add_error(self) -> None:
        """Test adding error records."""
        meta = ExecutionMetadata()
        error = ValueError("test error")
        meta.add_error("test_component", error)

        assert len(meta.errors) == 1
        assert meta.errors[0]["component"] == "test_component"
        assert meta.errors[0]["error_type"] == "ValueError"
        assert meta.errors[0]["message"] == "test error"
        assert "timestamp" in meta.errors[0]

    def test_record_timing(self) -> None:
        """Test recording component timing."""
        meta = ExecutionMetadata()
        meta.record_timing("component1", 1.5)
        meta.record_timing("component2", 0.5)

        assert meta.component_timings["component1"] == 1.5
        assert meta.component_timings["component2"] == 0.5

    def test_has_errors(self) -> None:
        """Test has_errors property."""
        meta = ExecutionMetadata()
        assert not meta.has_errors

        meta.add_error("comp", ValueError("error"))
        assert meta.has_errors

    def test_total_duration(self) -> None:
        """Test total_duration property."""
        from datetime import datetime, timedelta, timezone

        meta = ExecutionMetadata()
        meta.started_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        meta.completed_at = datetime.now(timezone.utc)

        assert meta.total_duration is not None
        assert meta.total_duration >= 4.9  # Allow for timing variance

    def test_total_duration_incomplete(self) -> None:
        """Test total_duration when not completed."""
        meta = ExecutionMetadata()
        assert meta.total_duration is None


class TestFlowContext:
    """Tests for FlowContext class."""

    def test_init_defaults(self) -> None:
        """Test default values on initialization."""
        ctx = FlowContext()
        assert isinstance(ctx.data, DotDict)
        assert isinstance(ctx.metadata, ExecutionMetadata)
        assert ctx.input is None

    def test_set_and_get(self) -> None:
        """Test set and get methods."""
        ctx = FlowContext()
        ctx.set("key", "value")
        assert ctx.get("key") == "value"

    def test_get_default(self) -> None:
        """Test get with default value."""
        ctx = FlowContext()
        assert ctx.get("missing", "default") == "default"

    def test_has(self) -> None:
        """Test has method."""
        ctx = FlowContext()
        ctx.set("exists", "value")
        assert ctx.has("exists")
        assert not ctx.has("missing")

    def test_delete(self) -> None:
        """Test delete method."""
        ctx = FlowContext()
        ctx.set("key", "value")
        assert ctx.has("key")
        ctx.delete("key")
        assert not ctx.has("key")

    def test_dot_access(self) -> None:
        """Test accessing data with dot notation."""
        ctx = FlowContext()
        ctx.set("user", {"name": "Alice", "age": 30})
        assert ctx.data.user.name == "Alice"
        assert ctx.data.user.age == 30

    def test_to_dict(self) -> None:
        """Test to_dict method."""
        ctx = FlowContext()
        ctx.set("test", 123)
        ctx.input = "input_data"

        result = ctx.to_dict()
        assert result["data"]["test"] == 123
        assert result["input"] == "input_data"
        assert "flow_id" in result
        assert "started_at" in result

    def test_to_json(self) -> None:
        """Test to_json method."""
        ctx = FlowContext()
        ctx.set("test", 123)

        json_str = ctx.to_json()
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["data"]["test"] == 123

    def test_from_dict(self) -> None:
        """Test creating context from dictionary."""
        data = {
            "data": {"key": "value"},
            "input": "test_input",
        }
        ctx = FlowContext.from_dict(data)

        assert ctx.get("key") == "value"
        assert ctx.input == "test_input"

    def test_copy(self) -> None:
        """Test copying context."""
        ctx = FlowContext()
        ctx.set("key", "value")
        ctx.input = "input"

        copy = ctx.copy()
        assert copy.get("key") == "value"
        assert copy.input == "input"

        # Verify it's a copy, not the same object
        copy.set("key", "modified")
        assert ctx.get("key") == "value"

    def test_metadata_tracking(self) -> None:
        """Test metadata tracking in context."""
        ctx = FlowContext()
        ctx.metadata.record_timing("comp1", 1.5)
        ctx.metadata.skipped_components.append("skipped_comp")
        ctx.metadata.add_error("comp2", ValueError("error"))

        result = ctx.to_dict()
        assert result["metadata"]["component_timings"]["comp1"] == 1.5
        assert "skipped_comp" in result["metadata"]["skipped_components"]
        assert len(result["metadata"]["errors"]) == 1
