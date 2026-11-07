"""Read-only, parameterized KPI queries against the verified NexaRetail DW schema."""

from __future__ import annotations

import os
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row

SCENARIOS = frozenset({"original", "low", "medium", "critical"})


def _scenario(value: str) -> str:
    if value not in SCENARIOS:
        raise ValueError(f"Scénario non autorisé : {value!r}")
    return value


def _connect():
    # Prefer a dedicated read-only DB role; PostgreSQL enforces read-only transaction too.
    url = os.getenv("ASSISTANT_DATABASE_URL")
    if not url:
        raise RuntimeError("ASSISTANT_DATABASE_URL manquant dans .env")
    return psycopg.connect(
        url,
        row_factory=dict_row, # type: ignore
        options="-c default_transaction_read_only=on -c statement_timeout=10000",
    )


def _run(sql: str, scenario: str) -> dict:
    scenario = _scenario(scenario)
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(sql, (scenario,)) # type: ignore
        result = cur.fetchone()
        if result is None:
            raise RuntimeError("Aucun résultat")
        return {k: float(v) if isinstance(v, Decimal) else v for k, v in result.items()} # type: ignore


def overview(scenario: str = "medium") -> dict:
    """KPI commerciaux avec contrôle de complétude des montants."""

    sql = """
        SELECT
            COUNT(*) AS commandes,
            COUNT(order_total) AS commandes_avec_montant,
            COUNT(*) - COUNT(order_total) AS montants_manquants,
            COALESCE(SUM(order_total), 0) AS chiffre_affaires_commandes,
            ROUND(AVG(order_total), 2) AS panier_moyen,
            ROUND(
                100.0 * COUNT(order_total) / NULLIF(COUNT(*), 0),
                2
            ) AS taux_completude_pct
        FROM dw.fact_orders
        WHERE scenario = %s
    """

    result = _run(sql, scenario)

    if result["commandes"] == 0:
        avertissement = "Aucune commande pour ce scénario."
    elif result["montants_manquants"] > 0:
        avertissement = (
            f"{result['montants_manquants']} commandes ont un "
            "montant manquant. Le panier moyen est calculé "
            "uniquement sur les montants renseignés."
        )
    else:
        avertissement = None

    return {
        "source": "dw.fact_orders",
        "scenario": scenario,
        "metric_definition": (
            "CA = SUM(order_total) ; "
            "panier moyen = AVG(order_total) hors NULL ; "
            "complétude = montants renseignés / commandes"
        ),
        **result,
        "avertissement_qualite": avertissement,
    }


def delivery(scenario: str = "original") -> dict:
    """Late delivery rate among shipments with both dates; not all shipments."""
    sql = """SELECT COUNT(*) AS expeditions,
                    COUNT(*) FILTER (WHERE actual_delivery_date IS NOT NULL AND estimated_delivery_date IS NOT NULL) AS livraisons_evaluables,
                    COUNT(*) FILTER (WHERE actual_delivery_date IS NOT NULL AND estimated_delivery_date IS NOT NULL AND actual_delivery_date > estimated_delivery_date) AS retards,
                    ROUND(100.0 * COUNT(*) FILTER (WHERE actual_delivery_date IS NOT NULL AND estimated_delivery_date IS NOT NULL AND actual_delivery_date > estimated_delivery_date)
                        / NULLIF(COUNT(*) FILTER (WHERE actual_delivery_date IS NOT NULL AND estimated_delivery_date IS NOT NULL), 0), 2) AS taux_retard_pct
             FROM dw.fact_shipments WHERE scenario = %s"""
    return {
        "source": "dw.fact_shipments",
        "scenario": scenario,
        "metric_definition": "retards / livraisons évaluables",
        **_run(sql, scenario),
    }


ALLOWED = {"overview": overview, "delivery": delivery}


def answer_data(intent: str, scenario: str = "original") -> dict:
    if intent not in ALLOWED:
        raise ValueError("Question non prise en charge par la version actuelle")
    return ALLOWED[intent](scenario)
