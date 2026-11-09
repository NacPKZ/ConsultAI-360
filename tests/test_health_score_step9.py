from src.assistant.health_score import health


def test_health_medium():
    result = health(
        {
            "missing_pct": 5.0,
            "late_pct": 14.76,
        }
    )
    assert result["score"] == 73.2


def test_health_perfect():
    result = health(
        {
            "missing_pct": 0.0,
            "late_pct": 0.0,
        }
    )
    assert result["score"] == 100.0


def test_health_components():
    result = health(
        {
            "missing_pct": 5.0,
            "late_pct": 14.76,
        }
    )
    assert result["comp"] == 75.0
    assert result["punct"] == 70.48
