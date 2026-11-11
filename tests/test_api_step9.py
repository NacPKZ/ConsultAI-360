import pytest
from fastapi.testclient import TestClient

from api.main import app, build_kpis

client = TestClient(app)


@pytest.fixture(autouse=True)
def activer_mode_demonstration(monkeypatch):
    """Rendre les tests indépendants de PostgreSQL et de l'environnement local."""
    monkeypatch.setenv("CONSULTAI_DEMO_MODE", "true")


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_scenarios():
    response = client.get("/scenarios")
    assert response.status_code == 200
    assert set(response.json()["scenarios"]) == {"low", "medium", "critical"}


@pytest.mark.parametrize(
    "scenario,missing",
    [
        ("low", 1200),
        ("medium", 6000),
        ("critical", 12000),
    ],
)
def test_kpis(scenario, missing):
    response = client.get(f"/kpis/{scenario}")
    assert response.status_code == 200
    assert response.json()["missing"] == missing


def test_unknown_scenario():
    response = client.get("/kpis/unknown")
    assert response.status_code == 404


def test_build_kpis():
    result = build_kpis("medium")
    assert result["orders"] == 120000
    assert result["missing_pct"] == 5.0
