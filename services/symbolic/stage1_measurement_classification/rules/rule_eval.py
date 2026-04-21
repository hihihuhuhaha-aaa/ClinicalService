from __future__ import annotations

"""Rule expression evaluation utilities.

This module provides a safe AST-based evaluator for conditions and formulas
defined in the YAML rulebook.
"""

import ast
import operator
import re
from typing import Any

COMPARISON_OPERATORS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Is: operator.is_,
    ast.IsNot: operator.is_not,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}

BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
    ast.Not: operator.not_,
}


def _normalize_bool_map(expression: str) -> str:
    """Normalize YAML-style boolean operators and whitespace to Python syntax."""
    expression = re.sub(r"\bAND\b", "and", expression, flags=re.IGNORECASE)
    expression = re.sub(r"\bOR\b", "or", expression, flags=re.IGNORECASE)
    expression = re.sub(r"\bNOT\b", "not", expression, flags=re.IGNORECASE)
    expression = re.sub(r"\btrue\b", "True", expression, flags=re.IGNORECASE)
    expression = re.sub(r"\bfalse\b", "False", expression, flags=re.IGNORECASE)
    expression = re.sub(r"\bnull\b", "None", expression, flags=re.IGNORECASE)
    expression = re.sub(r"\s+", " ", expression).strip()
    return expression


def _eval_ast(node: ast.AST, context: dict[str, Any]) -> Any:
    """Evaluate an AST node recursively using a limited safe operator set."""
    if isinstance(node, ast.Expression):
        return _eval_ast(node.body, context)

    if isinstance(node, ast.BoolOp):
        values = [_eval_ast(value, context) for value in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        if isinstance(node.op, ast.Or):
            return any(values)

    if isinstance(node, ast.UnaryOp):
        if type(node.op) in UNARY_OPERATORS:
            return UNARY_OPERATORS[type(node.op)](_eval_ast(node.operand, context))

    if isinstance(node, ast.BinOp):
        left = _eval_ast(node.left, context)
        right = _eval_ast(node.right, context)
        if type(node.op) in BINARY_OPERATORS:
            return BINARY_OPERATORS[type(node.op)](left, right)

    if isinstance(node, ast.Compare):
        left = _eval_ast(node.left, context)
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval_ast(comparator, context)
            if type(op) not in COMPARISON_OPERATORS:
                raise ValueError(f"Unsupported comparison operator: {type(op).__name__}")
            if left is None or right is None:
                if isinstance(op, (ast.Is, ast.IsNot)):
                    pass
                else:
                    return False
            if not COMPARISON_OPERATORS[type(op)](left, right):
                return False
            left = right
        return True

    if isinstance(node, ast.Name):
        return context.get(node.id)

    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.Tuple):
        return tuple(_eval_ast(elt, context) for elt in node.elts)

    if isinstance(node, ast.List):
        return [_eval_ast(elt, context) for elt in node.elts]

    raise ValueError(f"Unsupported AST node: {type(node).__name__}")


def evaluate_condition(expression: str, context: dict[str, Any]) -> bool:
    """Evaluate a boolean condition from YAML against the provided context."""
    normalized = _normalize_bool_map(expression)
    try:
        parsed = ast.parse(normalized, mode="eval")
        result = _eval_ast(parsed, context)
        return bool(result)
    except Exception as exc:
        raise ValueError(f"Unable to evaluate condition '{expression}': {exc}") from exc


def evaluate_formula(expression: str, context: dict[str, Any]) -> float:
    """Evaluate a numeric formula from YAML and return its float result."""
    normalized = _normalize_bool_map(expression).strip()
    rhs = normalized.split("=", 1)[1].strip() if "=" in normalized else normalized
    parsed = ast.parse(rhs, mode="eval")
    result = _eval_ast(parsed, context)
    return float(result)
