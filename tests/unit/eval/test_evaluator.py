"""Tests for FlowEngine condition evaluator."""

import pytest

from flowengine import ConditionEvaluationError, ConditionEvaluator, FlowContext


class TestConditionEvaluator:
    """Tests for ConditionEvaluator class."""

    @pytest.fixture
    def evaluator(self) -> ConditionEvaluator:
        """Create an evaluator instance."""
        return ConditionEvaluator()

    @pytest.fixture
    def context(self) -> FlowContext:
        """Create a context with test data."""
        ctx = FlowContext()
        ctx.set("user", {"name": "Alice", "age": 30, "active": True})
        ctx.set("numbers", [1, 2, 3, 4, 5])
        ctx.set("count", 10)
        ctx.set("status", "success")
        return ctx

    # === Valid conditions ===

    def test_simple_comparison(
        self, evaluator: ConditionEvaluator, context: FlowContext
    ) -> None:
        """Test simple comparison evaluation."""
        assert evaluator.evaluate("context.data.count > 5", context)
        assert not evaluator.evaluate("context.data.count > 15", context)

    def test_equality(
        self, evaluator: ConditionEvaluator, context: FlowContext
    ) -> None:
        """Test equality evaluation."""
        assert evaluator.evaluate("context.data.status == 'success'", context)
        assert not evaluator.evaluate("context.data.status == 'failure'", context)

    def test_boolean_value(
        self, evaluator: ConditionEvaluator, context: FlowContext
    ) -> None:
        """Test boolean value evaluation."""
        assert evaluator.evaluate("context.data.user.active == True", context)
        assert evaluator.evaluate("context.data.user.active", context)

    def test_nested_attribute(
        self, evaluator: ConditionEvaluator, context: FlowContext
    ) -> None:
        """Test nested attribute access."""
        assert evaluator.evaluate("context.data.user.age > 25", context)
        assert evaluator.evaluate("context.data.user.name == 'Alice'", context)

    def test_boolean_and(
        self, evaluator: ConditionEvaluator, context: FlowContext
    ) -> None:
        """Test boolean AND."""
        assert evaluator.evaluate(
            "context.data.user.active and context.data.count > 5",
            context,
        )
        assert not evaluator.evaluate(
            "context.data.user.active and context.data.count > 15",
            context,
        )

    def test_boolean_or(
        self, evaluator: ConditionEvaluator, context: FlowContext
    ) -> None:
        """Test boolean OR."""
        assert evaluator.evaluate(
            "context.data.count > 15 or context.data.user.active",
            context,
        )

    def test_boolean_not(
        self, evaluator: ConditionEvaluator, context: FlowContext
    ) -> None:
        """Test boolean NOT."""
        assert evaluator.evaluate("not context.data.status == 'failure'", context)

    def test_is_none(
        self, evaluator: ConditionEvaluator, context: FlowContext
    ) -> None:
        """Test is None check."""
        assert evaluator.evaluate("context.data.missing is None", context)
        assert not evaluator.evaluate("context.data.user is None", context)

    def test_is_not_none(
        self, evaluator: ConditionEvaluator, context: FlowContext
    ) -> None:
        """Test is not None check."""
        assert evaluator.evaluate("context.data.user is not None", context)
        assert not evaluator.evaluate("context.data.missing is not None", context)

    def test_in_operator(
        self, evaluator: ConditionEvaluator, context: FlowContext
    ) -> None:
        """Test in operator."""
        assert evaluator.evaluate("3 in context.data.numbers", context)
        assert not evaluator.evaluate("10 in context.data.numbers", context)

    def test_not_in_operator(
        self, evaluator: ConditionEvaluator, context: FlowContext
    ) -> None:
        """Test not in operator."""
        assert evaluator.evaluate("10 not in context.data.numbers", context)
        assert not evaluator.evaluate("3 not in context.data.numbers", context)

    def test_complex_condition(
        self, evaluator: ConditionEvaluator, context: FlowContext
    ) -> None:
        """Test complex condition."""
        condition = (
            "(context.data.user.active and context.data.count >= 10) "
            "or context.data.status == 'override'"
        )
        assert evaluator.evaluate(condition, context)

    def test_arithmetic(
        self, evaluator: ConditionEvaluator, context: FlowContext
    ) -> None:
        """Test arithmetic in condition."""
        assert evaluator.evaluate("context.data.count + 5 > 10", context)
        assert evaluator.evaluate("context.data.user.age * 2 == 60", context)

    # === Invalid/unsafe conditions ===

    def test_function_call_rejected(
        self, evaluator: ConditionEvaluator, context: FlowContext
    ) -> None:
        """Test function calls are rejected."""
        with pytest.raises(ConditionEvaluationError, match="[Uu]nsafe"):
            evaluator.evaluate("len(context.data.items) > 0", context)

    def test_builtin_rejected(
        self, evaluator: ConditionEvaluator, context: FlowContext
    ) -> None:
        """Test builtins are rejected."""
        with pytest.raises(ConditionEvaluationError, match="[Uu]nsafe"):
            evaluator.evaluate("print('hello')", context)

    def test_method_call_rejected(
        self, evaluator: ConditionEvaluator, context: FlowContext
    ) -> None:
        """Test method calls are rejected."""
        with pytest.raises(ConditionEvaluationError, match="[Uu]nsafe"):
            evaluator.evaluate("context.data.status.upper() == 'SUCCESS'", context)

    def test_syntax_error(
        self, evaluator: ConditionEvaluator, context: FlowContext
    ) -> None:
        """Test syntax errors raise appropriate exception."""
        with pytest.raises(ConditionEvaluationError, match="[Ss]yntax"):
            evaluator.evaluate("x > > 5", context)

    def test_evaluation_error_raises(
        self, evaluator: ConditionEvaluator, context: FlowContext
    ) -> None:
        """Test runtime evaluation errors raise ConditionEvaluationError."""
        # This will try to compare with undefined variable
        with pytest.raises(ConditionEvaluationError, match="[Rr]untime"):
            evaluator.evaluate("undefined_var > 5", context)

    # === is_safe method ===

    def test_is_safe_valid(self, evaluator: ConditionEvaluator) -> None:
        """Test is_safe with valid condition."""
        assert evaluator.is_safe("x > 5")
        assert evaluator.is_safe("x == 'value' and y < 10")

    def test_is_safe_invalid(self, evaluator: ConditionEvaluator) -> None:
        """Test is_safe with invalid condition."""
        assert not evaluator.is_safe("len(x) > 0")
        assert not evaluator.is_safe("print('hello')")

    def test_is_safe_syntax_error(self, evaluator: ConditionEvaluator) -> None:
        """Test is_safe with syntax error."""
        assert not evaluator.is_safe("x > > 5")

    # === validate method ===

    def test_validate_valid(self, evaluator: ConditionEvaluator) -> None:
        """Test validate with valid condition."""
        errors = evaluator.validate("x > 5")
        assert errors == []

    def test_validate_invalid(self, evaluator: ConditionEvaluator) -> None:
        """Test validate with invalid condition."""
        errors = evaluator.validate("len(x) > 0")
        assert len(errors) > 0
        assert any("Call" in e for e in errors)

    def test_validate_syntax_error(self, evaluator: ConditionEvaluator) -> None:
        """Test validate with syntax error."""
        errors = evaluator.validate("x > > 5")
        assert len(errors) > 0
        assert any("syntax" in e.lower() for e in errors)

    # === Edge cases ===

    def test_empty_context(self, evaluator: ConditionEvaluator) -> None:
        """Test with empty context."""
        ctx = FlowContext()
        # Should return False since missing data evaluates to None
        result = evaluator.evaluate("context.data.something is not None", ctx)
        assert result is False

    def test_true_constant(
        self, evaluator: ConditionEvaluator, context: FlowContext
    ) -> None:
        """Test True constant."""
        assert evaluator.evaluate("True", context)

    def test_false_constant(
        self, evaluator: ConditionEvaluator, context: FlowContext
    ) -> None:
        """Test False constant."""
        assert not evaluator.evaluate("False", context)

    def test_none_constant(
        self, evaluator: ConditionEvaluator, context: FlowContext
    ) -> None:
        """Test None constant."""
        assert not evaluator.evaluate("None", context)  # bool(None) is False

    def test_context_input(
        self, evaluator: ConditionEvaluator, context: FlowContext
    ) -> None:
        """Test accessing context.input."""
        context.input = {"key": "value"}
        assert evaluator.evaluate("context.input is not None", context)
