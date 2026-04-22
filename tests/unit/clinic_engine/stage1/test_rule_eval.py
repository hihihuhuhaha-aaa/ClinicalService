"""Unit tests for the AST-based rule evaluator."""
from __future__ import annotations

import pytest

from services.clinic_engine.stage1_measurement_classification.rules.rule_eval import (
    evaluate_condition,
    evaluate_formula,
)


# ---------------------------------------------------------------------------
# evaluate_condition
# ---------------------------------------------------------------------------

class TestEvaluateCondition:
    # --- basic comparisons ---
    def test_simple_gte_true(self):
        assert evaluate_condition("sys >= 140", {"sys": 145}) is True

    def test_simple_gte_false(self):
        assert evaluate_condition("sys >= 140", {"sys": 130}) is False

    def test_simple_lt_true(self):
        assert evaluate_condition("sys < 120", {"sys": 115}) is True

    def test_equality(self):
        assert evaluate_condition("level == 'high'", {"level": "high"}) is True

    def test_inequality(self):
        assert evaluate_condition("level != 'low'", {"level": "high"}) is True

    # --- boolean operators ---
    def test_and_true(self):
        assert evaluate_condition("sys >= 140 and dia >= 90", {"sys": 145, "dia": 92}) is True

    def test_and_false_when_one_fails(self):
        assert evaluate_condition("sys >= 140 and dia >= 90", {"sys": 145, "dia": 85}) is False

    def test_or_true_one_side(self):
        assert evaluate_condition("sys >= 140 or dia >= 90", {"sys": 130, "dia": 92}) is True

    def test_or_false_both_fail(self):
        assert evaluate_condition("sys >= 140 or dia >= 90", {"sys": 130, "dia": 85}) is False

    def test_not_true(self):
        assert evaluate_condition("not available", {"available": False}) is True

    def test_not_false(self):
        assert evaluate_condition("not available", {"available": True}) is False

    # --- YAML-style boolean words (case-insensitive) ---
    def test_uppercase_AND(self):
        assert evaluate_condition("sys >= 140 AND dia >= 90", {"sys": 145, "dia": 92}) is True

    def test_uppercase_OR(self):
        assert evaluate_condition("sys >= 140 OR dia >= 90", {"sys": 130, "dia": 92}) is True

    def test_true_literal(self):
        assert evaluate_condition("flag == true", {"flag": True}) is True

    def test_false_literal(self):
        assert evaluate_condition("flag == false", {"flag": False}) is True

    def test_null_literal(self):
        # null → None, nhưng None == None comparison trả False trong evaluator
        # (code trả False khi either side is None cho non-Is/IsNot ops)
        # Dùng "is" operator thay vào đó:
        assert evaluate_condition("value is null", {"value": None}) is True

    # --- context variable lookup ---
    def test_missing_variable_returns_false(self):
        # Variable không có trong context → None → comparison returns False
        assert evaluate_condition("missing_var >= 10", {}) is False

    def test_chained_comparison(self):
        # Python cho phép chained: 120 <= sys <= 139
        assert evaluate_condition("120 <= sys <= 139", {"sys": 130}) is True
        assert evaluate_condition("120 <= sys <= 139", {"sys": 145}) is False

    # --- special values ---
    def test_in_operator(self):
        assert evaluate_condition("status in ('high', 'medium')", {"status": "high"}) is True

    def test_not_in_operator(self):
        assert evaluate_condition("status not in ('high', 'medium')", {"status": "low"}) is True

    # --- error cases ---
    def test_invalid_syntax_raises_value_error(self):
        with pytest.raises(ValueError):
            evaluate_condition("sys >>=>> 140", {"sys": 145})

    def test_attribute_access_raises(self):
        with pytest.raises((ValueError, AttributeError)):
            evaluate_condition("obj.attr >= 1", {"obj": object()})


# ---------------------------------------------------------------------------
# evaluate_formula
# ---------------------------------------------------------------------------

class TestEvaluateFormula:
    def test_simple_addition(self):
        result = evaluate_formula("a + b", {"a": 1.0, "b": 2.0})
        assert result == pytest.approx(3.0)

    def test_weighted_sum(self):
        # score = 0.3 * a + 0.7 * b
        result = evaluate_formula("0.3 * a + 0.7 * b", {"a": 1.0, "b": 0.5})
        assert result == pytest.approx(0.65)

    def test_formula_with_assignment_prefix(self):
        # YAML thường dùng "score = 0.3 * a + 0.7 * b" → evaluator tự bỏ phần trước "="
        result = evaluate_formula("score = 0.3 * a + 0.7 * b", {"a": 1.0, "b": 0.5})
        assert result == pytest.approx(0.65)

    def test_subtraction_and_division(self):
        result = evaluate_formula("(a - b) / a * 100", {"a": 150.0, "b": 127.0})
        assert result == pytest.approx(15.333, abs=0.01)

    def test_power_operator(self):
        result = evaluate_formula("a ** 2", {"a": 3.0})
        assert result == pytest.approx(9.0)

    def test_returns_float(self):
        result = evaluate_formula("1 + 1", {})
        assert isinstance(result, float)

    def test_formula_clamped_at_zero(self):
        # Không phải behaviour của hàm — chỉ verify không crash khi kết quả âm
        result = evaluate_formula("a - b", {"a": 0.1, "b": 1.0})
        assert result == pytest.approx(-0.9)
