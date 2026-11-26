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
    assert len(console.sidebar.radio[0].options) == 4


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
    assert "référence" in console.info[0].value
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


def test_old_session_navigation_is_migrated_safely(monkeypatch):
    monkeypatch.setenv("CONSULTAI_DEMO_MODE", "true")
    app = AppTest.from_file(APP, default_timeout=20)
    app.session_state["navigation"] = "Mission Control"
    app.run()
    assert not app.exception
    assert app.title[0].value == "Synthèse"


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
    assert any("Référence affichée" in c.value for c in app.sidebar.caption)
