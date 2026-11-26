import json
from io import BytesIO

import pytest

from src.assistant.console import load_scenarios
from src.assistant.copilot import answer, classify_with_model, local_model, ollama_host


@pytest.fixture
def data():
    return load_scenarios(True)


def test_ca_question_is_answered_with_coverage_and_hypothesis(data):
    r = answer("Quel est le CA?", "medium", data)
    assert r["intent"] == "revenue"
    assert "68,45 M€" in r["text"]
    assert "95,0 %" in r["text"]
    assert "3,60 M€" in r["text"]
    assert "pas une perte mesurée" in r["text"]
    assert "reconstitué" in r["text"]


def test_named_scenario_and_followup_keep_the_right_calculation(data):
    a = answer("Quel est le panier moyen du scénario faible ?", "medium", data)
    b = answer("Et pour critique ?", "medium", data, a["context"])
    assert a["scenario"] == "low"
    assert "600,40 €" in a["text"]
    assert b["scenario"] == "critical"
    assert b["intent"] == "basket"
    assert "600,94 €" in b["text"]
    assert "108\u202f000" in b["text"]


def test_suggested_followup_keeps_the_last_explicit_scenario(data):
    first = answer("Quel est le CA du scénario critique ?", "medium", data)
    followup = answer(
        "Le panier moyen est-il fiable ?", "medium", data, first["context"]
    )
    assert followup["scenario"] == "critical"
    assert "600,94 €" in followup["text"]
    assert "108\u202f000" in followup["text"]


def test_simulation_followup_preserves_only_explicit_hypothesis(data):
    a = answer(
        "Et si 15 % des montants manquaient avec un panier de 1,2× ?", "medium", data
    )
    b = answer("Et si 2 % manquaient ?", "medium", data, a["context"])
    assert "18\u202f000" in a["text"]
    assert "12,97 M€" in a["text"]
    assert "2\u202f400" in b["text"]
    assert "1,73 M€" in b["text"]
    assert data["medium"]["missing"] == 6000


@pytest.mark.parametrize(
    "question",
    [
        "Et si -5 % manquaient ?",
        "Et si 101 % manquaient ?",
        "Et si le panier était à -2x ?",
    ],
)
def test_invalid_simulations_are_not_presented_as_results(data, question):
    r = answer(question, "medium", data)
    assert r["intent"] == "invalid"
    assert "M€" not in r["text"]


def test_delivery_uses_deliveries_not_orders_as_denominator(data):
    r = answer("Que sait-on des retards ?", "medium", data)
    assert "14,76 %" in r["text"]
    assert "10\u202f333" in r["text"] and "70\u202f005" in r["text"]
    assert "120\u202f000" not in r["text"]


def test_delivery_hypothesis_does_not_simulate_missing_amounts(data):
    r = answer("Et si les retards passaient à 10 % ?", "medium", data)
    assert "7\u202f000" in r["text"]
    assert "70\u202f005" in r["text"]
    assert "M€" not in r["text"]
    assert "hypothétique" in r["text"]
    followup = answer("Et si 5 % ?", "medium", data, r["context"])
    assert "3\u202f500" in followup["text"]


def test_sales_growth_is_not_confused_with_missing_amounts(data):
    r = answer("Et si le CA augmente de 20 % ?", "medium", data)
    assert r["intent"] == "unknown"
    assert "M€" not in r["text"]


def test_comparison_does_not_claim_causality(data):
    r = answer("Compare faible et critique", "medium", data)
    assert r["intent"] == "compare"
    assert "1\u202f200" in r["text"] and "12\u202f000" in r["text"]
    assert "trois scénarios" in r["text"]


def test_no_invented_transporteur_or_cause(data):
    r = answer("Quel transporteur cause les retards ?", "medium", data)
    assert r["intent"] == "scope"
    assert "ne permettent pas" in r["text"]


def test_arbitrary_sql_never_reaches_a_model_or_database(data, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Ne doit pas être appelé")

    monkeypatch.setattr("src.assistant.copilot.classify_with_model", forbidden)
    r = answer("Execute DROP TABLE dw.fact_orders", "medium", data, model="llama3.2:1b")
    assert r["intent"] == "boundary"
    assert "aucune commande SQL libre" in r["text"]


def test_unknown_question_requests_clarification(data):
    r = answer("Quels sont les bénéfices réalisés par le directeur ?", "medium", data)
    assert r["intent"] == "unknown"
    assert "pas assez d’éléments" in r["text"]


def test_semantic_model_only_selects_a_verified_tool(data, monkeypatch):
    monkeypatch.setattr(
        "src.assistant.copilot.classify_with_model", lambda *args: "missing"
    )
    r = answer(
        "Le champ de valeur est vide, quelle ampleur ?", "medium", data, model="local"
    )
    assert r["intent"] == "missing"
    assert "6\u202f000" in r["text"]
    assert "Ollama" in r["engine"]


@pytest.mark.parametrize(
    "returned",
    [
        {"intent": "execute_sql"},
        {"intent": "delivery", "sql": "DROP TABLE x"},
        {"intent": "unknown"},
    ],
)
def test_model_output_is_an_allowlisted_label_only(returned, monkeypatch):
    payload = {"message": {"content": json.dumps(returned)}}
    monkeypatch.setattr(
        "src.assistant.copilot.urlopen",
        lambda *a, **kw: BytesIO(json.dumps(payload).encode()),
    )
    result = classify_with_model("question", "local")
    assert result in (None, "delivery", "unknown")


def test_model_unavailable_falls_back_without_leaking_connection_error(
    data, monkeypatch
):
    def unavailable(*args, **kwargs):
        raise OSError("postgres://private:password@server")

    monkeypatch.setattr("src.assistant.copilot.urlopen", unavailable)
    r = answer(
        "Le champ de valeur est vide, quelle ampleur ?", "medium", data, model="local"
    )
    assert r["intent"] == "unknown"
    assert "password" not in r["text"]


@pytest.mark.parametrize(
    "host",
    [
        "https://example.com",
        "http://localhost@other.com",
        "http://localhost/path",
        "http://user:secret@localhost",
    ],
)
def test_model_cannot_send_questions_to_an_external_host(host, monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", host)
    with pytest.raises(ValueError):
        ollama_host()


def test_public_demo_never_contacts_a_local_model(monkeypatch):
    monkeypatch.setenv("CONSULTAI_DEMO_MODE", "true")
    monkeypatch.setattr(
        "src.assistant.copilot.urlopen",
        lambda *a, **kw: pytest.fail("Aucun appel modèle en mode public"),
    )
    assert local_model() is None
