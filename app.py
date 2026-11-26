"""ConsultAI 360 — dossier d'analyse NexaRetail.

Lancer : python -m streamlit run app.py
Démo publique : CONSULTAI_DEMO_MODE=true ; PostgreSQL et Ollama restent optionnels.
"""

from __future__ import annotations

import html
import json
import os
from pathlib import Path

import streamlit as st

from project_knowledge import profile
from src.exploration import views as explore
from src.exploration.figures import flow
from src.assistant.console import (
    SCENARIOS,
    SCENARIO_NAMES,
    evidence,
    fmt,
    load_scenarios,
)
from src.assistant.copilot import PROMPTS, answer, local_model

st.set_page_config(
    page_title="ConsultAI 360",
    page_icon=":material/analytics:",
    layout="wide",
    initial_sidebar_state="auto",
)
st.markdown(
    "<style>" + (Path(__file__).parent / "assets/console.css").read_text() + "</style>",
    unsafe_allow_html=True,
)

PAGES = (
    "Synthèse",
    "Diagnostic opérationnel",
    "Simulations",
    "Traçabilité des données",
    "Assistant IA",
)


@st.cache_data(ttl=300, show_spinner=False)
def cached_metrics(demo: bool) -> dict:
    return load_scenarios(demo)


@st.cache_data(ttl=60, show_spinner=False)
def available_model() -> str | None:
    return local_model()


def esc(value) -> str:
    return html.escape(str(value))


with st.sidebar:
    st.markdown(
        '<div class="brand"><div class="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24"><path fill="currentColor" d="M12 2 22 12 12 22 2 12Z"/></svg></div><div><strong>ConsultAI 360</strong><small>Analyse des données</small></div></div>',
        unsafe_allow_html=True,
    )
    scenario = st.selectbox(
        "Scénario NexaRetail",
        SCENARIOS,
        index=1,
        format_func=SCENARIO_NAMES.get,
        key="data_scenario",
    )
    demo = st.toggle(
        "Mode démonstration",
        value=True,
        key="demo_mode",
        help="Référence figée en démonstration ; connexion PostgreSQL en lecture seule lorsque désactivé et configuré.",
    )
    configured = bool(os.getenv("ASSISTANT_DATABASE_URL", "").strip())
    source_status = st.empty()
    if st.session_state.get("navigation") not in PAGES:
        st.session_state["navigation"] = PAGES[0]
    with st.container(key="mission_nav"):
        st.markdown(
            '<div class="side-label">Dossier d’analyse</div>', unsafe_allow_html=True
        )
        page = st.radio(
            "Navigation", PAGES, key="navigation", label_visibility="collapsed"
        )
    author = profile()
    with st.container(key="mission_author"):
        st.markdown(
            f'<div class="side-label">À propos du projet</div><div class="side-author">{esc(author["name"])}</div>',
            unsafe_allow_html=True,
        )
        links = [
            f'<a href="{esc(author["github"])}" target="_blank" rel="noopener noreferrer">GitHub</a>'
        ]
        if author["linkedin"]:
            links.insert(
                0,
                f'<a href="{esc(author["linkedin"])}" target="_blank" rel="noopener noreferrer">LinkedIn</a>',
            )
        st.markdown(
            '<div class="author-links">' + "".join(links) + "</div>",
            unsafe_allow_html=True,
        )

using_reference = demo or not configured
try:
    with st.spinner("Chargement des indicateurs…"):
        all_metrics = cached_metrics(using_reference)
except Exception:
    if using_reference:
        st.error("Les données de démonstration ne peuvent pas être chargées.")
        st.stop()
    using_reference = True
    source_status.warning(
        "PostgreSQL est indisponible. La référence de démonstration prend le relais."
    )
    all_metrics = cached_metrics(True)

metrics = all_metrics[scenario]
if not demo and not configured:
    source_status.markdown(
        '<aside class="postgres-note" role="status">Pour faire tourner PostgreSQL 24 h/24, '
        "il me manque encore un petit détail… <strong>un stage ou un CDI !</strong>"
        "<small>En attendant, la démo utilise les données de référence.</small></aside>",
        unsafe_allow_html=True,
    )
elif not using_reference:
    source_status.caption(
        "PostgreSQL en lecture seule. Actualisation toutes les cinq minutes."
    )

if page != "Synthèse":
    st.title(page, anchor=False)

if page == "Synthèse":
    explore.home(scenario, all_metrics, author["name"])
elif page == "Diagnostic opérationnel":
    section = explore.pick(
        "Dossier à explorer",
        ["Anomalies", "Livraisons", "Mon rapport Power BI"],
        "diagnostic_view",
    )
    if section == "Anomalies":
        st.subheader("Quelles anomalies restent à traiter ?", anchor=False)
        explore.audit(scenario)
    elif section == "Livraisons":
        explore.logistics(scenario, metrics)
    else:
        st.subheader("Feuilleter le rapport NexaRetail", anchor=False)
        explore.dashboard(scenario)
elif page == "Simulations":
    explore.simulator(scenario, metrics, all_metrics)
elif page == "Traçabilité des données":
    pop = explore.pick(
        "Population à suivre", ["Commandes", "Livraisons"], "trace_population"
    )
    orders = pop == "Commandes"
    st.subheader("D’où vient ce chiffre ?", anchor=False)
    left, right = st.columns([1.6, 1], gap="medium")
    with left:
        explore.show(flow(metrics, orders), "lineage_flow")
    with right:
        if orders:
            explore.readout(
                f"{fmt(metrics['complete_pct'],1)} %",
                "Couverture des montants",
                f"{fmt(metrics['known'])} commandes renseignées sur {fmt(metrics['orders'])}.",
            )
        else:
            explore.readout(
                f"{fmt(metrics['late_pct'],2)} %",
                "Livraisons en retard",
                f"{fmt(metrics['late'])} retards sur {fmt(metrics['deliveries'])} livraisons dont les deux dates sont connues.",
            )
        origin = (
            "Référence figée de la démonstration"
            if using_reference
            else (
                "dw.fact_orders / overview()"
                if orders
                else "dw.fact_shipments / delivery()"
            )
        )
        st.markdown(f"**Source affichée :** {origin}.")
    with st.expander("Contrôles et limites des calculs"):
        st.markdown(
            "- Volumes entiers, populations non vides, anomalies comprises dans leur population.\n- Panier et CA non négatifs et finis ; aucune imputation automatique des montants absents.\n- En PostgreSQL : requêtes paramétrées, transaction en lecture seule et délai maximal de requête.\n- Les hypothèses ne sont pas incluses dans le CA renseigné."
        )
        if using_reference:
            st.info(
                "La référence conserve le panier moyen arrondi. Le CA affiché est donc reconstitué ; aucune requête PostgreSQL n’est exécutée en démonstration."
            )
        st.code(
            "Couverture = commandes avec montant / commandes × 100\nRetards = livraisons en retard / livraisons évaluables × 100",
            language="text",
        )
    st.download_button(
        "Exporter les valeurs et leur source",
        json.dumps(evidence(metrics, scenario), indent=2, ensure_ascii=False),
        file_name=f"consultai_sources_{scenario}.json",
        mime="application/json",
    )
    st.link_button(
        "Consulter le calcul des indicateurs",
        "https://github.com/NacPKZ/ConsultAI-360/blob/main/src/assistant/kpi.py",
    )

else:
    model = available_model()
    st.caption(
        f"Modèle local {model} disponible pour reconnaître les demandes. Chiffres calculés par les outils vérifiés."
        if model
        else "Réponses calculées à partir des données chargées. Aucun modèle de langage connecté sur ce serveur."
    )
    chats = st.session_state.setdefault("consult_chats", {})
    thread = chats.setdefault(
        f"{scenario}:{metrics['source']}", {"messages": [], "context": {}}
    )
    messages = thread["messages"]
    if messages:
        export, reset = st.columns([1, 1])
        with export:
            transcript = "\n\n".join(
                f"{'Question' if item['role'] == 'user' else 'Réponse / scénario ' + SCENARIO_NAMES[item['scenario']].lower()}\n\n{item['text']}"
                for item in messages
            )
            st.download_button(
                "Exporter l’échange",
                transcript,
                file_name=f"consultai_echange_{scenario}.md",
                mime="text/markdown",
            )
        with reset:
            if st.button("Nouvel échange", key="clear_chat"):
                thread.update(messages=[], context={})
                st.rerun()
    prompt = st.session_state.pop("audit_handoff", None)
    if not messages:
        for column, suggestion in zip(st.columns(3), PROMPTS):
            with column:
                if st.button(suggestion, key=f"quick_{suggestion}", width="stretch"):
                    prompt = suggestion
    pinned = st.session_state.get("mission_pins", {}).get(
        explore.note_key(scenario, metrics), {}
    )
    if pinned and not messages:
        with st.expander("Mes hypothèses de travail"):
            for note in pinned.values():
                st.markdown(note)
    for item in messages:
        with st.chat_message(
            item["role"],
            avatar=(
                ":material/person:"
                if item["role"] == "user"
                else ":material/analytics:"
            ),
        ):
            if item["role"] == "assistant" and item["scenario"] != scenario:
                st.caption(
                    f"Contexte de l’échange : scénario {SCENARIO_NAMES[item['scenario']].lower()}."
                )
            st.markdown(item["text"])
            if item["role"] == "assistant" and item.get("evidence"):
                with st.expander("Sources et calculs"):
                    st.caption(item["engine"])
                    for line in item["evidence"]:
                        st.markdown("- " + line)
    if messages and messages[-1]["role"] == "assistant":
        for i, (column, suggestion) in enumerate(
            zip(st.columns(2), messages[-1].get("followups", []))
        ):
            with column:
                if st.button(
                    suggestion, key=f"follow_{len(messages)}_{i}", width="stretch"
                ):
                    prompt = suggestion
    typed = st.chat_input("Votre question sur les données NexaRetail…", max_chars=1500)
    prompt = typed or prompt
    if prompt:
        with st.spinner("Analyse de la demande…"):
            response = answer(
                prompt, scenario, all_metrics, thread["context"], model=model
            )
        messages.extend(
            [{"role": "user", "text": prompt}, {"role": "assistant", **response}]
        )
        thread["messages"] = messages[-20:]
        thread["context"] = response["context"]
        st.rerun()
