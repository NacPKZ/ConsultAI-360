import copy
import math

import pytest

from src.assistant.console import (
    REFERENCE,
    build_metrics,
    evidence,
    impact,
    load_scenarios,
    mission_note,
)


@pytest.mark.parametrize(
    "scenario,missing,coverage",
    [("low", 1200, 99), ("medium", 6000, 95), ("critical", 12000, 90)],
)
def test_reference_keeps_populations_separate(scenario, missing, coverage):
    metrics = load_scenarios(True)[scenario]
    assert metrics["missing"] == missing
    assert metrics["complete_pct"] == coverage
    assert metrics["late_pct"] == pytest.approx(100 * 10333 / 70005)
    assert metrics["known"] + metrics["missing"] == metrics["orders"]
    assert metrics["revenue_approximate"] is True


@pytest.mark.parametrize(
    "change",
    [
        {"orders": 0},
        {"missing": 120001},
        {"missing": -1},
        {"missing": 120000},
        {"deliveries": 0},
        {"late": 70006},
        {"late": -1},
        {"basket": math.nan},
        {"orders": 100.5},
        {"basket": -1},
    ],
)
def test_incoherent_kpis_are_rejected(change):
    with pytest.raises(ValueError):
        build_metrics({**REFERENCE["medium"], **change}, "reference")


def test_database_revenue_is_not_replaced_by_rounded_basket():
    m = build_metrics({**REFERENCE["medium"], "known_rev": 68448127.94}, "postgresql")
    assert m["known_rev"] == 68448127.94
    assert m["known_rev"] != m["known"] * m["basket"]
    assert evidence(m, "medium")["revenue"]["approximate"] is False


@pytest.mark.parametrize(
    "rate,ratio",
    [(-1, 1), (101, 1), (math.nan, 1), (5, 0), (5, -1), (5, math.inf), (5, 11)],
)
def test_hypothesis_rejects_invalid_inputs(rate, ratio):
    with pytest.raises(ValueError):
        impact(load_scenarios(True)["medium"], rate, ratio)


def test_hypothesis_does_not_change_observed_values():
    m = load_scenarios(True)["medium"]
    original = copy.deepcopy(m)
    simulated = impact(m, 15, 1.2)
    assert simulated["missing"] == 18000
    assert simulated["amount"] == pytest.approx(18000 * 600.42 * 1.2)
    assert m == original
    assert evidence(m, "medium")["hypothesis"]["measured_loss"] is False


def test_export_identifies_actual_source_and_reconstruction():
    m = load_scenarios(True)["critical"]
    payload = evidence(m, "critical")
    assert payload["source"] == "reference_figee"
    assert payload["revenue"]["approximate"] is True
    note = mission_note(m, "critical")
    assert "12\u202f000" in note
    assert "reconstitué" in note
    assert "référence figée" in note
