import pytest

from src.assistant.console import (
    DEFAULT_TH, SCENARIOS, conversational_answer, evidence_payload,
    metrics_from_reference, monte_carlo,
)


@pytest.fixture
def metrics():
    return {scenario: metrics_from_reference(scenario) for scenario in SCENARIOS}


def test_medium_keeps_documented_revenue_and_denominators(metrics):
    data = metrics["medium"]
    assert data["known_rev"] == 68_448_127.94
    assert data["missing"] == 6000
    assert data["complete_pct"] == 95
    assert data["late_pct"] == pytest.approx(14.760374, abs=0.00001)
    payload = evidence_payload(data, "medium", True, DEFAULT_TH)
    assert payload["hypothesis"]["not_measured"] is True
    assert payload["observed"]["known_rev"] != payload["hypothesis"]["unverified_revenue"]


@pytest.mark.parametrize(
    "question,expected",
    [
        ("Cmb de commande ont pas de montant ?", "6\u202f000"),
        ("Quelle heure est-il ?", "Europe/Paris"),
        ("Compare les résultats avec le scénario critique.", "Critique"),
        ("Et si 15 % des montants manquaient ?", "hypoth"),
    ],
)
def test_conversation_in_demo_mode(question, expected, metrics):
    result = conversational_answer(question, "medium", metrics, DEFAULT_TH, {}, [], "Conversation")
    assert expected.lower() in result["text"].lower()


def test_monte_carlo_is_seeded_and_returns_expected_number_of_draws(metrics):
    result = monte_carlo(metrics["medium"], 0.15)
    assert result.size == 20_000
    assert (result == monte_carlo(metrics["medium"], 0.15)).all()


def test_unsupported_question_asks_for_clarification(metrics):
    answer = conversational_answer("Et les satellites de Jupiter ?", "medium", metrics, DEFAULT_TH, {}, [], "Conversation")
    assert answer["intent"] == "aucune"
    assert "quel angle" in answer["text"]
