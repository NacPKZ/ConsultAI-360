"""Moteur déterministe et sources de référence de la console NexaRetail."""
from __future__ import annotations

import difflib
import json
import os
import re
import unicodedata
import urllib.request
from datetime import date, datetime
from functools import lru_cache
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import numpy as np
import streamlit as st

from project_knowledge import correct as correct_question, project_answer
from src.assistant.decision_rules import DEFAULT_TH, gate
from src.assistant.health_score import health

REFERENCE = {
    "low": {
        "orders": 120000,
        "known_rev": 71_327_494.22,
        "missing": 1200,
        "basket": 600.40,
        "deliveries": 70005,
        "late": 10333,
    },
    "medium": {
        "orders": 120000,
        "known_rev": 68_448_127.94,
        "missing": 6000,
        "basket": 600.42,
        "deliveries": 70005,
        "late": 10333,
    },
    "critical": {
        "orders": 120000,
        "known_rev": 64_901_512.00,
        "missing": 12000,
        "basket": 600.94,
        "deliveries": 70005,
        "late": 10333,
    },
}


SCENARIOS = ("low", "medium", "critical")


SCENARIO_NAME = {"low": "Faible", "medium": "Moyen", "critical": "Critique"}


SCENARIO_LABEL = {
    "low": "Scénario faible",
    "medium": "Scénario moyen",
    "critical": "Scénario critique",
}


PUBLIC = os.getenv("CONSULTAI_DEMO_MODE", "false").strip().lower() in (
    "true",
    "1",
    "yes",
)


def fmt(v, digits: int = 0) -> str:
    """Format français ; espace fine insécable pour que « 120 000 » ne se coupe jamais."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "N/D"
    return f"{v:,.{digits}f}".replace(",", "\u202f").replace(".", ",")


def eur_m(v) -> str:
    return "N/D" if v is None else f"{fmt(v / 1e6, 1)}\u00a0M€"


def norm(s: str) -> str:
    return "".join(
        c
        for c in unicodedata.normalize("NFKD", s.lower())
        if not unicodedata.combining(c)
    )


def enrich(m: dict) -> dict:
    basket = m.get("basket")
    m["exposure"] = m["missing"] * basket if basket is not None else None
    m["known_rev"] = m.get(
        "known_rev", m["known"] * basket if basket is not None else None
    )
    return m


def metrics_from_reference(scenario: str) -> dict:
    r = REFERENCE[scenario]
    return enrich(
        {
            **r,
            "known": r["orders"] - r["missing"],
            "missing_pct": 100 * r["missing"] / r["orders"],
            "complete_pct": 100 * (r["orders"] - r["missing"]) / r["orders"],
            "late_pct": 100 * r["late"] / r["deliveries"],
        }
    )


def metrics_from_db(scenario: str) -> dict:
    from src.assistant.kpi import delivery, overview

    c, l = overview(scenario), delivery(scenario)
    orders, missing = int(c["commandes"]), int(c["montants_manquants"])
    deliveries, late = int(l["livraisons_evaluables"]), int(l["retards"])
    if (
        orders <= 0
        or deliveries <= 0
        or c["panier_moyen"] is None
        or c.get("chiffre_affaires_commandes") is None
        or not (0 <= missing <= orders)
        or not (0 <= late <= deliveries)
    ):
        raise ValueError(
            f"KPI incomplets ou incohérents pour le scénario {scenario} : vérifie le DWH."
        )
    if not all(
        np.isfinite(float(v)) and float(v) >= 0
        for v in (c["panier_moyen"], c["chiffre_affaires_commandes"])
    ):
        raise ValueError("Panier moyen ou chiffre d’affaires négatif ou non fini.")
    return enrich(
        {
            "orders": orders,
            "missing": missing,
            "known": orders - missing,
            "basket": float(c["panier_moyen"]),
            "deliveries": deliveries,
            "late": late,
            "known_rev": float(c["chiffre_affaires_commandes"]),
            "missing_pct": 100 * missing / orders,
            "complete_pct": 100 * (orders - missing) / orders,
            "late_pct": 100 * late / deliveries,
        }
    )


@st.cache_data(ttl=300, show_spinner="Chargement des indicateurs…")
def load_metrics(demo: bool) -> dict:
    """Mis en cache 5 min : avant, 3 requêtes SQL partaient à chaque interaction."""
    return {
        s: (metrics_from_reference(s) if demo else metrics_from_db(s))
        for s in SCENARIOS
    }


VERDICT = {
    "go": ("Publiable", "v-go"),
    "warn": ("Publiable avec réserves", "v-warn"),
    "stop": ("À bloquer", "v-stop"),
}


def recommendations(d: dict, th: dict | None = None) -> list[dict]:
    """Les seuils sont réglables dans la Porte de décision."""
    th = th or DEFAULT_TH
    recs = []
    if d["missing_pct"] > th["m_fail"]:
        recs.append(
            dict(
                t="Suspendre la publication du chiffre d'affaires mensuel",
                sev="high",
                impact=3,
                effort=1,
                why=f"{fmt(d['missing_pct'], 1)} % des commandes n'ont pas de montant : le total publié serait trompeur tant que la complétude n'est pas rétablie.",
            )
        )
    if d["missing_pct"] >= 1:
        sev = "high" if d["missing_pct"] > th["m_warn"] else "mid"
        recs.append(
            dict(
                t="Comparer les commandes avec et sans montant",
                sev=sev,
                impact=3,
                effort=1,
                why="Magasin, canal, période, catégorie : si les montants manquent au hasard, le panier moyen reste exploitable. Sinon, il est biaisé.",
            )
        )
        recs.append(
            dict(
                t="Auditer la chaîne de collecte des montants",
                sev=sev,
                impact=3,
                effort=2,
                why="Remonter l'ETL : champ vide à la source, perte à la jointure ou transformation défaillante ?",
            )
        )
        recs.append(
            dict(
                t="Publier le chiffre d'affaires avec son taux de couverture",
                sev="mid",
                impact=2,
                effort=1,
                why="Afficher « CA sur X % des commandes » évite de présenter une estimation comme un fait.",
            )
        )
    if d["late_pct"] > th["l_warn"]:
        recs.append(
            dict(
                t="Segmenter les retards par transporteur et par zone",
                sev="mid",
                impact=2,
                effort=1,
                why=f"{fmt(d['late_pct'], 1)} % de retards : les agrégats ne disent pas où le problème se concentre.",
            )
        )
    if not recs:
        recs.append(
            dict(
                t="Maintenir la surveillance",
                sev="low",
                impact=1,
                effort=1,
                why="Aucun seuil dépassé : conserver les contrôles automatiques.",
            )
        )
    return sorted(recs, key=lambda r: (-r["impact"], r["effort"]))


@lru_cache(maxsize=64)
def _mc(
    missing: int, basket: float, sigma: float, n: int = 20000, seed: int = 7
) -> np.ndarray:
    rng = np.random.default_rng(seed)
    ratio = rng.lognormal(mean=-0.5 * sigma**2, sigma=sigma, size=n)
    return missing * basket * ratio / 1e6


def monte_carlo(d: dict, sigma: float) -> np.ndarray:
    """Exposition (M€) si le panier des commandes sans montant est log-normal de moyenne 1× le panier connu.
    Mis en cache : 20 000 tirages n'étaient plus recalculés qu'une fois par jeu de paramètres.
    Un tirage représente le panier moyen inconnu du groupe, pas chaque commande (scénario subjectif, non calibré)."""
    return _mc(int(d["missing"]), float(d["basket"]), round(float(sigma), 4))


def memo_markdown(d: dict, scenario: str, g: dict, hs: dict, recs: list[dict]) -> str:
    q = np.percentile(monte_carlo(d, 0.15), [5, 95])
    lines = [
        f"# Note de décision — ConsultAI 360 ({date.today():%d/%m/%Y})",
        "",
        f"**Scénario analysé :** {SCENARIO_LABEL[scenario]}",
        f"**Verdict :** {VERDICT[g['overall']][0]}  |  **Indice de santé :** {hs['score']:.0f}/100",
        "",
        "## Faits vérifiés",
        f"- {fmt(d['orders'])} commandes ; {fmt(d['missing'])} sans montant ({fmt(d['missing_pct'], 2)} %).",
        f"- Panier moyen sur montants connus : {fmt(d['basket'], 2)} €.",
        f"- {fmt(d['late'])} retards sur {fmt(d['deliveries'])} livraisons évaluables ({fmt(d['late_pct'], 2)} %).",
        "",
        "## Hypothèse (non mesurée)",
        f"- Exposition si panier identique : {eur_m(d['exposure'])} ; fourchette illustrative P5–P95 (hypothèse log-normale, sigma=0,15) : {fmt(q[0], 1)} à {fmt(q[1], 1)} M€.",
        "",
        "## Contrôles",
    ]
    lines += [f"- {c[0]} : {c[1]} → {VERDICT[c[2]][0]}" for c in g["checks"]]
    lines += ["", "## Actions recommandées (par priorité)"] + [
        f"{i}. **{r['t']}** — {r['why']}" for i, r in enumerate(recs, 1)
    ]
    lines += [
        "",
        "## Limites",
        "Données synthétiques. Aucun effet causal sur les ventes n'est démontré. Les chiffres viennent de calculs Python/SQL, pas d'un modèle de langage.",
    ]
    return "\n".join(lines)


SC_WORDS = {
    "low": r"\b(low|faible|bas)\b",
    "medium": r"\b(medium|moyen|median)\b",
    "critical": r"\b(critical|critique|pire)\b",
}


INTENTS = {
    "greet": ["bonjour", "salut", "hello", "coucou", "merci"],
    "help": [
        "aide",
        "que sais-tu",
        "que peux-tu",
        "tu sais faire",
        "capacite",
        "qui es-tu",
        "presente",
    ],
    "compare": ["compar", "scenarios", "difference", "versus", " vs ", "ecart entre"],
    "solve": [
        "a partir de quel",
        "quel taux",
        "pour atteindre",
        "point de bascule",
        "tolere",
        "quel seuil",
        "jusqu'ou",
        "combien de montants",
        "limite acceptable",
    ],
    "simulate": [
        "simul",
        "et si",
        "passe a",
        "passait",
        "manquaient",
        "manquait",
        "augmente",
        "baisse",
        "hypothe",
        "scenario catastrophe",
    ],
    "exposure": [
        " ca ",
        "revenu",
        "perte",
        "perdu",
        "expos",
        "euros",
        "argent",
        "incertitude",
        "intervalle",
        "fourchette",
    ],
    "basket": ["panier"],
    "late": ["retard", "livraison", "transporteur", "logisti", "ponctualite"],
    "risk": ["risque", "qualite", "probleme", "priorite", "gravite", "danger"],
    "actions": [
        "action",
        "recommand",
        "que faire",
        "plan",
        "conseil",
        "ameliorer",
        "corriger",
        "prochaine etape",
    ],
    "score": ["score", "sante", "indice"],
    "gate": [
        "publier",
        "publication",
        "valider",
        "decision",
        "bloquer",
        "fiable",
        "se fier",
        "utilisable",
        "verdict",
    ],
    "why": ["pourquoi", "explique", "justifie", "d'ou vient", "comment est calcule"],
    "glossary": [
        "c'est quoi",
        "definition",
        "signifie",
        "completude",
        "evaluable",
        "mnar",
        "mcar",
        "mar ",
    ],
    "memo": [
        "memo",
        "synthese",
        "resume",
        "rapport",
        "brief",
        "note de decision",
        "redige",
        "ecris",
    ],
    "method": [
        "methode",
        "hallucin",
        "limite",
        "llm",
        "ollama",
        "modele",
        "comment tu",
        "tu calcules",
        "source",
    ],
}


KIND = {
    "compare": "Calcul vérifié",
    "basket": "Calcul vérifié",
    "late": "Calcul vérifié",
    "risk": "Calcul vérifié",
    "actions": "Règles de priorisation",
    "score": "Calcul vérifié",
    "gate": "Règle de décision",
    "why": "Calcul vérifié",
    "simulate": "Hypothèse",
    "exposure": "Hypothèse",
    "solve": "Hypothèse",
    "memo": "Note générée",
    "glossary": "Définition",
    "method": "Information",
    "help": "Information",
    "greet": "Information",
}


FOLLOWUPS = {
    "compare": [
        "Et si 15 % des montants manquaient ?",
        "À partir de quel taux faut-il bloquer le chiffre d'affaires ?",
        "Que faire en priorité ?",
    ],
    "simulate": [
        "Et avec un panier manquant à 1,3× ?",
        "Quel taux pour atteindre 10 M€ d'exposition ?",
        "Peut-on publier le chiffre d'affaires ?",
    ],
    "exposure": [
        "Compare les trois scénarios",
        "Et si 15 % des montants manquaient ?",
        "Rédige une note de décision",
    ],
    "solve": [
        "Et pour le scénario critique ?",
        "Peut-on publier le chiffre d'affaires ?",
        "Que faire en priorité ?",
    ],
    "basket": [
        "Combien de chiffre d'affaires est exposé ?",
        "C'est quoi MCAR et MNAR ?",
        "Que faire en priorité ?",
    ],
    "late": [
        "Les retards dépendent-ils du scénario ?",
        "Que faire en priorité ?",
        "Rédige une note de décision",
    ],
    "risk": [
        "Que faire en priorité ?",
        "Pourquoi ce verdict ?",
        "Combien de chiffre d'affaires est exposé ?",
    ],
    "actions": [
        "Rédige une note de décision",
        "Peut-on publier le chiffre d'affaires ?",
        "Compare les trois scénarios",
    ],
    "score": [
        "Pourquoi ce verdict ?",
        "Compare les trois scénarios",
        "Que faire en priorité ?",
    ],
    "gate": [
        "Pourquoi ce verdict ?",
        "À partir de quel taux faut-il bloquer le chiffre d'affaires ?",
        "Rédige une note de décision",
    ],
    "why": [
        "Que faire en priorité ?",
        "Et pour le scénario critique ?",
        "Rédige une note de décision",
    ],
}


DEFAULT_FOLLOW = [
    "Compare les trois scénarios",
    "Combien de chiffre d'affaires est exposé ?",
    "Peut-on publier le chiffre d'affaires ?",
]


CATALOG = tuple(dict.fromkeys(question for prompts in FOLLOWUPS.values() for question in prompts))


IDENTITY_PATTERNS = (
    r"\bqui es[ -]?tu\b",
    r"\btu es qui\b",
    r"\bqui etes[ -]?vous\b",
    r"\bpresente[ -]?toi\b",
    r"\bton role\b",
    r"\bque fais[ -]?tu\b",
    r"\bc.est quoi consultai\b",
    r"\bwhat are you\b",
)


def _num(m: re.Match | None) -> float | None:
    return float(m.group(1).replace(",", ".")) if m else None


def respond(question: str, scenario: str, allm: dict, th: dict, ctx: dict) -> dict:
    """Agent à outils : détecte les intentions et entités, appelle des outils Python, trace chaque appel."""
    question, corrections = correct_question(question)
    # La ponctuation collée ("CA?") ne doit pas empêcher la détection des mots-clés (" ca ").
    qn = " " + re.sub(r"[?!;:]", " ", norm(question)) + " "
    trace: list[str] = []
    if corrections:
        trace.append(
            "Correction de saisie : " + ", ".join(f"{a} → {b}" for a, b in corrections)
        )
    project = project_answer(question)
    if project is not None:
        return {
            "text": project["text"],
            "evidence": trace + project["evidence"],
            "intent": "projet_" + project["topic"].lower(),
            "kind": "Documentation",
            "followups": project["followups"],
            "scenario": scenario,
        }

    def T(call: str, result: str) -> None:
        trace.append(f"`{call}` → {result}")

    named = [s for s, rx in SC_WORDS.items() if re.search(rx, qn)]
    sc = (
        named[0]
        if len(named) == 1
        else (
            ctx.get("scenario", scenario)
            if re.search(r"\b(et|encore|aussi|pourquoi|pareil|ce|celui)\b", qn)
            else scenario
        )
    )
    d = allm[sc]
    pct = _num(re.search(r"(-?\d+(?:[.,]\d+)?)\s*%", qn))
    mult = _num(re.search(r"(-?\d+(?:[.,]\d+)?)\s*(?:x|×|fois)(?:\s|$)", qn))
    target = _num(re.search(r"(-?\d+(?:[.,]\d+)?)\s*(?:m€|meur|millions?|m\s)", qn))

    scores = {k: sum(1 for w in ws if w in qn) for k, ws in INTENTS.items()}
    if len(named) >= 2:
        scores["compare"] += 3
    if target is not None:
        scores["solve"] += 3
    if mult is not None:
        scores["simulate"] += 2
    if (
        pct is not None
        and scores["solve"] == 0
        and not any(w in qn for w in ("seuil", "bloqu"))
    ):
        scores["simulate"] += 2
    # Les formules ne doivent pas être supplantées par des mots génériques.
    if "panier" in qn and ("fiable" in qn or "biais" in qn):
        scores["basket"] += 4
    if "note de decision" in qn or "redige" in qn:
        scores["memo"] += 4
    if "priorite" in qn or "en premier" in qn:
        scores["actions"] += 4
    if "bloquer" in qn and ("quel taux" in qn or "partir" in qn):
        scores["solve"] += 4
    ranked = [k for k in sorted(scores, key=lambda k: -scores[k]) if scores[k] > 0]
    if not ranked and (named or pct or mult or target) and ctx.get("intent"):
        ranked = [ctx["intent"]]
        trace.append(
            f"Question de suivi : intention reprise de la réponse précédente ({ctx['intent']})"
        )
    if any(re.search(p, qn) for p in IDENTITY_PATTERNS):
        return {
            "text": (
                "### Je suis le copilote d'analyse ConsultAI 360\n\n"
                "J'accompagne une **mission fictive de conseil Data & IA pour NexaRetail**. "
                "Je transforme les indicateurs vérifiés en diagnostics, scénarios et pistes d'action.\n\n"
                "**Ce que je peux faire**\n"
                "- Comparer les trois niveaux de qualité des données.\n"
                "- Simuler l'effet des montants manquants sur le chiffre d'affaires.\n"
                "- Expliquer les règles de publication et leurs seuils.\n"
                "- Proposer un plan d'investigation et une note de décision.\n\n"
                "**Mes limites :** les calculs viennent de SQL/Python, pas d'une génération de texte. "
                "Je ne connais pas les causes réelles des anomalies et je n'exécute aucune décision. "
                "Ollama, lorsqu'il est activé, peut reformuler les résultats, mais ne remplace pas les contrôles."
            ),
            "evidence": ["Réponse de présentation : aucune requête SQL nécessaire."],
            "intent": "identite",
            "kind": "Information",
            "followups": [
                "Compare les trois scénarios",
                "Que faire en priorité ?",
                "Rédige une note de décision",
            ],
            "scenario": sc,
        }
    if not ranked:
        close = (
            difflib.get_close_matches(question.strip(), CATALOG, n=3, cutoff=0.2)
            or CATALOG[:3]
        )
        return {
            "text": (
                "Je n'ai pas reconnu de question sur les données NexaRetail. Je sais comparer les scénarios, simuler un taux de montants absents, "
                "chiffrer l'exposition et son incertitude, trouver à partir de quel taux bloquer, expliquer un verdict et rédiger une note.\n\n"
                "Tu voulais peut-être demander :"
            ),
            "evidence": [],
            "intent": "aucune",
            "kind": "Information",
            "followups": close,
            "scenario": sc,
        }
    picks = ranked[:1] + [
        k for k in ranked[1:2] if scores[k] >= 2 and scores[k] >= scores[ranked[0]] - 1
    ]
    hs, g, recs = health(d), gate(d, th), recommendations(d, th)
    formulas: list[str] = []
    parts: list[str] = []

    for intent in picks:
        if intent == "greet":
            parts.append(
                "Bonjour. Pose-moi une question sur la qualité des données NexaRetail, ou clique sur une suggestion."
            )
        elif intent == "help":
            parts.append(
                "Je fonctionne en deux temps : des outils Python calculent les chiffres, puis je les assemble. Je sais :\n"
                "- **comparer** les scénarios ;\n- **simuler** (« et si 15 % manquaient ? », « avec un panier à 1,3× ») ;\n"
                "- **chiffrer l'exposition** et son intervalle d'incertitude ;\n- trouver **à partir de quel taux bloquer**, ou quel taux atteint X M€ ;\n"
                "- **expliquer** un score ou un verdict, classer les **actions**, rédiger une **note de décision**.\n\n"
                "Je comprends les questions de suivi (« et pour critique ? »)."
            )
        elif intent == "compare":
            rows = [
                "| Scénario | Montants absents | Panier moyen | CA non vérifiable | Verdict | Indice |",
                "|---|---|---|---|---|---|",
            ]
            for s in SCENARIOS:
                m = allm[s]
                rows.append(
                    f"| {SCENARIO_NAME[s]} | {fmt(m['missing_pct'], 1)} % | {fmt(m['basket'], 2)} € | {eur_m(m['exposure'])} | {VERDICT[gate(m, th)['overall']][0]} | {health(m)['score']:.0f} |"
                )
                T(
                    f"kpis('{s}')",
                    f"{fmt(m['missing'])} absents, panier {fmt(m['basket'], 2)} €",
                )
            spread = allm["critical"]["basket"] - allm["low"]["basket"]
            ratio = (
                allm["critical"]["exposure"] / allm["low"]["exposure"]
                if allm["low"]["exposure"]
                else None
            )
            parts.append(
                "\n".join(rows)
                + f"\n\nEntre faible et critique, le panier moyen ne bouge que de {fmt(spread, 2)} € mais l'exposition est multipliée par {fmt(ratio, 1)} (N/D si la référence est nulle). "
                + (
                    "Les retards sont identiques ; aucun effet causal n’est démontré."
                    if len({round(m["late_pct"], 6) for m in allm.values()}) == 1
                    else "Les taux de retard diffèrent ; une segmentation est nécessaire pour comprendre les écarts."
                )
            )
        elif intent == "simulate":
            p = pct if pct is not None else ctx.get("pct", d["missing_pct"])
            r = mult if mult is not None else ctx.get("mult", 1.0)
            if not 0 <= p <= 100:
                parts.append("Le taux simulé doit être compris entre 0 et 100 %.")
                continue
            if r <= 0 or not np.isfinite(r):
                parts.append(
                    "Le multiplicateur de panier doit être strictement positif et fini."
                )
                continue
            n = round(d["orders"] * p / 100)
            expo = n * d["basket"] * r
            documented = (d["orders"] - n) * d["basket"]
            share = 100 * expo / (expo + documented) if expo + documented else 0
            T(
                "simulate(taux, multiplicateur)",
                f"{fmt(p, 1)} %, {fmt(r, 2)}× → {fmt(n)} commandes, {eur_m(expo)}",
            )
            formulas.append(
                "exposition = commandes sans montant × panier connu × multiplicateur"
            )
            parts.append(
                f"À **{fmt(p, 1)} %** de montants absents (scénario {SCENARIO_NAME[sc]}), **{fmt(n)} commandes** n'auraient pas de montant, soit {fmt(n - d['missing'])} de plus que l'observé. "
                f"Avec un panier à {fmt(r, 2)}× le panier connu ({fmt(d['basket'], 2)} €), l'exposition est d'environ **{eur_m(expo)}**, "
                f"soit {fmt(share, 1)} % du chiffre d'affaires total hypothétique.\n\nC'est une hypothèse : le Laboratoire de scénarios propose aussi une simulation Monte Carlo."
            )
            ctx.update(pct=p, mult=r)
        elif intent == "exposure":
            q5, q50, q95 = np.percentile(monte_carlo(d, 0.15), [5, 50, 95])
            T(
                f"kpis('{sc}')",
                f"{fmt(d['missing'])} × {fmt(d['basket'], 2)} € = {eur_m(d['exposure'])}",
            )
            T(
                "monte_carlo(sigma=15 %, n=20 000)",
                f"P5 {fmt(q5, 1)} / P50 {fmt(q50, 1)} / P95 {fmt(q95, 1)} M€",
            )
            formulas.append(
                "panier des commandes sans montant ~ log-normale de moyenne 1× et dispersion 15 %"
            )
            parts.append(
                f"Dans le scénario {SCENARIO_NAME[sc]}, {fmt(d['missing'])} commandes n'ont pas de montant. À panier moyen, le chiffre d'affaires non vérifiable est d'environ **{eur_m(d['exposure'])}**. "
                f"Sous une hypothèse log-normale non calibrée (sigma=0,15), la fourchette P5–P95 va de **{fmt(q5, 1)} à {fmt(q95, 1)} M€**. Le CA documenté est de {eur_m(d['known_rev'])}.\n\n"
                "Ce n'est pas une perte : ces commandes existent, leur montant est absent."
            )
        elif intent == "solve":
            if target is not None:
                if target <= 0 or (mult is not None and mult <= 0):
                    parts.append(
                        "La cible d’exposition et le multiplicateur doivent être strictement positifs."
                    )
                    continue
                denom = d["orders"] * d["basket"] * (mult or 1.0)
                p = 100 * target * 1e6 / denom
                T(
                    "solve_rate(cible_M€)",
                    f"{fmt(target, 1)} M€ → {fmt(p, 2)} % de montants absents",
                )
                formulas.append(
                    "taux = cible ÷ (commandes × panier connu × multiplicateur)"
                )
                parts.append(
                    f"Pour atteindre **{fmt(target, 1)} M€** d'exposition dans le scénario {SCENARIO_NAME[sc]}, il faudrait environ **{fmt(p, 1)} %** de commandes sans montant"
                    + (
                        f", soit {fmt(d['orders'] * p / 100)} commandes."
                        if p <= 100
                        else ". C'est supérieur à 100 % : la cible dépasse le chiffre d'affaires total."
                    )
                    + f" Le scénario {SCENARIO_NAME[sc]} est à {fmt(d['missing_pct'], 1)} %."
                )
            else:
                nb = d["orders"] * th["m_fail"] / 100
                T(
                    "gate_threshold()",
                    f"blocage à {th['m_fail']} %, réserves à {th['m_warn']} %",
                )
                margin = th["m_fail"] - d["missing_pct"]
                parts.append(
                    f"Avec la politique actuelle, le blocage se déclenche **au-delà de {fmt(th['m_fail'], 1)} %** de montants absents, soit {fmt(nb)} commandes et {eur_m(nb * d['basket'])} d'exposition. "
                    f"Les réserves commencent à {fmt(th['m_warn'], 1)} %. Le scénario {SCENARIO_NAME[sc]} est à {fmt(d['missing_pct'], 1)} % : "
                    + (
                        f"il reste {fmt(margin, 1)} point(s) de marge avant le blocage."
                        if margin >= 0
                        else f"il dépasse le seuil de {fmt(-margin, 1)} point(s)."
                    )
                )
                formulas.append("seuils réglables dans la Porte de décision")
        elif intent == "basket":
            T(
                f"kpis('{sc}')",
                f"AVG(order_total) = {fmt(d['basket'], 2)} € sur {fmt(d['known'])} commandes",
            )
            parts.append(
                f"Le panier moyen de **{fmt(d['basket'], 2)} €** est calculé sur {fmt(d['known'])} commandes avec montant ({fmt(d['complete_pct'], 1)} % du total). "
                "On ne peut pas l'étendre aux autres sans savoir pourquoi leurs montants manquent. Si l'absence est indépendante des valeurs (MCAR), l'estimation reste utilisable sous conditions ; "
                "si elle dépend de la valeur (MNAR), un biais est possible.\n\nTest à faire : comparer magasin, canal, période et catégorie entre commandes avec et sans montant."
            )
            formulas.append("AVG(order_total) hors NULL")
        elif intent == "late":
            T(
                f"kpis('{sc}')",
                f"{fmt(d['late'])} retards / {fmt(d['deliveries'])} évaluables",
            )
            same = len({round(m["late_pct"], 6) for m in allm.values()}) == 1
            parts.append(
                f"{fmt(d['late'])} livraisons sont en retard sur {fmt(d['deliveries'])} évaluables, soit **{fmt(d['late_pct'], 2)} %**. Le dénominateur n'est pas le nombre de commandes : "
                "seules les livraisons où date prévue et date réelle sont comparables comptent."
                + (
                    " Ce taux est identique dans les trois scénarios : aucun effet causal n'est démontré."
                    if same
                    else ""
                )
                + " Aucune cause n'est identifiable avec des agrégats : découper par transporteur, zone et période."
            )
            formulas.append("retards ÷ livraisons évaluables")
        elif intent == "risk":
            r = recs[0]
            parts.append(
                f"Le risque principal est l'absence de montants ({fmt(d['missing_pct'], 2)} % des commandes). Priorité : **{r['t'].lower()}**. {r['why']}\n\nIndice de santé : {hs['score']:.0f}/100."
            )
            T(f"recommendations('{sc}')", f"{len(recs)} actions, première : {r['t']}")
        elif intent == "actions":
            parts.append(
                "Actions classées par impact puis effort :\n\n"
                + "\n".join(
                    f"{i}. **{r['t']}** : {r['why']}" for i, r in enumerate(recs, 1)
                )
            )
            T(f"recommendations('{sc}')", f"{len(recs)} actions")
            formulas.append("tri : impact décroissant, effort croissant")
        elif intent in ("score", "why"):
            label = VERDICT[g["overall"]][0]
            T(
                f"health('{sc}')",
                f"{hs['score']:.0f}/100 (−{fmt(hs['lost_missing'], 1)} pts montants, −{fmt(hs['lost_late'], 1)} pts retards)",
            )
            T(f"gate('{sc}')", label)
            bad = [c for c in g["checks"] if c[2] != "go"]
            parts.append(
                f"Indice de santé **{hs['score']:.0f}/100** : en partant de 100, les montants absents coûtent **{fmt(hs['lost_missing'], 1)} points** et les retards **{fmt(hs['lost_late'], 1)} points**. "
                f"Verdict : **{label}**."
                + (
                    "\n\nPoints qui pèsent sur le verdict :\n"
                    + "\n".join(f"- {c[0]} : {c[1]} ({c[3].lower()})" for c in bad)
                    if bad
                    else " Aucun seuil n'est dépassé."
                )
                + "\n\nL'indice est pédagogique : 60 % complétude, 40 % ponctualité."
            )
            formulas += [
                "complétude = 100 − 5 × % absents",
                "ponctualité = 100 − 2 × % retards",
            ]
        elif intent == "gate":
            label = VERDICT[g["overall"]][0]
            T(f"gate('{sc}')", label)
            parts.append(
                f"Verdict de la porte qualité : **{label}**.\n\n"
                + "\n".join(
                    f"- {c[0]} : {c[1]}, {VERDICT[c[2]][0].lower()}. {c[3]}."
                    for c in g["checks"]
                )
            )
            formulas += [c[3] for c in g["checks"]]
        elif intent == "glossary":
            parts.append(
                "- **Complétude** : part des commandes dont le montant est renseigné.\n- **Livraison évaluable** : livraison où date prévue et date réelle sont comparables.\n"
                "- **MCAR** : l'absence ne dépend d'aucune valeur ; l'estimation peut rester non biaisée sous conditions.\n- **MAR** : l'absence dépend de variables observées (magasin, canal).\n"
                "- **MNAR** : l'absence dépend de la valeur manquante elle-même ; biais possible.\n- **CA non vérifiable** : commandes sans montant × panier connu, hypothèse de travail."
            )
        elif intent == "memo":
            parts.append(memo_markdown(d, sc, g, hs, recs))
            T(
                "memo_markdown()",
                "note générée à partir des KPI, du verdict et des actions",
            )
        elif intent == "method":
            parts.append(
                "Les chiffres viennent de Python/SQL ou d'une référence figée, jamais d'un modèle de langage. Ma réponse suit trois étapes : 1) détecter intention et paramètres ; "
                "2) appeler des outils déterministes (KPI, simulation, Monte Carlo, règles) ; 3) rédiger. Chaque appel est listé dans « Preuves et méthode ». "
                "Avec Ollama, le modèle reformule les résultats des outils et chaque nombre est recoupé : ceux qu'on ne retrouve pas sont signalés. Aucun mode ne prouve de causalité."
            )

    ctx.update(intent=picks[0], scenario=sc)
    return {
        "text": "\n\n---\n\n".join(parts),
        "evidence": trace + formulas,
        "intent": " + ".join(picks),
        "kind": KIND.get(picks[0], "Information"),
        "followups": FOLLOWUPS.get(picks[0], DEFAULT_FOLLOW),
        "scenario": sc,
    }


def _tokens(s: str) -> set[str]:
    return {
        re.sub(r"\D", "", t) for t in re.findall(r"\d[\d\s\u202f]*(?:[.,]\d+)?", s)
    } - {""}


def _local_ollama_host() -> str:
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    parsed = urlparse(host)
    if parsed.scheme not in ("http", "https") or parsed.hostname not in (
        "localhost",
        "127.0.0.1",
        "::1",
    ):
        raise ValueError(
            "Ollama doit utiliser une adresse locale (localhost ou 127.0.0.1)."
        )
    return host.rstrip("/")


def ollama_answer(question: str, allm: dict, history: list[dict], base: dict) -> dict:
    """Le modèle local ne calcule rien : il rédige à partir des résultats d'outils, puis chaque nombre est recoupé."""
    host = _local_ollama_host()  # validé AVANT toute construction de requête
    model = st.session_state.get("chat_model") or os.getenv(
        "CONSULTAI_OLLAMA_MODEL", "llama3.2:1b"
    )
    facts = "\n".join(
        f"- {SCENARIO_NAME[s]}: commandes {fmt(m['orders'])}, montants absents {fmt(m['missing'])} ({fmt(m['missing_pct'], 2)} %), panier moyen {fmt(m['basket'], 2)} €, "
        f"retards {fmt(m['late'])} sur {fmt(m['deliveries'])} ({fmt(m['late_pct'], 2)} %), CA non vérifiable {eur_m(m['exposure'])}"
        for s, m in allm.items()
    )
    verified = base["text"]
    style = st.session_state.get("response_style", "Conversation")
    system = (
        "Tu es l'analyste de ConsultAI 360 (entreprise fictive NexaRetail, données synthétiques). Réponds en français, avec un ton naturel de collègue analyste. Réponds directement, rebondis sur la demande et pose une seule question précise si le besoin est ambigu. Adapte la longueur au besoin. Évite les formules répétitives, les longues listes systématiques et le jargon. Utilise le contexte des échanges, mais les chiffres actuels ci-dessous priment sur les anciens messages. Si la demande porte sur une méthode, explique-la avec les connaissances générales en la distinguant des résultats observés. Ne prétends jamais avoir exécuté une requête ou une action métier.  "
        "Appuie-toi UNIQUEMENT sur les KPI et les RÉSULTATS VÉRIFIÉS ci-dessous. Ne change aucun chiffre, n'en invente aucun, ne conclus jamais à une causalité. "
        "Évite les listes numérotées et tout chiffre nouveau, y compris coûts, délais et pourcentages supposés. Si les résultats ne répondent pas à la question, demande une précision. Format demandé : "
        + style
        + ".\n\nKPI :\n"
        + facts
        + "\n\nRÉSULTATS VÉRIFIÉS :\n"
        + verified
    )
    msgs = (
        [{"role": "system", "content": system}]
        + [{"role": h["role"], "content": h["content"]} for h in history[-12:]]
        + [{"role": "user", "content": question}]
    )
    req = urllib.request.Request(
        host + "/api/chat",
        headers={"Content-Type": "application/json"},
        data=json.dumps(
            {
                "model": model,
                "stream": False,
                "options": {"temperature": 0.25, "num_predict": 900},
                "messages": msgs,
            }
        ).encode(),
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        text = json.load(r)["message"]["content"]
    allowed = _tokens(facts + " " + verified)
    unknown = sorted(t for t in _tokens(text) if t not in allowed)
    ev = base["evidence"] + [f"rédaction par le modèle local : {model}"]
    accepted = bool(text.strip()) and not unknown
    if not accepted:
        ev.append(
            "nombres non retrouvés dans les résultats d'outils : " + ", ".join(unknown)
        )
        text = base["text"]
        ev.append("Reformulation rejetée : réponse déterministe utilisée à la place.")
    return {
        **base,
        "text": text,
        "evidence": ev,
        "intent": base["intent"] + (" + ollama" if accepted else ""),
    }


@st.cache_data(ttl=30, show_spinner=False)
def local_models() -> tuple[list[str], str]:
    if PUBLIC:
        return [], "Démo : réponses calculées, modèle local désactivé"
    try:
        with urllib.request.urlopen(
            _local_ollama_host() + "/api/tags", timeout=2
        ) as response:
            names = sorted(
                {str(item["name"]) for item in json.load(response).get("models", [])}
            )
        return names, (
            "Modèle local disponible"
            if names
            else "Ollama accessible, aucun modèle installé"
        )
    except Exception:
        return [], "Modèle local indisponible · outils de calcul disponibles"


def conversational_answer(question, scenario, allm, th, ctx, history, style):
    """Suit les reprises de conversation et fournit une analyse vérifiable."""
    question = question.strip()[:1200]
    raw = norm(question).strip(" ?!. ")
    if re.search(r"\b(quelle heure|heure actuelle|quelle date|quel jour)\b", raw):
        now = datetime.now(ZoneInfo("Europe/Paris"))
        text = f"À Paris (Europe/Paris), il est **{now:%H:%M}** le **{now:%d/%m/%Y}**."
        return {"text": text, "intent": "date_heure", "kind": "Heure locale", "scenario": scenario, "evidence": [], "followups": []}
    corrected, _ = correct_question(question)
    words = norm(corrected)
    if (re.search(r"\b(combien|cmb|nombre)\b", words)
            and re.search(r"\b(commandes?|montants?)\b", words)
            and re.search(r"\b(sans|absents?|manqu\w*|pas de)\b", words)
            and not re.search(r"\d\s*%|et si", words)):
        named = [name for name, pattern in SC_WORDS.items() if re.search(pattern, words)]
        selected = named[0] if len(named) == 1 else scenario
        data = allm[selected]
        text = f"**{fmt(data['missing'])} commandes** n’ont pas de montant sur **{fmt(data['orders'])}**, soit **{fmt(data['missing_pct'], 2)} %** (scénario {SCENARIO_NAME[selected].lower()})."
        ctx.update(scenario=selected, intent="risk")
        return {"text": text, "intent": "montants_absents", "kind": "Calcul vérifié", "scenario": selected, "evidence": ["Commandes sans montant / commandes du scénario"], "followups": []}
    last = next((m for m in reversed(history) if m["role"] == "assistant"), None)
    if (
        raw
        in ("plus court", "resume", "resume ca", "en bref", "synthetise", "plus simple")
        and last
    ):
        paragraphs = [
            x.strip()
            for x in last["content"].split("\n\n")
            if x.strip() and not x.startswith("#")
        ]
        text = "\n\n".join(paragraphs[:2]) or last["content"]
        return {
            "text": text,
            "intent": "reformulation",
            "kind": "Synthèse",
            "scenario": last.get("scenario", scenario),
            "evidence": last.get("evidence", []),
            "followups": ["Développe l’analyse", "Que faire en priorité ?"],
        }
    if (
        raw
        in (
            "developpe",
            "detaille",
            "developpe l'analyse",
            "explique davantage",
            "et pourquoi",
            "pourquoi",
        )
        and last
    ):
        question = "Explique le diagnostic et les actions du scénario " + ctx.get(
            "scenario", scenario
        )
    if raw in ("merci", "merci beaucoup", "ok merci", "parfait"):
        return {
            "text": "Avec plaisir. Tu peux poursuivre avec une simulation, examiner les actions prioritaires ou préparer ta restitution.",
            "intent": "conversation",
            "kind": "Échange",
            "scenario": scenario,
            "evidence": [],
            "followups": ["Prépare ma restitution", "Que faire en priorité ?"],
        }
    normalized = raw.replace("’", "'")
    if any(
        t in normalized
        for t in (
            "analyse complete",
            "analyse approfondie",
            "analyse globale",
            "diagnostic complet",
            "prepare ma restitution",
        )
    ):
        m = allm[scenario]
        decision = gate(m, th)
        actions = recommendations(m, th)
        gap = th["m_fail"] - m["missing_pct"]
        text = (
            f"### Ce que je retiens\n\nLe scénario **{SCENARIO_NAME[scenario]}** est **{VERDICT[decision['overall']][0].lower()}** selon tes seuils. "
            f"Il manque le montant de **{fmt(m['missing'])} commandes**, soit **{fmt(m['missing_pct'], 2)} %**. "
            f"Le taux de retard est de **{fmt(m['late_pct'], 2)} %** sur les livraisons évaluables.\n\n"
            f"### Ce que cela implique\n\nLe CA documenté est **{eur_m(m['known_rev'])}**. L’exposition estimée de **{eur_m(m['exposure'])}** repose sur l’hypothèse du panier moyen connu. "
            f"La distance au seuil de blocage des montants est de **{fmt(gap, 2)} points de pourcentage**.\n\n"
            "### Ce que je te propose\n\n"
            + "\n".join(
                f"{i}. **{a['t']}** — {a['why']}" for i, a in enumerate(actions[:3], 1)
            )
            + "\n\n**À vérifier ensuite :** répartition des montants absents par magasin, canal et période. Les agrégats disponibles ne permettent pas de localiser les causes."
        )
        ctx.update(scenario=scenario, intent="risk")
        return {
            "text": text,
            "intent": "diagnostic_complet",
            "kind": "Analyse vérifiée",
            "scenario": scenario,
            "evidence": [
                "KPI du scénario actif",
                "gate() : seuils actifs",
                "recommendations() : priorité impact/effort",
                "Exposition : montants absents × panier connu",
            ],
            "followups": [
                "Et pour le scénario critique ?",
                "Et si 15 % des montants manquaient ?",
                "Rédige une note de décision",
            ],
        }
    result = respond(question, scenario, allm, th, ctx)
    if result["intent"] == "aucune":
        result["text"] = (
            "Pour t’aider précisément, quel angle veux-tu examiner : les montants absents, les retards, la publication du CA ou la méthode d’analyse ? Tu peux aussi me décrire la décision que tu prépares."
        )
    result["text"] = result["text"].replace(
        "Bonjour. Pose-moi une question sur la qualité des données NexaRetail, ou clique sur une suggestion.",
        "Bonjour. On peut partir de ton objectif : comprendre les risques, décider quoi publier ou préparer les actions. Quel point veux-tu creuser ?",
    )
    if (
        style == "Synthèse"
        and result["intent"] not in ("compare", "memo")
        and not result["intent"].startswith("projet_")
    ):
        result["text"] = "\n\n".join(result["text"].split("\n\n")[:3])
    elif style == "Analyse détaillée" and result["intent"] in (
        "risk",
        "actions",
        "gate",
    ):
        result["text"] += (
            "\n\n**Pour vérifier ce diagnostic :** rapprocher les montants avec la source, contrôler les jointures et comparer les taux par magasin, canal et période avant d’attribuer une cause."
        )
    ctx["last_question"] = question
    return result


def evidence_payload(d: dict, scenario: str, demo: bool, th: dict) -> dict:
    return {
        "scenario": scenario,
        "source": "reference_frozen" if demo else "postgresql_read_only",
        "observed": {
            k: d[k]
            for k in (
                "orders",
                "missing",
                "known",
                "basket",
                "deliveries",
                "late",
                "missing_pct",
                "late_pct",
                "known_rev",
            )
        },
        "hypothesis": {
            "unverified_revenue": d["exposure"],
            "method": "missing_orders * observed_basket",
            "not_measured": True,
        },
        "policy": dict(th),
        "verdict": gate(d, th)["overall"],
        "limits": [
            "synthetic_data",
            "no_causal_inference",
            "missing_values_not_recovered",
        ],
    }
