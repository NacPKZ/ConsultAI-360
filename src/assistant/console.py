"""Calculs et sources de la console, indépendants de Streamlit et du modèle IA."""

from __future__ import annotations

import math
from datetime import date

SCENARIOS = ("low", "medium", "critical")
SCENARIO_NAMES = {"low": "Faible", "medium": "Moyen", "critical": "Critique"}
REFERENCE = {
    "low": {
        "orders": 120000,
        "missing": 1200,
        "basket": 600.40,
        "deliveries": 70005,
        "late": 10333,
    },
    "medium": {
        "orders": 120000,
        "missing": 6000,
        "basket": 600.42,
        "deliveries": 70005,
        "late": 10333,
    },
    "critical": {
        "orders": 120000,
        "missing": 12000,
        "basket": 600.94,
        "deliveries": 70005,
        "late": 10333,
    },
}


def fmt(value: float | int, digits: int = 0) -> str:
    return f"{value:,.{digits}f}".replace(",", "\u202f").replace(".", ",")


def money(value: float) -> str:
    return f"{fmt(value / 1e6, 2)} M€" if abs(value) >= 1e6 else f"{fmt(value, 2)} €"


def build_metrics(raw: dict, source: str) -> dict:
    """Valide les populations avant de calculer les taux. Aucun NULL n'est remplacé par zéro."""
    if source not in ("reference", "postgresql"):
        raise ValueError("Source inconnue")
    counts = {}
    for key in ("orders", "missing", "deliveries", "late"):
        value = float(raw[key])
        if not math.isfinite(value) or value != int(value):
            raise ValueError("Volume non entier ou non fini")
        counts[key] = int(value)
    orders, missing, deliveries, late = (
        counts[k] for k in ("orders", "missing", "deliveries", "late")
    )
    basket = float(raw["basket"])
    if (
        orders <= 0
        or deliveries <= 0
        or not 0 <= missing < orders
        or not 0 <= late <= deliveries
    ):
        raise ValueError("Populations incohérentes ou absence de montant exploitable")
    if not math.isfinite(basket) or basket < 0:
        raise ValueError("Panier invalide")
    # La référence historique n'a conservé que le panier arrondi, pas SUM(order_total).
    # Ne pas présenter cette multiplication comme un CA exact observé en base.
    known = orders - missing
    known_rev = float(raw["known_rev"]) if source == "postgresql" else known * basket
    if not math.isfinite(known_rev) or known_rev < 0:
        raise ValueError("Chiffre d'affaires invalide")
    return {
        **counts,
        "basket": basket,
        "known": known,
        "missing_pct": 100 * missing / orders,
        "complete_pct": 100 * known / orders,
        "late_pct": 100 * late / deliveries,
        "known_rev": known_rev,
        "revenue_approximate": source == "reference",
        "exposure": missing * basket,
        "source": source,
    }


def load_scenarios(demo: bool) -> dict[str, dict]:
    if demo:
        return {s: build_metrics(REFERENCE[s], "reference") for s in SCENARIOS}
    from src.assistant.kpi import delivery, overview

    result = {}
    for scenario in SCENARIOS:
        sales, logistics = overview(scenario), delivery(scenario)
        result[scenario] = build_metrics(
            {
                "orders": sales["commandes"],
                "missing": sales["montants_manquants"],
                "basket": sales["panier_moyen"],
                "known_rev": sales["chiffre_affaires_commandes"],
                "deliveries": logistics["livraisons_evaluables"],
                "late": logistics["retards"],
            },
            "postgresql",
        )
    return result


def impact(
    metrics: dict, missing_pct: float | None = None, basket_ratio: float = 1.0
) -> dict:
    """Hypothèse explicite : panier inconnu = panier connu × ratio choisi."""
    rate = metrics["missing_pct"] if missing_pct is None else float(missing_pct)
    ratio = float(basket_ratio)
    if not math.isfinite(rate) or not 0 <= rate <= 100:
        raise ValueError("Le taux doit être compris entre 0 et 100 %.")
    if not math.isfinite(ratio) or not 0 < ratio <= 10:
        raise ValueError(
            "Le coefficient de panier doit être supérieur à 0 et inférieur ou égal à 10."
        )
    missing = round(metrics["orders"] * rate / 100)
    return {
        "missing": missing,
        "rate": rate,
        "ratio": ratio,
        "amount": missing * metrics["basket"] * ratio,
    }


def priorities(metrics: dict) -> list[dict]:
    actions = []
    if metrics["missing"]:
        actions.extend(
            [
                {
                    "title": "Rapprocher les montants avec la source",
                    "detail": f"{fmt(metrics['missing'])} commandes à contrôler, par magasin, canal et période.",
                    "owner": "Équipe data et finance",
                },
                {
                    "title": "Afficher la couverture du chiffre d’affaires",
                    "detail": f"Les montants renseignés couvrent {fmt(metrics['complete_pct'], 1)} % des commandes.",
                    "owner": "Responsable du reporting",
                },
            ]
        )
    if metrics["late"]:
        actions.append(
            {
                "title": "Localiser les retards de livraison",
                "detail": "Comparer les transporteurs et les zones à partir des dates prévues et réelles.",
                "owner": "Équipe logistique",
            }
        )
    return actions


def evidence(metrics: dict, scenario: str) -> dict:
    """Export des valeurs effectivement affichées, avec leur provenance réelle."""
    demo = metrics["source"] == "reference"
    return {
        "scenario": scenario,
        "source": "reference_figee" if demo else "postgresql_lecture_seule_cache_5_min",
        "scope": "NexaRetail, données synthétiques",
        "orders": {
            k: metrics[k]
            for k in ("orders", "known", "missing", "basket", "complete_pct")
        },
        "deliveries": {k: metrics[k] for k in ("deliveries", "late", "late_pct")},
        "revenue": {
            "value": metrics["known_rev"],
            "method": (
                "commandes renseignées × panier moyen arrondi"
                if demo
                else "SUM(order_total) hors NULL"
            ),
            "approximate": demo,
        },
        "hypothesis": {
            "method": "montants absents × panier connu",
            "amount": metrics["exposure"],
            "measured_loss": False,
        },
    }


def mission_note(metrics: dict, scenario: str) -> str:
    revenue_label = (
        "CA reconstitué à partir du panier arrondi"
        if metrics["revenue_approximate"]
        else "CA renseigné (SUM des montants)"
    )
    actions = "\n".join(
        f"- {a['title']} : {a['detail']} ({a['owner']}, à confirmer)."
        for a in priorities(metrics)
    )
    return (
        f"# NexaRetail — synthèse du scénario {SCENARIO_NAMES[scenario].lower()}\n\n"
        f"Note exportée le {date.today():%d/%m/%Y}. Données synthétiques. "
        f"Source : {'référence figée de démonstration' if metrics['source'] == 'reference' else 'PostgreSQL en lecture seule, cache de 5 minutes'}.\n\n"
        "## Constats\n\n"
        f"- {fmt(metrics['orders'])} commandes, dont {fmt(metrics['missing'])} sans montant ({fmt(metrics['missing_pct'], 2)} %).\n"
        f"- Panier connu : {fmt(metrics['basket'], 2)} €, calculé sur {fmt(metrics['known'])} commandes.\n"
        f"- {revenue_label} : {money(metrics['known_rev'])}.\n"
        f"- Retards : {fmt(metrics['late'])} / {fmt(metrics['deliveries'])} livraisons évaluables ({fmt(metrics['late_pct'], 2)} %).\n\n"
        "## Actions proposées\n\n" + actions + "\n\n"
        "## Point à vérifier\n\n"
        "Les agrégats ne permettent pas d’identifier les magasins, transporteurs ou causes concernés. "
        "Les commandes sans montant ne constituent pas une perte de chiffre d’affaires mesurée.\n"
    )
