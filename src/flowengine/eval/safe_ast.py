"""Safe AST validation for condition expressions.

This module provides AST validation to ensure condition expressions
are safe to evaluate. It prevents code injection by rejecting
dangerous constructs like function calls, imports, and assignments.
"""

import ast
from typing import ClassVar


class SafeASTValidator(ast.NodeVisitor):
    """Validates that an AST only contains safe nodes.

    Prevents code injection by rejecting:
    - Function calls
    - Imports
    - Attribute assignment
    - Lambda/comprehensions
    - Any assignment operations

    Example:
        ```python
        validator = SafeASTValidator()

        # Safe expression
        tree = ast.parse("x > 5 and y == 'test'", mode='eval')
        assert validator.validate(tree)

        # Unsafe expression (function call)
        tree = ast.parse("len(items) > 0", mode='eval')
        assert not validator.validate(tree)
        print(validator.errors)  # ["Disallowed node type: Call"]
        ```
    """

    ALLOWED_NODES: ClassVar[frozenset[type[ast.AST]]] = frozenset(
        {
            # Expressions
            ast.Expression,
            ast.BoolOp,
            ast.Compare,
            ast.UnaryOp,
            ast.BinOp,
            ast.IfExp,
            # Boolean operators
            ast.And,
            ast.Or,
            ast.Not,
            # Comparison operators
            ast.Eq,
            ast.NotEq,
            ast.Lt,
            ast.LtE,
            ast.Gt,
            ast.GtE,
            ast.Is,
            ast.IsNot,
            ast.In,
            ast.NotIn,
            # Binary operators (for arithmetic in conditions)
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.Div,
            ast.Mod,
            ast.FloorDiv,
            # Values
            ast.Constant,
            ast.Name,
            ast.Attribute,
            ast.Load,
            # Subscript access
            ast.Subscript,
            ast.Slice,
            # Collections (for literals like [1, 2, 3])
            ast.List,
            ast.Tuple,
            ast.Dict,
            ast.Set,
        }
    )

    def __init__(self) -> None:
        """Initialize validator with empty error list."""
        self.errors: list[str] = []

    def validate(self, node: ast.AST) -> bool:
        """Validate entire AST tree.

        Args:
            node: Root AST node to validate

        Returns:
            True if all nodes are safe, False otherwise
        """
        self.errors = []
        self.visit(node)
        return len(self.errors) == 0

    def generic_visit(self, node: ast.AST) -> None:
        """Check each node against allowlist.

        Args:
            node: AST node to check
        """
        if type(node) not in self.ALLOWED_NODES:
            self.errors.append(f"Disallowed node type: {type(node).__name__}")
        super().generic_visit(node)

    def get_errors(self) -> list[str]:
        """Get list of validation errors.

        Returns:
            List of error messages
        """
        return self.errors.copy()
