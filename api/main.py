import os

from fastapi import FastAPI, HTTPException

app = FastAPI(
    title="ConsultAI 360 API",
    version="0.9.0",
)

REFERENCE = {
    "low": {"orders": 120000, "missing": 1200},
    "medium": {"orders": 120000, "missing": 6000},
    "critical": {"orders": 120000, "missing": 12000},
}

SCENARIOS = tuple(REFERENCE)


def demo_enabled() -> bool:
    return os.getenv("CONSULTAI_DEMO_MODE", "false").strip().lower() in (
        "true",
        "1",
        "yes",
    )


def build_kpis(scenario: str) -> dict:
    if scenario not in SCENARIOS:
        raise ValueError(f"Scénario inconnu : {scenario}")

    if demo_enabled():
        data = REFERENCE[scenario]
        return {
            "scenario": scenario,
            "orders": data["orders"],
            "missing": data["missing"],
            "missing_pct": round(100 * data["missing"] / data["orders"], 2),
            "source": "demo",
        }

    from src.assistant.kpi import delivery, overview

    sales = overview(scenario)
    logistics = delivery(scenario)

    orders = int(sales["commandes"])
    missing = int(sales["montants_manquants"])
    deliveries = int(logistics["livraisons_evaluables"])
    late = int(logistics["retards"])

    if (
        orders <= 0
        or deliveries <= 0
        or not 0 <= missing <= orders
        or not 0 <= late <= deliveries
    ):
        raise ValueError("KPI PostgreSQL incohérents")

    return {
        "scenario": scenario,
        "orders": orders,
        "missing": missing,
        "missing_pct": round(100 * missing / orders, 2),
        "deliveries": deliveries,
        "late": late,
        "late_pct": round(100 * late / deliveries, 2),
        "source": "postgresql",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/scenarios")
def scenarios():
    return {"scenarios": list(SCENARIOS)}


@app.get("/kpis/{scenario}")
def kpis(scenario: str):
    scenario = scenario.strip().lower()
    if scenario not in SCENARIOS:
        raise HTTPException(
            status_code=404,
            detail="Scénario inconnu",
        )

    try:
        return build_kpis(scenario)
    except Exception as exc:
        # Ne jamais exposer les détails SQL ou secrets au client.
        raise HTTPException(
            status_code=503,
            detail="Données temporairement indisponibles",
        ) from exc
