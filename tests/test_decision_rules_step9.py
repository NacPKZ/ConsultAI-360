import pytest

from src.assistant.decision_rules import (
    DEFAULT_TH,
    gate,
    safe_th,
)


def test_valid_thresholds():
    th = dict(DEFAULT_TH)
    assert safe_th(th) == th


def test_invalid_thresholds():
    th = {
        "m_warn": 10,
        "m_fail": 5,
        "l_warn": 10,
        "l_fail": 20,
    }
    assert safe_th(th) == DEFAULT_TH


@pytest.mark.parametrize(
    "missing,late,expected",
    [
        (1, 5, "go"),
        (5, 15, "warn"),
        (10, 15, "stop"),
        (2, 25, "stop"),
        (8, 20, "warn"),
        (0, 0, "go"),
    ],
)
def test_decision_levels(missing, late, expected):
    data = {
        "missing_pct": missing,
        "late_pct": late,
    }
    assert gate(data, DEFAULT_TH)["overall"] == expected


def test_checks_structure():
    result = gate(
        {"missing_pct": 5, "late_pct": 14.76},
        DEFAULT_TH,
    )
    assert len(result["checks"]) == 2
    assert result["checks"][0][2] == "warn"
    assert result["checks"][1][2] == "warn"
    assert "14,76" in result["checks"][1][1]
