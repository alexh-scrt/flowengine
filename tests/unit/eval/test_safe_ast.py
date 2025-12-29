"""Tests for FlowEngine safe AST validator."""

import ast

import pytest

from flowengine.eval.safe_ast import SafeASTValidator


class TestSafeASTValidator:
    """Tests for SafeASTValidator class."""

    @pytest.fixture
    def validator(self) -> SafeASTValidator:
        """Create a validator instance."""
        return SafeASTValidator()

    # === Allowed expressions ===

    def test_simple_comparison(self, validator: SafeASTValidator) -> None:
        """Test simple comparison is allowed."""
        tree = ast.parse("x > 5", mode="eval")
        assert validator.validate(tree)

    def test_equality(self, validator: SafeASTValidator) -> None:
        """Test equality comparison is allowed."""
        tree = ast.parse("x == 'value'", mode="eval")
        assert validator.validate(tree)

    def test_not_equal(self, validator: SafeASTValidator) -> None:
        """Test not equal comparison is allowed."""
        tree = ast.parse("x != 'value'", mode="eval")
        assert validator.validate(tree)

    def test_less_than(self, validator: SafeASTValidator) -> None:
        """Test less than comparison is allowed."""
        tree = ast.parse("x < 10", mode="eval")
        assert validator.validate(tree)

    def test_less_than_equal(self, validator: SafeASTValidator) -> None:
        """Test less than or equal comparison is allowed."""
        tree = ast.parse("x <= 10", mode="eval")
        assert validator.validate(tree)

    def test_greater_than_equal(self, validator: SafeASTValidator) -> None:
        """Test greater than or equal comparison is allowed."""
        tree = ast.parse("x >= 10", mode="eval")
        assert validator.validate(tree)

    def test_boolean_and(self, validator: SafeASTValidator) -> None:
        """Test boolean AND is allowed."""
        tree = ast.parse("x > 0 and y < 10", mode="eval")
        assert validator.validate(tree)

    def test_boolean_or(self, validator: SafeASTValidator) -> None:
        """Test boolean OR is allowed."""
        tree = ast.parse("x > 0 or y < 10", mode="eval")
        assert validator.validate(tree)

    def test_boolean_not(self, validator: SafeASTValidator) -> None:
        """Test boolean NOT is allowed."""
        tree = ast.parse("not x", mode="eval")
        assert validator.validate(tree)

    def test_is_none(self, validator: SafeASTValidator) -> None:
        """Test 'is None' is allowed."""
        tree = ast.parse("x is None", mode="eval")
        assert validator.validate(tree)

    def test_is_not_none(self, validator: SafeASTValidator) -> None:
        """Test 'is not None' is allowed."""
        tree = ast.parse("x is not None", mode="eval")
        assert validator.validate(tree)

    def test_in_operator(self, validator: SafeASTValidator) -> None:
        """Test 'in' operator is allowed."""
        tree = ast.parse("x in [1, 2, 3]", mode="eval")
        assert validator.validate(tree)

    def test_not_in_operator(self, validator: SafeASTValidator) -> None:
        """Test 'not in' operator is allowed."""
        tree = ast.parse("x not in [1, 2, 3]", mode="eval")
        assert validator.validate(tree)

    def test_attribute_access(self, validator: SafeASTValidator) -> None:
        """Test attribute access is allowed."""
        tree = ast.parse("context.data.user.name", mode="eval")
        assert validator.validate(tree)

    def test_subscript(self, validator: SafeASTValidator) -> None:
        """Test subscript access is allowed."""
        tree = ast.parse("context.data['key']", mode="eval")
        assert validator.validate(tree)

    def test_constants(self, validator: SafeASTValidator) -> None:
        """Test constants are allowed."""
        for expr in ["True", "False", "None", "42", "'string'", "3.14"]:
            tree = ast.parse(expr, mode="eval")
            assert validator.validate(tree), f"Failed for: {expr}"

    def test_list_literal(self, validator: SafeASTValidator) -> None:
        """Test list literals are allowed."""
        tree = ast.parse("[1, 2, 3]", mode="eval")
        assert validator.validate(tree)

    def test_tuple_literal(self, validator: SafeASTValidator) -> None:
        """Test tuple literals are allowed."""
        tree = ast.parse("(1, 2, 3)", mode="eval")
        assert validator.validate(tree)

    def test_dict_literal(self, validator: SafeASTValidator) -> None:
        """Test dict literals are allowed."""
        tree = ast.parse("{'a': 1}", mode="eval")
        assert validator.validate(tree)

    def test_arithmetic_in_condition(self, validator: SafeASTValidator) -> None:
        """Test arithmetic operations are allowed."""
        tree = ast.parse("x + 1 > 5", mode="eval")
        assert validator.validate(tree)

    def test_complex_expression(self, validator: SafeASTValidator) -> None:
        """Test complex but safe expression."""
        expr = "(context.data.count > 0 and context.data.status == 'active') or context.data.override"
        tree = ast.parse(expr, mode="eval")
        assert validator.validate(tree)

    def test_ternary_expression(self, validator: SafeASTValidator) -> None:
        """Test ternary/conditional expression is allowed."""
        tree = ast.parse("x if y > 0 else z", mode="eval")
        assert validator.validate(tree)

    # === Disallowed expressions ===

    def test_function_call_rejected(self, validator: SafeASTValidator) -> None:
        """Test function calls are rejected."""
        tree = ast.parse("len(x)", mode="eval")
        assert not validator.validate(tree)
        assert any("Call" in e for e in validator.errors)

    def test_builtin_call_rejected(self, validator: SafeASTValidator) -> None:
        """Test builtin calls are rejected."""
        tree = ast.parse("print('hello')", mode="eval")
        assert not validator.validate(tree)

    def test_method_call_rejected(self, validator: SafeASTValidator) -> None:
        """Test method calls are rejected."""
        tree = ast.parse("x.upper()", mode="eval")
        assert not validator.validate(tree)

    def test_lambda_rejected(self, validator: SafeASTValidator) -> None:
        """Test lambda expressions are rejected."""
        tree = ast.parse("lambda x: x + 1", mode="eval")
        assert not validator.validate(tree)

    def test_list_comprehension_rejected(self, validator: SafeASTValidator) -> None:
        """Test list comprehensions are rejected."""
        tree = ast.parse("[x for x in items]", mode="eval")
        assert not validator.validate(tree)

    def test_dict_comprehension_rejected(self, validator: SafeASTValidator) -> None:
        """Test dict comprehensions are rejected."""
        tree = ast.parse("{k: v for k, v in items}", mode="eval")
        assert not validator.validate(tree)

    def test_generator_rejected(self, validator: SafeASTValidator) -> None:
        """Test generator expressions are rejected."""
        tree = ast.parse("(x for x in items)", mode="eval")
        assert not validator.validate(tree)

    def test_get_errors(self, validator: SafeASTValidator) -> None:
        """Test get_errors returns copy of errors."""
        tree = ast.parse("len(x)", mode="eval")
        validator.validate(tree)

        errors = validator.get_errors()
        assert len(errors) > 0

        # Verify it's a copy
        errors.clear()
        assert len(validator.errors) > 0

    def test_errors_reset_on_validate(self, validator: SafeASTValidator) -> None:
        """Test errors are reset on each validate call."""
        # First validation with error
        tree1 = ast.parse("len(x)", mode="eval")
        validator.validate(tree1)
        assert len(validator.errors) > 0

        # Second validation without error
        tree2 = ast.parse("x > 5", mode="eval")
        assert validator.validate(tree2)
        assert len(validator.errors) == 0
