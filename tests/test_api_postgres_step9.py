import sys
import types

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


@pytest.fixture
def fake_database(monkeypatch):
    """Remplace les fonctions SQL par des réponses contrôlées."""
    monkeypatch.setenv("CONSULTAI_DEMO_MODE", "false")

    def overview(scenario):
        return {
            "commandes": 120000,
            "montants_manquants": 6000,
            "panier_moyen": 600.42,
            "chiffre_affaires_commandes": 68448127.94,
        }

    def delivery(scenario):
        return {
            "livraisons_evaluables": 70005,
            "retards": 10333,
        }

    fake_kpi = types.ModuleType("src.assistant.kpi")
    fake_kpi.overview = overview # type: ignore
    fake_kpi.delivery = delivery # type: ignore

    monkeypatch.setitem(sys.modules, "src.assistant.kpi", fake_kpi)


def test_postgresql_medium(fake_database):
    response = client.get("/kpis/medium")
    assert response.status_code == 200

    data = response.json()
    assert data["source"] == "postgresql"
    assert data["orders"] == 120000
    assert data["missing"] == 6000
    assert data["deliveries"] == 70005
    assert data["late"] == 10333


def test_postgresql_case_insensitive(fake_database):
    response = client.get("/kpis/Medium")
    assert response.status_code == 200
    assert response.json()["scenario"] == "medium"


def test_postgresql_invalid_data(fake_database, monkeypatch):
    fake_kpi = sys.modules["src.assistant.kpi"]

    def invalid_overview(scenario):
        return {
            "commandes": 100,
            "montants_manquants": 200,
            "panier_moyen": 600.42,
            "chiffre_affaires_commandes": 50000,
        }

    monkeypatch.setattr(fake_kpi, "overview", invalid_overview)

    response = client.get("/kpis/medium")
    assert response.status_code == 503
    assert "Données" in response.json()["detail"]


def test_unknown_scenario_without_database(fake_database):
    response = client.get("/kpis/unknown")
    assert response.status_code == 404
