"""Base documentaire locale du copilote : réponses descriptives, jamais des KPI inventés."""

from __future__ import annotations

import difflib
import os
import re
import unicodedata

GITHUB = "https://github.com/NacPKZ/ConsultAI-360"
PAGES = {
    "mission control": (
        "Mission Control",
        "Synthèse exécutive, indicateurs et état de la mission.",
    ),
    "observatoire": (
        "Observatoire",
        "Comparaisons graphiques, couverture, pont de CA et sensibilité.",
    ),
    "investigation": (
        "Investigation",
        "Diagnostic des risques, contrôles et priorisation des investigations.",
    ),
    "scenario lab": (
        "Scenario Lab",
        "Hypothèses et simulations ; ne pas confondre projections et données observées.",
    ),
    "decision gate": (
        "Decision Gate",
        "Seuils de décision configurables et verdict de publication pédagogique.",
    ),
    "data lineage": (
        "Data Lineage",
        "Chaîne de preuve, dictionnaire des KPI et exports.",
    ),
    "ai copilot": (
        "AI Copilot",
        "Questions en langage naturel, outils de calcul, preuves et Ollama optionnel.",
    ),
}
TECH = {
    "python": "Python : préparation, logique métier, calculs, simulations et tests.",
    "sql": "SQL : interrogation et agrégation des tables du Data Warehouse PostgreSQL.",
    "postgresql": "PostgreSQL : stockage des données et tables analytiques, interrogées en lecture seule par le copilote.",
    "power bi": "Power BI : tableaux de bord analytiques du projet ; distincts de cette interface Streamlit.",
    "streamlit": "Streamlit : interface interactive de cette application, graphiques Plotly et copilote.",
    "plotly": "Plotly : graphiques interactifs de l'application Streamlit.",
    "ollama": "Ollama : modèle de langage local facultatif pour reformuler les réponses ; ne calcule pas les KPI.",
    "github": "GitHub : code source, historique et documentation du projet.",
    "git": "Git : suivi des versions et collaboration ; GitHub héberge le dépôt.",
    "machine learning": "Machine learning : volet de prédiction des retards de livraison sur un dataset public distinct. Ce n'est pas un modèle entraîné par le copilote.",
    "ml": "Machine learning : volet de prédiction des retards de livraison sur un dataset public distinct.",
    "excel": "Excel : outil de manipulation et d'analyse, à distinguer des calculs SQL/Python présentés ici.",
    "dbt": "dbt : outil de transformation et de documentation SQL ; ne pas présumer de son déploiement sans preuve dans le dépôt.",
}
# Corrections volontairement restreintes aux termes métier, pour ne pas déformer les questions.
TERMS = (
    "consultai",
    "nexaretail",
    "observatoire",
    "investigation",
    "scenario",
    "mission",
    "control",
    "decision",
    "gate",
    "lineage",
    "copilot",
    "github",
    "linkedin",
    "streamlit",
    "postgresql",
    "python",
    "power",
    "plotly",
    "ollama",
    "livraison",
    "retard",
    "montants",
    "manquants",
    "chiffre",
    "affaires",
    "panier",
    "qualite",
    "risque",
    "compare",
    "comparaison",
    "simuler",
    "simulation",
    "completude",
    "projet",
    "createur",
    "auteur",
    "profil",
    "presentation",
    "fonctionnement",
    "documentation",
    "architecture",
    "donnees",
    "tableaux",
    "bord",
    "scenario",
    "critique",
    "faible",
    "moyen",
    "resume",
    "synthese",
    "decision",
    "seuil",
    "methode",
    "fiabilite",
)
ALIASES = {
    "linkdin": "linkedin",
    "linkedln": "linkedin",
    "linkdln": "linkedin",
    "gitub": "github",
    "githube": "github",
    "gituhb": "github",
    "consutlai": "consultai",
    "consultia": "consultai",
    "nexaretial": "nexaretail",
    "powerbi": "power bi",
    "powerbii": "power bi",
    "stramlit": "streamlit",
    "postgress": "postgresql",
    "retarrd": "retard",
    "retarrds": "retards",
    "livraisons": "livraison",
    "livrasion": "livraison",
    "senario": "scenario",
    "scenrio": "scenario",
}


def norm(text: str) -> str:
    return "".join(
        c
        for c in unicodedata.normalize("NFKD", text.lower())
        if not unicodedata.combining(c)
    )


def correct(text: str) -> tuple[str, list[tuple[str, str]]]:
    fixes = []

    def fix(match):
        original = match.group(0)
        token = norm(original)
        if len(token) < 5 or token.isnumeric():
            return original
        replacement = ALIASES.get(token)
        if replacement is None and token not in TERMS:
            # Seuil strict : éviter de remplacer des mots ordinaires proches.
            candidate = difflib.get_close_matches(token, TERMS, n=1, cutoff=0.86)
            if candidate and (token[0] == candidate[0][0]):
                replacement = candidate[0]
        if replacement and replacement != token:
            fixes.append((original, replacement))
            return replacement
        return original

    return re.sub(r"[A-Za-zÀ-ÿ]+", fix, text), fixes


def profile() -> dict:
    # Ne jamais inventer un nom complet ni une URL LinkedIn.
    name = os.getenv("CONSULTAI_AUTHOR_NAME", "Can Pekgoz").strip()
    role = os.getenv(
        "CONSULTAI_AUTHOR_ROLE",
        "Étudiant en Master BIDABI (Data & Business Intelligence)",
    ).strip()
    li = os.getenv(
        "CONSULTAI_LINKEDIN_URL", "https://www.linkedin.com/in/can-pekgoz/"
    ).strip()
    if not re.fullmatch(
        r"https://(?:www\.)?linkedin\.com/(?:in|company)/[A-Za-z0-9_\-%/]+/?(?:\?[^\s]*)?",
        li,
    ):
        li = ""
    return {"name": name, "role": role, "github": GITHUB, "linkedin": li}


def project_answer(question: str) -> dict | None:
    q = norm(question)
    p = profile()

    def out(text, topic):
        return {
            "text": text,
            "topic": topic,
            "evidence": [
                "Base documentaire locale de l'application (description, pas une mesure SQL)."
            ],
            "followups": [
                "Où se trouve l'Observatoire ?",
                "Qui a créé le projet ?",
                "Comment fonctionne le copilote ?",
            ],
        }

    if any(
        x in q
        for x in (
            "qui suis je",
            "qui suis-je",
            "mon profil",
            "mon linkedin",
            "mon github",
            "mon git",
            "mes reseaux",
            "qui a cree",
            "qui est le createur",
            "qui est l auteur",
            "qui est l'auteur",
            "ton createur",
            "qui a fait le projet",
            "contact",
            "auteur du projet",
        )
    ):
        li = (
            f"[LinkedIn]({p['linkedin']})"
            if p["linkedin"]
            else "LinkedIn non configuré : définir `CONSULTAI_LINKEDIN_URL` dans l'environnement."
        )
        return out(
            f"**Auteur / porteur du projet :** {p['name']}\n\n**Profil :** {p['role']}\n\n**GitHub :** [ConsultAI 360]({p['github']})\n\n**LinkedIn :** {li}",
            "Profil",
        )
    if any(
        x in q
        for x in (
            "qui es tu",
            "qui es-tu",
            "tu es qui",
            "presente toi",
            "ton role",
            "c est quoi consultai",
            "qu est ce que consultai",
        )
    ):
        return out(
            "Je suis **le copilote de ConsultAI 360**, une application de démonstration d'une mission de conseil Data & IA pour **NexaRetail**, entreprise fictive. Je réponds sur les KPI, les scénarios, les règles de décision et la structure du projet. Les calculs viennent de SQL/Python ; Ollama peut seulement reformuler les résultats. Je ne peux pas consulter arbitrairement tous les fichiers du dépôt ni exécuter des actions métier.",
            "Identité",
        )
    if any(x in q for x in ("github", "linkedin", "portfolio", "depot", "repository")):
        if "linkedin" in q:
            return out(
                f"Profil LinkedIn : [ouvrir le profil]({p['linkedin']})."
                if p["linkedin"]
                else "Le profil LinkedIn n'est pas encore renseigné. Configurer `CONSULTAI_LINKEDIN_URL` avec l'URL publique exacte.",
                "Profil",
            )
        return out(
            f"Dépôt GitHub officiel du projet : [ConsultAI 360]({GITHUB}). Vous y trouverez le code et les documents effectivement publiés.",
            "Ressource",
        )
    if any(
        x in q
        for x in (
            "ou se trouve",
            "ou est",
            "dans quelle page",
            "quelle page",
            "ou trouver",
            "ou sont",
            "naviguer",
            "navigation",
            "menu",
            "barre laterale",
        )
    ):
        for key, (label, desc) in PAGES.items():
            if key in q or any(
                alias in q
                for alias in {
                    "mission control": ("accueil", "synthese", "kpi"),
                    "observatoire": ("graphique", "graphe", "graphiques"),
                    "investigation": ("diagnostic", "risque"),
                    "scenario lab": ("simulation", "simulateur"),
                    "decision gate": ("seuil", "verdict"),
                    "data lineage": ("source", "dictionnaire", "tracabilite"),
                    "ai copilot": ("chat", "assistant", "ia"),
                }[key]
            ):
                return out(
                    f"**{label}** : {desc}\n\nOuvrez **{label}** dans la barre latérale, rubrique « Explorer la mission ».",
                    "Navigation",
                )
        return out(
            "La barre latérale donne accès à : "
            + "; ".join(f"**{v[0]}** ({v[1]})" for v in PAGES.values()),
            "Navigation",
        )
    if any(
        x in q
        for x in (
            "architecture",
            "technologie",
            "technos",
            "outils utilises",
            "stack",
            "comment fonctionne le projet",
            "etapes du projet",
            "phases du projet",
            "structure du projet",
            "comment marche consultai",
        )
    ):
        return out(
            "**Chaîne du projet :** données synthétiques NexaRetail → audit et nettoyage → PostgreSQL / Data Warehouse → calculs SQL/Python → visualisations Power BI et Streamlit → simulations et règles → copilote IA optionnel.\n\n**Volet ML :** prédiction des retards de livraison sur un dataset public distinct.\n\n**Limite :** cette présentation est un plan fonctionnel, pas un audit automatique du dépôt ni une garantie que chaque module est déployé.",
            "Architecture",
        )
    if any(
        x in q
        for x in (
            "nexaretail",
            "donnees synthetiques",
            "donnees fictives",
            "entreprise fictive",
        )
    ) and not any(
        x in q for x in ("retard", "montant", "panier", "scenar", "risque", "livraison")
    ):
        return out(
            "**NexaRetail** est l'entreprise fictive du cas d'étude. Ses données de commerce et de logistique sont synthétiques ; elles permettent de simuler des problèmes de qualité et d'étudier leurs conséquences sur la décision. Les chiffres de la démo sont des références figées, pas des données de production.",
            "Projet",
        )
    for tech in sorted(TECH, key=len, reverse=True):
        if re.search(r"(?<![a-z])" + re.escape(tech) + r"(?![a-z])", q) and any(
            x in q
            for x in (
                "sert",
                "outil",
                "techn",
                "pourquoi",
                "role",
                "utilise",
                "c est quoi",
                "fonction",
                "dans le projet",
            )
        ):
            return out(TECH[tech], "Technologie")
    return None
