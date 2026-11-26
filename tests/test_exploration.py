import numpy as np
import pytest

from src.assistant.console import load_scenarios
from src.assistant.copilot import answer
from src.exploration.data import archive, recovery, distribution, stages
from src.exploration.figures import flow, bridge, benchmark

M = load_scenarios(True)


def test_replay_comes_from_three_observed_snapshots_and_waterfall_reconciles():
    values = stages("medium", "CA déclaré")
    assert values == [72056406.6, 68137639.12, 68448127.94]
    plot = bridge(values, "M€").data[0]
    assert sum(plot.y[:3]) * 1e6 == pytest.approx(values[-1])
    assert stages("medium", "Doublons") == [0, 6000, 0]


@pytest.mark.parametrize("s", M)
def test_audit_link_and_populations(s):
    m = M[s]
    for orders, total in [(True, m["orders"]), (False, m["deliveries"])]:
        assert sum(flow(m, orders).data[0].link.value) == total
    _, audit = archive(s)
    assert (
        sum(audit["cleaning"]["remaining_alerts_by_type"].values())
        == audit["cleaning"]["remaining_alerts"]
    )
    resp = answer(
        "Après le nettoyage, que reste-t-il pour les références rompues ?", s, M
    )
    assert resp["intent"] == "audit" and resp["scenario"] == s
    assert f"/{s}/evaluation_summary.json" in resp["evidence"][0]
    assert "PostgreSQL" not in resp["evidence"][0]


def test_recovery_rounds_up_to_whole_days_and_doesnt_claim_repairs():
    m = M["medium"]
    assert recovery(m, 99.0, 500) == (4800, 10)
    assert recovery(m, 95.0, 500) == (0, 0)
    assert recovery(m, 100.0, 1) == (6000, 6000)
    with pytest.raises(ValueError):
        recovery(m, 92.0, 100)
    assert m["missing"] == 6000


def test_subjective_monte_carlo_rescales_with_assumed_basket():
    a = distribution(100, 0.15)
    b = distribution(150, 0.15)
    assert len(a) == 20000 and np.allclose(a * 1.5, b)
    assert np.quantile(distribution(100, 0.4), 0.95) > np.quantile(a, 0.95)


def test_coverage_comparison_keeps_each_denominator():
    chart = benchmark(M, ("medium", "critical"))
    assert list(chart.data[0].y) == ["Moyen", "Critique"]
    assert list(chart.data[0].customdata) == [114000, 108000]
    assert list(chart.data[1].customdata) == [6000, 12000]
    assert np.allclose(np.array(chart.data[0].x) + chart.data[1].x, 100)
