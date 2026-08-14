"""
Calculator Tool — Perform mathematical calculations.
"""

from __future__ import annotations

import ast
import logging
import math
import operator
from typing import Any, ClassVar

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class _MathEvaluator:
    """Safe AST-based evaluator for arithmetic expressions.

    Only a whitelist of operators, functions, and constants is accepted;
    arbitrary Python is never executed.
    """

    _BIN_OPS: ClassVar[dict[type[ast.operator], Any]] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }

    _UNARY_OPS: ClassVar[dict[type[ast.unaryop], Any]] = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    _FUNCTIONS: ClassVar[dict[str, Any]] = {
        "abs": abs,
        "min": min,
        "max": max,
        "sum": sum,
        "round": round,
        "pow": pow,
        "sqrt": math.sqrt,
        "log": math.log,
        "log10": math.log10,
        "log2": math.log2,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,
        "ceil": math.ceil,
        "floor": math.floor,
        "degrees": math.degrees,
        "radians": math.radians,
    }

    _CONSTANTS: ClassVar[dict[str, Any]] = {
        "pi": math.pi,
        "e": math.e,
        "tau": math.tau,
    }

    def __init__(self, expression: str) -> None:
        self._tree = ast.parse(expression, mode="eval")

    def evaluate(self) -> float:
        """Evaluate the parsed expression."""
        val = self._eval(self._tree.body)
        return float(val)

    def _eval(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("Only numeric literals are allowed.")
        if isinstance(node, ast.BinOp):
            op = self._BIN_OPS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            return op(self._eval(node.left), self._eval(node.right))
        if isinstance(node, ast.UnaryOp):
            op = self._UNARY_OPS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            return op(self._eval(node.operand))
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in self._FUNCTIONS:
                raise ValueError("Only whitelisted math functions are allowed.")
            if node.keywords:
                raise ValueError("Keyword arguments are not supported.")
            args = [self._eval(a) for a in node.args]
            return self._FUNCTIONS[node.func.id](*args)
        if isinstance(node, ast.Name):
            if node.id in self._CONSTANTS:
                return self._CONSTANTS[node.id]
            raise ValueError(f"Unknown name: {node.id}")
        raise ValueError(f"Unsupported expression element: {type(node).__name__}")


class CalculatorTool(BaseTool):
    """Evaluate mathematical expressions safely."""

    schema = ToolSchema(
        name="calculator",
        description="Evaluate a mathematical expression. Supports arithmetic, powers, "
        "roots, and common math functions.",
        category="basic",
        parameters=[
            ToolParameter(
                name="expression",
                type="string",
                description="Mathematical expression to evaluate "
                "(e.g., '2 + 3 * 4', 'sqrt(16)', 'pi * 2')",
            ),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        """Evaluate a math expression."""
        expression = kwargs["expression"]
        try:
            result = _MathEvaluator(expression).evaluate()
            return str(result)
        except Exception as e:
            return f"Error evaluating '{expression}': {e}"
