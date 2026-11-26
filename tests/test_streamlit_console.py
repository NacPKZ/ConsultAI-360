from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


@pytest.fixture
def console(monkeypatch):
    monkeypatch.setenv("CONSULTAI_DEMO_MODE", "true")
    monkeypatch.delenv("ASSISTANT_DATABASE_URL", raising=False)
    return AppTest.from_file(APP, default_timeout=20).run()


def test_navigation_and_three_scenarios_render_without_errors(console):
    for scenario in ("low", "medium", "critical"):
        console.sidebar.selectbox[0].set_value(scenario).run()
        for page in console.sidebar.radio[0].options:
            console.sidebar.radio[0].set_value(page).run()
            assert not console.exception
    assert "Simulations" in console.sidebar.radio[0].options


def test_chat_is_separate_for_each_scenario_and_can_resume(console):
    console.sidebar.radio[0].set_value("Assistant IA").run()
    console.chat_input[0].set_value("Quel est le CA ?").run()
    assert len(console.chat_message) == 2
    assert "6\u202f000" in console.chat_message[1].markdown[0].value
    console.sidebar.selectbox[0].set_value("critical").run()
    assert len(console.chat_message) == 0
    console.chat_input[0].set_value("Quel est le CA ?").run()
    assert "12\u202f000" in console.chat_message[1].markdown[0].value
    console.sidebar.selectbox[0].set_value("medium").run()
    assert len(console.chat_message) == 2
    assert "6\u202f000" in console.chat_message[1].markdown[0].value


def test_public_postgres_toggle_keeps_selection_and_identifies_fallback(console):
    console.sidebar.selectbox[0].set_value("critical").run()
    console.sidebar.toggle[0].set_value(False).run()
    assert not console.exception
    assert console.sidebar.toggle[0].value is False
    assert console.sidebar.selectbox[0].value == "critical"
    fallback = next(
        m.value for m in console.sidebar.markdown if "postgres-note" in m.value
    )
    assert "stage ou un CDI" in fallback and "référence" in fallback
    console.sidebar.toggle[0].set_value(True).run()
    assert not any("postgres-note" in m.value for m in console.sidebar.markdown)
    console.sidebar.radio[0].set_value("Traçabilité des données").run()
    assert any("Référence figée" in m.value for m in console.markdown)


def test_new_exchange_clears_history_and_hypothesis_context(console):
    console.sidebar.radio[0].set_value("Assistant IA").run()
    console.chat_input[0].set_value("Et si 15 % manquaient ?").run()
    next(b for b in console.button if b.label == "Nouvel échange").click().run()
    assert len(console.chat_message) == 0
    console.chat_input[0].set_value("Et si le panier était à 1x ?").run()
    assert "6\u202f000" in console.chat_message[1].markdown[0].value
    assert "18\u202f000" not in console.chat_message[1].markdown[0].value


def test_suggestion_keeps_explicit_scenario_and_labels_context(console):
    console.sidebar.radio[0].set_value("Assistant IA").run()
    console.chat_input[0].set_value("Quel est le CA du scénario critique ?").run()
    next(
        b for b in console.button if b.label == "Le panier moyen est-il fiable ?"
    ).click().run()
    assert "600,94 €" in console.chat_message[-1].markdown[0].value
    assert console.sidebar.selectbox[0].value == "medium"
    assert "critique" in console.chat_message[-1].caption[0].value


def test_old_session_navigation_is_migrated_safely(monkeypatch):
    monkeypatch.setenv("CONSULTAI_DEMO_MODE", "true")
    app = AppTest.from_file(APP, default_timeout=20)
    app.session_state["navigation"] = "Mission Control"
    app.run()
    assert not app.exception
    assert app.sidebar.radio[0].value == "Synthèse"
    assert any("Peut-on publier" in md.value for md in app.markdown)


def test_database_failure_never_leaks_the_connection_string(monkeypatch):
    from src.assistant.console import load_scenarios

    monkeypatch.setenv("CONSULTAI_DEMO_MODE", "true")
    monkeypatch.setenv("ASSISTANT_DATABASE_URL", "postgres://private:secret@server")

    def fail_database(demo):
        if not demo:
            raise RuntimeError("postgres://private:secret@server")
        return load_scenarios(True)

    monkeypatch.setattr("src.assistant.console.load_scenarios", fail_database)
    app = AppTest.from_file(APP, default_timeout=20).run()
    app.sidebar.toggle[0].set_value(False).run()
    assert not app.exception
    assert "référence" in app.warning[0].value
    assert "secret" not in str(app)
    assert len(app.sidebar.warning) == 1 and not any(
        "postgres-note" in m.value for m in app.sidebar.markdown
    )


def test_pin_recovery_and_isolate_it_from_other_scenarios(console):
    console.sidebar.radio[0].set_value("Simulations").run()
    console.radio(key="simulation_mode").set_value("Plan de rattrapage").run()
    console.number_input(key="capacity_medium").set_value(400).run()
    assert any("12 jours" in m.value for m in console.markdown)
    console.button(key="pin_rattrapage").click().run()
    console.button(key="open_rattrapage").click().run()
    assert console.sidebar.radio[0].value == "Synthèse"
    assert any(
        "4800" in m.value.replace("\u202f", "") and "12 jours" in m.value
        for m in console.markdown
    )
    console.sidebar.selectbox[0].set_value("low").run()
    assert not any("12 jours" in m.value for m in console.markdown)


def test_selected_audit_family_continues_in_assistant(console):
    console.sidebar.radio[0].set_value("Diagnostic opérationnel").run()
    console.selectbox(key="audit_family_medium").set_value("duplicates").run()
    next(
        b for b in console.button if b.label == "Examiner avec l’assistant"
    ).click().run()
    assert console.sidebar.radio[0].value == "Assistant IA"
    assert (
        "25\u202f648 alertes avant nettoyage, 0 après"
        in console.chat_message[-1].markdown[0].value
    )


def test_delivery_goal_updates_chart_and_exportable_note(console):
    console.sidebar.radio[0].set_value("Diagnostic opérationnel").run()
    console.radio(key="diagnostic_view").set_value("Livraisons").run()
    console.slider(key="delivery_goal_medium").set_value(5.0).run()
    assert any("6\u202f833" in m.value for m in console.markdown)
    console.button(key="pin_livraisons").click().run()
    console.button(key="open_livraisons").click().run()
    assert any(
        "Objectif de livraison" in m.value and "6\u202f833" in m.value
        for m in console.markdown
    )
