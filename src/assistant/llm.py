import json
import re
from urllib import error, request

from .business_rules import build_business_facts
from .kpi import delivery, overview

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:1b"


def _commentaire_valide(texte: str) -> bool:
    """Vérifie les règles minimales de qualité du commentaire IA."""

    # 1. Vérifier que la réponse contient suffisamment de texte
    if not isinstance(texte, str) or len(texte.strip()) < 40:
        return False

    contenu = texte.lower()

    # 2. Vérifier la présence des trois sections obligatoires
    sections = (
        "diagnostic",
        "limites",
        "recommandations",
    )

    if not all(section in contenu for section in sections):
        return False

    # 3. Retirer les numéros de listes éventuels
    texte_sans_listes = re.sub(
        r"(?m)^\s*\d+[\.\)]\s+",
        "",
        texte,
    )

    # 4. Rejeter les chiffres présents dans le commentaire
    # Les chiffres officiels sont déjà fournis par Python
    if re.search(r"\d", texte_sans_listes):
        return False

    # 5. Rejeter certaines affirmations métier trompeuses
    expressions_interdites = (
        "commandes manquantes",
        "commandes absentes",
        "perte de revenus",
        "pertes de revenus",
        "revenus perdus",
        "chiffre d'affaires perdu",
    )

    if any(expression in contenu for expression in expressions_interdites):
        return False

    return True


def analyse_business(scenario: str = "medium") -> dict:
    """Analyse hybride : KPI PostgreSQL + règles Python + Ollama."""

    # 1. Récupérer les KPI calculés par PostgreSQL
    commercial = overview(scenario)
    logistique = delivery(scenario)

    # 2. Construire les faits métier vérifiés
    faits = build_business_facts(commercial, logistique)

    # 3. Préparer une réponse de secours
    secours = (
        "Diagnostic : les indicateurs ont été calculés par PostgreSQL.\n"
        "Limites : les montants manquants peuvent limiter "
        "l'interprétation des résultats.\n"
        "Recommandations : contrôler les montants manquants "
        "et examiner les retards de livraison."
    )

    # 4. Préparer les instructions destinées à Ollama
    prompt = f"""
Tu es un consultant Data chargé de commenter des KPI vérifiés.

FAITS CERTAINS :
{faits}

ATTENTION :
- Toutes les commandes existent.
- Certaines commandes ont un montant non renseigné.
- Un montant manquant n'est PAS une commande manquante.
- Les livraisons en retard existent, mais leurs causes sont inconnues.
- Les chiffres ont déjà été calculés par Python.

MISSION :
Rédige uniquement trois sections courtes.

Diagnostic :
Explique que les montants non renseignés limitent la lecture
des résultats commerciaux et que les retards méritent une analyse.

Limites :
Explique qu'on ne connaît pas encore les causes des montants
non renseignés ni celles des retards.

Recommandations :
Propose de vérifier les montants non renseignés et d'analyser
les causes des retards.

RÈGLES STRICTES :
- Écris obligatoirement les trois titres :
  Diagnostic, Limites, Recommandations.
- Aucun chiffre dans ta réponse.
- Aucune liste numérotée.
- N'invente aucune cause.
- Ne parle jamais de commandes absentes ou manquantes.
- N'affirme pas que les commandes sont de mauvaise qualité.
- Ne répète pas les faits chiffrés.
- Réponds en français.
- Maximum 100 mots.
"""

    # 5. Construire la requête HTTP vers Ollama
    payload = json.dumps(
        {
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0},
        }
    ).encode("utf-8")

    # 6. Utiliser le fallback par défaut
    mode = "fallback"
    commentaire = secours

    # 7. Interroger Ollama
    try:
        req = request.Request(
            OLLAMA_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with request.urlopen(req, timeout=120) as response:
            resultat = json.loads(response.read().decode("utf-8"))

        proposition = resultat.get("response", "")

        # 8. Accepter uniquement les commentaires conformes
        if _commentaire_valide(proposition):
            commentaire = proposition
            mode = "ollama"

    except (error.URLError, TimeoutError, ValueError, OSError):
        # En cas d'erreur, conserver la réponse de secours
        pass

    # 9. Retourner les faits vérifiés et le commentaire
    return {
        "mode": mode,
        "scenario": scenario,
        "reponse": (f"FAITS VÉRIFIÉS\n{faits}\n\nINTERPRÉTATION\n{commentaire}"),
        "kpi": {
            "commercial": commercial,
            "logistique": logistique,
        },
    }
