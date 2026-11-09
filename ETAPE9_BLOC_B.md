"""Read-only API. Independent from Streamlit's app.py (which renders UI at import)."""
from __future__ import annotations
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="ConsultAI 360 — KPI API", version="0.9.0")

REFERENCE = {
    "low": {"orders": 120000, "missing": 1200, "basket": 600.40, "deliveries": 70005, "late": 10333},
    "medium": {"orders": 120000, "missing": 6000, "basket": 600.42, "deliveries": 70005, "late": 10333},
    "critical": {"orders": 120000, "missing": 12000, "basket": 600.94, "deliveries": 70005, "late": 10333},
}

class KPIs(BaseModel):
    scenario: str
    source: str
    orders: int
    missing: int
    known: int
    missing_pct: float
    complete_pct: float
    deliveries: int
    late: int
    late_pct: float
    basket: float
    known_rev: float | None
    exposure_estimate: float


def build_kpis(scenario: str, raw: dict, source: str) -> KPIs:
    orders, missing = int(raw["orders"]), int(raw["missing"])
    deliveries, late = int(raw["deliveries"]), int(raw["late"])
    basket = float(raw["basket"])
    if not (orders > 0 and deliveries > 0 and 0 <= missing <= orders and 0 <= late <= deliveries and basket >= 0):
        raise ValueError("Incohérence de données")
    return KPIs(scenario=scenario, source=source, orders=orders, missing=missing,
        known=orders-missing, missing_pct=100*missing/orders,
        complete_pct=100*(orders-missing)/orders, deliveries=deliveries,
        late=late, late_pct=100*late/deliveries, basket=basket,
        known_rev=raw.get("known_rev"), exposure_estimate=missing*basket)


def demo_enabled() -> bool:
    return os.getenv("CONSULTAI_DEMO_MODE", "true").lower() in {"true", "1", "yes"}


@app.get("/health")
def health():
    return {"status": "ok", "mode": "demo" if demo_enabled() else "database"}


@app.get("/scenarios")
def scenarios():
    return {"scenarios": list(REFERENCE)}


@app.get("/kpis/{scenario}", response_model=KPIs)
def kpis(scenario: str):
    if scenario not in REFERENCE:
        raise HTTPException(status_code=404, detail="Scénario inconnu")
    if demo_enabled():
        return build_kpis(scenario, REFERENCE[scenario], "demo_reference")
    try:
        # Import only in database mode; no credentials or DB required in demo.
        from src.assistant.kpi import overview, delivery
        c, l = overview(scenario), delivery(scenario)
        if c.get("panier_moyen") is None or c.get("chiffre_affaires_commandes") is None:
            raise ValueError("KPI SQL incomplets")
        raw = {"orders": c["commandes"], "missing": c["montants_manquants"],
               "basket": c["panier_moyen"], "known_rev": float(c["chiffre_affaires_commandes"]),
               "deliveries": l["livraisons_evaluables"], "late": l["retards"]}
        return build_kpis(scenario, raw, "postgresql")
    except (ImportError, KeyError, ValueError, TypeError, OSError, RuntimeError) as exc:
        # Do not leak DB details to public clients.
        raise HTTPException(status_code=503, detail="Données SQL indisponibles ou incohérentes") from exc
