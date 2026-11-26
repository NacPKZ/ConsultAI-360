"""Assistant de mission : sélection d'outils autorisés, calculs vérifiés, contexte explicite.

Ollama peut reconnaître une intention, jamais fabriquer une valeur ou exécuter du SQL.
Sans modèle local, les mêmes outils restent accessibles par le routeur déterministe.
"""

from __future__ import annotations

import json
import os
import re
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from project_knowledge import correct, norm, project_answer
from src.assistant.console import (
    SCENARIOS,
    SCENARIO_NAMES,
    fmt,
    impact,
    money,
    priorities,
)

INTENTS = {
    "summary",
    "compare",
    "revenue",
    "missing",
    "basket",
    "delivery",
    "actions",
    "simulation",
    "sources",
    "method",
    "unknown",
}
SCENARIO_WORDS = {
    "low": r"\b(faible|low|bas)\b",
    "medium": r"\b(moyen|medium|median)\b",
    "critical": r"\b(critique|critical)\b",
}
PROMPTS = (
    "Que traiter en priorité ?",
    "Comparer les scénarios",
    "Que sait-on des retards ?",
)


def ollama_host() -> str:
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434").strip()
    parsed = urlparse(host)
    if (
        parsed.scheme not in ("http", "https")
        or parsed.hostname not in ("localhost", "127.0.0.1", "::1")
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
    ):
        raise ValueError(
            "Ollama doit être un service local, sans identifiants dans l’URL."
        )
    return host.rstrip("/")


def local_model() -> str | None:
    if os.getenv("CONSULTAI_DEMO_MODE", "").lower() in ("1", "true", "yes"):
        return None
    try:
        with urlopen(ollama_host() + "/api/tags", timeout=2) as response:
            names = {str(m["name"]) for m in json.load(response).get("models", [])}
        preferred = os.getenv("CONSULTAI_OLLAMA_MODEL", "llama3.2:1b")
        return preferred if preferred in names else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def classify_with_model(
    question: str, model: str, previous_intent: str = ""
) -> str | None:
    """La sortie JSON est une étiquette contrôlée ; aucune instruction issue du modèle n'est exécutée."""
    payload = {
        "model": model,
        "stream": False,
        "format": {
            "type": "object",
            "properties": {"intent": {"type": "string", "enum": sorted(INTENTS)}},
            "required": ["intent"],
            "additionalProperties": False,
        },
        "options": {"temperature": 0, "num_predict": 60},
        "messages": [
            {
                "role": "system",
                "content": "Classe la demande d'un analyste NexaRetail. Renvoie seulement l'objet JSON intent. summary=bilan, compare=scénarios, revenue=CA, missing=montants absents, basket=panier, delivery=livraisons, actions=priorités, simulation=hypothèse chiffrée, sources=traçabilité, method=méthode. unknown si hors périmètre. L'intention précédente est : "
                + previous_intent,
            },
            {"role": "user", "content": question[:1500]},
        ],
    }
    request = Request(
        ollama_host() + "/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            content = json.loads(json.load(response)["message"]["content"])
        if not isinstance(content, dict) or set(content) != {"intent"}:
            return None
        intent = content.get("intent")
        return intent if intent in INTENTS else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _intent(q: str, named: list[str], context: dict) -> str:
    if len(named) >= 2 or any(
        t in q
        for t in ("compar", "scenarios", "difference", "identique", "entre les", " vs ")
    ):
        return "compare"
    if any(
        t in q
        for t in ("et si", "simul", "hypothe", "passait", "manquaient", "manquait")
    ) or re.search(r"\d\s*%", q):
        return "simulation"
    if any(
        t in q
        for t in (
            "priorit",
            "en premier",
            "recommand",
            "que faire",
            "traiter",
            "plan d'action",
            "plan d’action",
            "action",
        )
    ):
        return "actions"
    if any(
        t in q
        for t in (
            "source",
            "tracabil",
            "provenance",
            "d'ou viennent",
            "d’où viennent",
            "calcul",
            "formule",
        )
    ):
        return "sources"
    if any(
        t in q for t in ("retard", "livraison", "transporteur", "logist", "ponctual")
    ):
        return "delivery"
    if "panier" in q:
        return "basket"
    if any(t in q for t in ("chiffre d", "revenu", "perte", "expos")) or re.search(
        r"\bca\b", q
    ):
        return "revenue"
    if any(
        t in q for t in ("manquant", "absent", "complet", "couverture", "renseigne")
    ):
        return "missing"
    if any(
        t in q
        for t in (
            "diagnostic",
            "bilan",
            "synthese",
            "resume",
            "situation",
            "risque",
            "analyse",
            "restitution",
            "note de decision",
        )
    ):
        return "summary"
    if any(
        t in q
        for t in ("methode", "comment verifier", "comment controler", "protocole")
    ):
        return "method"
    if context.get("intent") in INTENTS and (
        named
        or re.match(r"^(et |pourquoi|et pourquoi|developpe|plus court|et encore)", q)
    ):
        return context["intent"]
    return "unknown"


def answer(
    question: str,
    scenario: str,
    all_metrics: dict,
    context: dict | None = None,
    model: str | None = None,
) -> dict:
    if scenario not in SCENARIOS:
        raise ValueError("Scénario inconnu")
    # Une requête est isolée : ne jamais modifier le contexte de la session appelante.
    context = dict(context or {})
    corrected, _ = correct(question[:1500])
    q = re.sub(r"[?!;:]", " ", norm(corrected)).lower().strip()
    # « Panier moyen » est une mesure, pas une sélection du scénario moyen.
    entity_text = re.sub(r"\b(panier|delai|montant|temps) moyen\b", "mesure", q)
    named = [
        s for s, pattern in SCENARIO_WORDS.items() if re.search(pattern, entity_text)
    ]
    active = named[0] if len(named) == 1 else scenario
    if not named and re.match(r"^(et |pourquoi|developpe|plus court)", q):
        active = context.get("scenario", scenario)
    if active not in SCENARIOS:
        active = scenario
    m = all_metrics[active]
    name = SCENARIO_NAMES[active].lower()
    proof = [
        f"Scénario {name} ; source : {'référence figée' if m['source'] == 'reference' else 'PostgreSQL, lecture seule (cache de 5 min)'}."
    ]
    intent = _intent(q, named, context)
    engine = "Calculs vérifiés"

    def result(text: str, kind: str = intent, followups: tuple | list = ()) -> dict:
        return {
            "text": text,
            "intent": kind,
            "scenario": active,
            "evidence": proof,
            "followups": list(followups)[:2],
            "engine": engine,
            "context": {
                "intent": kind,
                "scenario": active,
                **{
                    k: context[k]
                    for k in ("rate", "ratio", "simulation_metric")
                    if k in context
                },
            },
        }

    if re.search(
        r"\b(execute|executer|lance|lancer|ecris|supprime|drop|delete|insert|update)\b.*\b(sql|table|base|requete|database)\b",
        q,
    ):
        return result(
            "Je peux expliquer les résultats et leurs calculs. L’assistant n’exécute que les fonctions de lecture prévues dans l’application ; aucune commande SQL libre n’est exécutée.",
            "boundary",
        )

    # Ne pas attribuer une cause ou inventer une segmentation absente des agrégats.
    if any(
        t in q
        for t in (
            "quel magasin",
            "quels magasins",
            "quel transporteur",
            "quels transporteurs",
            "quelle zone",
            "quelles zones",
            "quel produit",
            "quels produits",
            "quelle periode",
            "quelles periodes",
            "quel canal",
        )
    ):
        return result(
            "Les données disponibles ici sont agrégées : elles ne permettent pas d’identifier les segments concernés. Il faut ventiler les montants absents par magasin, canal et période, ou les retards par transporteur et zone. Je ne peux pas désigner un responsable à partir de ces seuls totaux.",
            "scope",
        )

    if q.strip(" !?.") in (
        "bonjour",
        "salut",
        "hello",
        "merci",
        "merci beaucoup",
        "ok merci",
    ):
        return result(
            (
                "Bonjour. Quel point souhaitez-vous examiner : la qualité des montants, les retards ou les actions à prioriser ?"
                if "merci" not in q
                else "Avec plaisir. Les sources et les calculs restent consultables sous chaque réponse."
            ),
            "conversation",
            PROMPTS[:2],
        )

    if intent == "unknown":
        documented = project_answer(corrected)
        if documented:
            proof.extend(documented["evidence"])
            return result(documented["text"], "documentation")
        if model:
            selected = classify_with_model(corrected, model, context.get("intent", ""))
            if selected and selected != "unknown":
                intent = selected
                engine = "Intention reconnue par Ollama, calculs vérifiés"
        if intent == "unknown":
            return result(
                "Je n’ai pas assez d’éléments pour répondre. Souhaitez-vous examiner les montants absents, les retards de livraison ou comparer les scénarios ?",
                "unknown",
                PROMPTS[1:],
            )

    if intent == "compare":
        rows = [
            f"- **{SCENARIO_NAMES[s]}** : {fmt(all_metrics[s]['missing'])} montants absents, soit {fmt(all_metrics[s]['missing_pct'], 1)} % des commandes."
            for s in SCENARIOS
        ]
        rates = [round(all_metrics[s]["late_pct"], 8) for s in SCENARIOS]
        conclusion = (
            f"Le taux de retard reste à **{fmt(m['late_pct'], 2)} %** dans les trois scénarios : la dégradation simulée porte sur les montants, pas sur les livraisons."
            if len(set(rates)) == 1
            else "Les taux de retard diffèrent également. Il faut examiner les dates de livraison pour expliquer ces écarts."
        )
        proof.append(
            "Comparaison des volumes et taux de chaque scénario, sans mélanger commandes et livraisons."
        )
        return result(
            "\n".join(rows) + "\n\n" + conclusion,
            intent,
            ("Que traiter en priorité ?", "Et si 15 % des montants manquaient ?"),
        )

    if intent == "simulation":
        pct = re.search(r"(-?\d+(?:[.,]\d+)?)\s*%", q)
        delivery_question = any(t in q for t in ("retard", "livraison", "logisti"))
        amounts_question = any(t in q for t in ("montant", "panier", "manqu"))
        if delivery_question or (
            not amounts_question and context.get("simulation_metric") == "delivery"
        ):
            if not pct:
                return result(
                    "Quel taux de retard souhaitez-vous tester ? Indiquez un pourcentage de livraisons évaluables.",
                    "unknown",
                )
            rate = float(pct[1].replace(",", "."))
            if not 0 <= rate <= 100:
                return result("Le taux doit être compris entre 0 et 100 %.", "invalid")
            target = round(m["deliveries"] * rate / 100)
            context.update(rate=rate, simulation_metric="delivery")
            proof.append(
                "Hypothèse = arrondi(livraisons évaluables × taux de retard / 100). Aucun impact financier n'est déduit."
            )
            return result(
                f"À **{fmt(rate, 1)} %** de retard, environ **{fmt(target)} livraisons** seraient concernées, sur **{fmt(m['deliveries'])} évaluables**, contre **{fmt(m['late'])}** dans les données chargées.\n\nC’est un objectif hypothétique ; aucun effet d’une action logistique n’est démontré par ce calcul.",
                intent,
            )
        if not amounts_question and (
            any(t in q for t in ("croissance", "revenu", "chiffre d"))
            or re.search(r"\bca\b", q)
        ):
            return result(
                "Je peux faire varier le taux de montants absents, le panier supposé ou les retards. Une prévision de ventes nécessite d’autres données ; quel paramètre souhaitez-vous tester ?",
                "unknown",
            )
        coefficient = re.search(r"(-?\d+(?:[.,]\d+)?)\s*(?:x\b|×|fois\b)", q)
        rate = (
            float(pct[1].replace(",", "."))
            if pct
            else context.get("rate", m["missing_pct"])
        )
        ratio = (
            float(coefficient[1].replace(",", "."))
            if coefficient
            else context.get("ratio", 1.0)
        )
        try:
            simulated = impact(m, rate, ratio)
        except ValueError as exc:
            return result(str(exc), "invalid")
        context.update(rate=rate, ratio=ratio, simulation_metric="amounts")
        proof.append(
            "Hypothèse = arrondi(commandes × taux / 100) × panier connu × coefficient."
        )
        return result(
            f"Avec **{fmt(rate, 1)} %** de montants absents, **{fmt(simulated['missing'])} commandes** seraient concernées dans le scénario {name}. À **{fmt(ratio, 2)} fois** le panier connu, leur montant hypothétique serait de **{money(simulated['amount'])}**.\n\nCe calcul est une hypothèse de travail. Il ne mesure ni le montant réel de ces commandes ni une perte de revenus.",
            intent,
            ("Et si 2 % des montants manquaient ?", "Comment vérifier les montants ?"),
        )

    if intent == "delivery":
        proof.append(
            "Retards = date réelle > date prévue, uniquement lorsque les deux dates sont renseignées."
        )
        proof.append(f"Taux = {m['late']} / {m['deliveries']} × 100.")
        return result(
            f"**{fmt(m['late_pct'], 2)} %** des livraisons évaluables sont en retard : **{fmt(m['late'])} sur {fmt(m['deliveries'])}**.\n\nLes totaux ne donnent pas la cause des retards. **À vérifier :** leur répartition par transporteur et zone, puis les écarts entre dates prévues et réelles.",
            intent,
            ("Comparer les scénarios", "D’où viennent les chiffres ?"),
        )

    if intent == "basket":
        proof.append(
            "AVG(order_total) hors NULL ; le panier de la référence est arrondi à deux décimales."
        )
        return result(
            f"Le panier moyen est de **{fmt(m['basket'], 2)} €**, calculé sur **{fmt(m['known'])} commandes renseignées** ({fmt(m['complete_pct'], 1)} % du total).\n\nSon extension aux commandes sans montant suppose que celles-ci sont comparables. **À vérifier :** comparer les profils avec et sans montant par magasin, canal et période.",
            intent,
        )

    if intent == "revenue":
        label = (
            "Le CA reconstitué à partir du panier arrondi est d’environ"
            if m["revenue_approximate"]
            else "Le CA renseigné calculé en base est de"
        )
        proof.append(
            "CA = commandes renseignées × panier arrondi (approximation de démonstration)."
            if m["revenue_approximate"]
            else "CA = SUM(order_total) hors NULL dans dw.fact_orders."
        )
        proof.append(
            "Montant hypothétique des commandes sans montant = volume sans montant × panier connu."
        )
        return result(
            f"{label} **{money(m['known_rev'])}**, sur **{fmt(m['complete_pct'], 1)} % des commandes**.\n\nLes **{fmt(m['missing'])} commandes sans montant** représenteraient **{money(m['exposure'])}** si leur panier égalait le panier connu. Leur montant réel reste inconnu : ce n’est pas une perte mesurée.\n\n**À faire :** publier le CA avec sa couverture, puis rapprocher les montants avec la source.",
            intent,
            ("Le panier moyen est-il fiable ?", "Et si 15 % des montants manquaient ?"),
        )

    if intent == "missing":
        proof.append(
            f"Couverture = ({m['orders']} − {m['missing']}) / {m['orders']} × 100."
        )
        return result(
            f"**{fmt(m['missing'])} commandes** ont un montant absent dans le scénario {name}, soit **{fmt(m['missing_pct'], 2)} %**. Les commandes existent ; c’est le champ du montant qui manque.\n\n**À faire :** rapprocher ces enregistrements de la source et contrôler les jointures avant de recalculer le reporting.",
            intent,
            ("Quel est le chiffre d’affaires ?", "Comparer les scénarios"),
        )

    if intent == "sources":
        source = (
            "La démonstration utilise une **référence figée**, sans connexion à PostgreSQL. Le CA est reconstitué à partir du panier arrondi."
            if m["source"] == "reference"
            else "Les valeurs proviennent de **PostgreSQL en lecture seule**, avec un cache de cinq minutes. Le CA correspond à SUM(order_total) hors NULL."
        )
        proof.extend(
            [
                "Commandes et panier : overview(), dw.fact_orders.",
                "Livraisons : delivery(), dw.fact_shipments.",
                "Aucune requête SQL n'est générée par un modèle de langage.",
            ]
        )
        return result(
            source
            + "\n\nLes calculs reposent sur deux populations distinctes :\n- **Montants absents** : commandes sans montant / commandes.\n- **Retards** : livraisons en retard / livraisons dont les dates prévue et réelle sont renseignées.\n\nLe détail et l’export des valeurs sont dans **Traçabilité des données**.",
            intent,
        )

    if intent == "method":
        return result(
            "Pour contrôler le reporting :\n- rapprocher les identifiants de commande et les montants avec la source ;\n- comparer la couverture par magasin, canal et période ;\n- vérifier les jointures et les dates de livraison, puis recalculer les indicateurs.\n\nCe sont des vérifications à réaliser ; elles n’ont pas été exécutées par l’assistant.",
            intent,
        )

    if intent == "actions":
        actions = priorities(m)
        return result(
            "\n\n".join(f"**{a['title']}.** {a['detail']}" for a in actions)
            or "Aucune anomalie de montant ou de retard n’est présente dans les agrégats chargés.",
            intent,
            ("Quel est le chiffre d’affaires ?", "Que sait-on des retards ?"),
        )

    # Bilan compact, également utilisé pour préparer une restitution.
    return result(
        f"Dans le scénario **{name}**, **{fmt(m['missing_pct'], 1)} %** des commandes n’ont pas de montant et **{fmt(m['late_pct'], 2)} %** des livraisons évaluables sont en retard.\n\n**Priorité :** rapprocher les montants avec la source et afficher la couverture du CA. En parallèle, ventiler les retards par transporteur et zone. Les agrégats ne permettent pas encore d’en attribuer les causes.",
        "summary",
        PROMPTS[1:],
    )
