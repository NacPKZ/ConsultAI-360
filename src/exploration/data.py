"""Rapports de mission versionnés et hypothèses du visiteur ; aucune écriture en base."""

from functools import lru_cache
from pathlib import Path
import json
import math

import numpy as np

from src.assistant.console import SCENARIOS

ROOT = Path(__file__).resolve().parents[2]
STAGES = ("raw", "corrupted", "cleaned")
STAGE_NAMES = ("Référence", "Après injection", "Après nettoyage")
FAMILIES = {
    "duplicates": "Doublons",
    "negative_amounts": "Montants négatifs",
    "broken_references": "Références rompues",
    "missing_values": "Valeurs manquantes",
    "inconsistent_totals": "Totaux incohérents",
    "invalid_dates": "Dates impossibles",
    "invalid_status": "Statuts invalides",
    "invalid_formats": "Formats invalides",
}
MEASURES = {
    "CA déclaré": (
        "reported_order_total_sum",
        "Somme des montants des commandes. Les valeurs négatives sont incluses et les montants absents sont ignorés.",
        "M€",
    ),
    "Doublons": (
        "duplicate_order_ids",
        "Identifiants de commande dupliqués. Une ligne en double peut compter deux fois dans un total.",
        "commandes",
    ),
    "Panier utilisable": (
        "usable_amount_average",
        "Moyenne sur les lignes dont le montant est exploitable. Les valeurs négatives et les montants absents sont exclus.",
        "€",
    ),
}
VIEWS = {"Vue générale": "01", "Ventes": "02", "Logistique": "03", "Qualité": "04"}


@lru_cache(maxsize=3)
def archive(scenario):
    if scenario not in SCENARIOS:
        raise ValueError("Scénario inconnu")
    reports = ROOT / "reports"

    def read(path):
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if data["scenario"] != scenario:
            raise ValueError("Le rapport ne correspond pas au scénario")
        return data

    impact = read(
        reports / "business_impact" / scenario / "business_impact_summary.json"
    )
    evaluation = read(
        reports / "data_quality/evaluation" / scenario / "evaluation_summary.json"
    )
    return impact["snapshots"], evaluation


def stages(scenario, measure):
    rows, _ = archive(scenario)
    field = MEASURES[measure][0]
    return [rows[step][field] for step in STAGES]


def recovery(m, target, capacity):
    if (
        not m["complete_pct"] <= target <= 100
        or not isinstance(capacity, int)
        or capacity < 1
    ):
        raise ValueError("Objectif ou cadence invalide")
    required = max(
        0, min(m["missing"], math.ceil(m["orders"] * target / 100 - 1e-8) - m["known"])
    )
    return required, math.ceil(required / capacity)


def distribution(amount, sigma):
    """Ancien Monte-Carlo : un tirage représente le panier moyen inconnu de tout le groupe."""
    if not math.isfinite(amount) or amount < 0 or not 0 < sigma <= 1:
        raise ValueError("Paramètres de simulation invalides")
    rng = np.random.default_rng(7)
    return amount * rng.lognormal(mean=-0.5 * sigma**2, sigma=sigma, size=20000)
