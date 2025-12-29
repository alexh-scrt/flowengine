"""Condition evaluator for safe expression evaluation.

This module provides the ConditionEvaluator class that safely
evaluates Python expressions against a FlowContext.
"""

from __future__ import annotations

import ast
import logging
from typing import TYPE_CHECKING

from flowengine.errors import ConditionEvaluationError
from flowengine.eval.safe_ast import SafeASTValidator

if TYPE_CHECKING:
    from flowengine.core.context import FlowContext

logger = logging.getLogger(__name__)


class ConditionEvaluator:
    """Safely evaluates condition expressions.

    Uses AST validation to ensure expressions don't contain
    dangerous constructs before evaluation.

    Example:
        ```python
        evaluator = ConditionEvaluator()
        context = FlowContext()
        context.set("user", {"active": True})

        result = evaluator.evaluate(
            "context.data.user.active == True",
            context
        )
        print(result)  # True
        ```
    """

    def __init__(self) -> None:
        """Initialize evaluator with AST validator."""
        self.validator = SafeASTValidator()

    def evaluate(self, condition: str, context: FlowContext) -> bool:
        """Evaluate a condition expression.

        Args:
            condition: Python expression string
            context: Current flow context

        Returns:
            Boolean result of evaluation

        Raises:
            ConditionEvaluationError: If condition is unsafe or invalid
        """
        # Parse to AST
        try:
            tree = ast.parse(condition, mode="eval")
        except SyntaxError as e:
            raise ConditionEvaluationError(
                f"Invalid syntax: {e}",
                condition=condition,
            ) from e

        # Validate safety
        if not self.validator.validate(tree):
            raise ConditionEvaluationError(
                f"Unsafe condition: {self.validator.errors}",
                condition=condition,
            )

        # Build safe namespace
        namespace = {
            "context": context,
            "True": True,
            "False": False,
            "None": None,
        }

        # Evaluate
        try:
            result = eval(
                compile(tree, "<condition>", "eval"),
                {"__builtins__": {}},
                namespace,
            )
            return bool(result)
        except Exception as e:
            # Runtime errors (e.g., AttributeError for missing attributes)
            # should be raised so they can be recorded in metadata
            raise ConditionEvaluationError(
                f"Runtime error evaluating condition: {e}",
                condition=condition,
            ) from e

    def is_safe(self, condition: str) -> bool:
        """Check if a condition is safe to evaluate.

        Args:
            condition: Python expression string

        Returns:
            True if condition passes safety validation
        """
        try:
            tree = ast.parse(condition, mode="eval")
            return self.validator.validate(tree)
        except SyntaxError:
            return False

    def validate(self, condition: str) -> list[str]:
        """Validate a condition and return any errors.

        Args:
            condition: Python expression string

        Returns:
            List of validation errors (empty if valid)
        """
        errors: list[str] = []

        try:
            tree = ast.parse(condition, mode="eval")
        except SyntaxError as e:
            errors.append(f"Syntax error: {e}")
            return errors

        if not self.validator.validate(tree):
            errors.extend(self.validator.errors)

        return errors
