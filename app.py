"""ConsultAI 360 — dossier d'analyse NexaRetail.

Lancer : python -m streamlit run app.py
Démo publique : CONSULTAI_DEMO_MODE=true ; PostgreSQL et Ollama restent optionnels.
"""

from __future__ import annotations

import html
import json
import os
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from project_knowledge import profile
from src.assistant.console import (
    SCENARIOS,
    SCENARIO_NAMES,
    evidence,
    fmt,
    impact,
    load_scenarios,
    mission_note,
    money,
    priorities,
)
from src.assistant.copilot import PROMPTS, answer, local_model

st.set_page_config(
    page_title="ConsultAI 360",
    page_icon=":material/analytics:",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(
    "<style>" + (Path(__file__).parent / "assets/console.css").read_text() + "</style>",
    unsafe_allow_html=True,
)

PAGES = (
    "Synthèse",
    "Diagnostic opérationnel",
    "Traçabilité des données",
    "Assistant IA",
)
NAVY, GOLD, GREEN, RED = "#142b46", "#c49a3a", "#28765e", "#a33e47"
COLORS = {"low": GREEN, "medium": GOLD, "critical": RED}


@st.cache_data(ttl=300, show_spinner=False)
def cached_metrics(demo: bool) -> dict:
    return load_scenarios(demo)


@st.cache_data(ttl=60, show_spinner=False)
def available_model() -> str | None:
    return local_model()


def esc(value) -> str:
    return html.escape(str(value))


def chart(fig: go.Figure, height: int = 310) -> None:
    fig.update_layout(
        height=height,
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font={"family": "Arial, sans-serif", "color": NAVY, "size": 12},
        margin={"l": 18, "r": 26, "t": 30, "b": 25},
        hoverlabel={"bgcolor": NAVY, "font_color": "white"},
        showlegend=False,
        separators=", ",
        transition={"duration": 250},
    )
    fig.update_xaxes(gridcolor="#edf0f4", zeroline=False, fixedrange=True)
    fig.update_yaxes(gridcolor="#edf0f4", zeroline=False, fixedrange=True)
    st.plotly_chart(
        fig, config={"displayModeBar": False, "responsive": True}, width="stretch"
    )


def heading(title: str) -> None:
    st.markdown(
        f'<div class="page-top"><span class="eyebrow">NexaRetail / scénario {esc(SCENARIO_NAMES[scenario].lower())}</span><span class="source-pill">{esc(source_label)}</span></div>',
        unsafe_allow_html=True,
    )
    st.title(title, anchor=False)


def metric_grid(items: list[tuple]) -> None:
    st.markdown(
        '<div class="metric-grid">'
        + "".join(
            f'<article class="metric" style="--metric-color:{color}"><span class="metric-label">{esc(label)}</span><strong>{esc(value)}</strong><small>{esc(detail)}</small></article>'
            for label, value, detail, color in items
        )
        + "</div>",
        unsafe_allow_html=True,
    )


def action_list(metrics: dict) -> None:
    st.markdown(
        '<div class="action-list">'
        + "".join(
            f'<article class="action"><span class="action-index">{i:02d}</span><div><strong>{esc(a["title"])}</strong><p>{esc(a["detail"])}</p><small>À mobiliser : {esc(a["owner"])}</small></div></article>'
            for i, a in enumerate(priorities(metrics), 1)
        )
        + "</div>",
        unsafe_allow_html=True,
    )


def insight(text: str) -> None:
    st.markdown(f'<div class="insight">{text}</div>', unsafe_allow_html=True)


with st.sidebar:
    st.markdown(
        '<div class="brand"><div class="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24"><path fill="currentColor" d="M12 2 22 12 12 22 2 12Z"/></svg></div><div><strong>ConsultAI 360</strong><small>Analyse des données</small></div></div><div class="side-project">NexaRetail, cas d’étude</div>',
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown(
        '<div class="side-label">Données à analyser</div>', unsafe_allow_html=True
    )
    scenario = st.selectbox(
        "Scénario de données",
        SCENARIOS,
        index=1,
        format_func=lambda s: f"Scénario {SCENARIO_NAMES[s].lower()}",
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
    st.divider()
    st.markdown(
        '<div class="side-label">Dossier d’analyse</div>', unsafe_allow_html=True
    )
    if st.session_state.get("navigation") not in PAGES:
        st.session_state["navigation"] = PAGES[0]
    page = st.radio("Navigation", PAGES, key="navigation", label_visibility="collapsed")
    st.divider()
    st.markdown(
        '<div class="side-label">À propos du projet</div>', unsafe_allow_html=True
    )
    author = profile()
    st.markdown(
        f'<div class="side-author">{esc(author["name"])}</div>', unsafe_allow_html=True
    )
    if author["linkedin"]:
        st.link_button("Profil LinkedIn", author["linkedin"], width="stretch")
    st.link_button("Code source GitHub", author["github"], width="stretch")

using_reference = demo or not configured
if not demo and not configured:
    st.info(
        "PostgreSQL n’est pas configuré sur ce serveur. La référence de démonstration reste affichée."
    )
try:
    with st.spinner("Chargement des indicateurs…"):
        all_metrics = cached_metrics(using_reference)
except Exception:
    if using_reference:
        st.error("Les données de démonstration ne peuvent pas être chargées.")
        st.stop()
    using_reference = True
    st.warning(
        "PostgreSQL est indisponible. Les valeurs affichées proviennent de la référence de démonstration."
    )
    all_metrics = cached_metrics(True)

metrics = all_metrics[scenario]
source_label = (
    "Référence figée / démonstration"
    if using_reference
    else "PostgreSQL / cache de 5 min"
)
source_status.caption(
    "Données synthétiques de référence"
    if demo
    else (
        "Référence affichée / PostgreSQL indisponible"
        if using_reference
        else "PostgreSQL en lecture seule"
    )
)


if page == "Synthèse":
    heading("Synthèse")
    metric_grid(
        [
            (
                "Commandes",
                fmt(metrics["orders"]),
                "Avec ou sans montant renseigné",
                NAVY,
            ),
            (
                "Montants renseignés",
                f'{fmt(metrics["complete_pct"], 1)} %',
                f'{fmt(metrics["missing"])} commandes sans montant',
                GOLD,
            ),
            (
                "Panier moyen connu",
                f'{fmt(metrics["basket"], 2)} €',
                f'Sur {fmt(metrics["known"])} commandes',
                GREEN,
            ),
            (
                "Livraisons en retard",
                f'{fmt(metrics["late_pct"], 2)} %',
                f'{fmt(metrics["late"])} sur {fmt(metrics["deliveries"])} évaluables',
                RED,
            ),
        ]
    )
    left, right = st.columns([1.08, 1], gap="large")
    with left:
        st.subheader("Ce que le scénario change", anchor=False)
        figure = go.Figure(
            go.Bar(
                x=[SCENARIO_NAMES[s] for s in SCENARIOS],
                y=[all_metrics[s]["missing_pct"] for s in SCENARIOS],
                marker_color=[
                    COLORS[s] if s == scenario else "#dbe3ec" for s in SCENARIOS
                ],
                text=[f'{fmt(all_metrics[s]["missing_pct"], 1)} %' for s in SCENARIOS],
                textposition="outside",
                customdata=[[all_metrics[s]["missing"]] for s in SCENARIOS],
                hovertemplate="%{x}<br>%{customdata[0]:,} commandes sans montant<br>%{y:.1f} %<extra></extra>",
                width=0.48,
            )
        )
        figure.update_yaxes(
            title_text="Commandes sans montant (%)",
            range=[0, max(m["missing_pct"] for m in all_metrics.values()) * 1.3 or 1],
        )
        chart(figure, 300)
        if len({round(m["late_pct"], 8) for m in all_metrics.values()}) == 1:
            st.caption(
                "Les trois scénarios font varier les montants absents. Le taux de retard reste identique."
            )
    with right:
        st.subheader("Actions à engager", anchor=False)
        action_list(metrics)
    st.download_button(
        "Exporter la synthèse",
        mission_note(metrics, scenario),
        file_name=f"consultai_synthese_{scenario}.md",
        mime="text/markdown",
    )

elif page == "Diagnostic opérationnel":
    heading("Diagnostic opérationnel")
    amounts, deliveries = st.tabs(["Qualité des montants", "Livraisons"])
    with amounts:
        left, right = st.columns([1.2, 1], gap="large")
        with left:
            st.subheader("CA renseigné et montants à vérifier", anchor=False)
            known_label = (
                "CA reconstitué (approx.)" if using_reference else "CA renseigné"
            )
            figure = go.Figure(
                go.Bar(
                    y=[known_label, "Montant inconnu (hypothèse)"],
                    x=[metrics["known_rev"] / 1e6, metrics["exposure"] / 1e6],
                    orientation="h",
                    marker_color=[NAVY, GOLD],
                    marker_pattern_shape=["", "/"],
                    text=[money(metrics["known_rev"]), money(metrics["exposure"])],
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate="%{y}<br>%{x:.2f} M€<extra></extra>",
                )
            )
            figure.update_xaxes(
                title_text="Montant (M€)",
                range=[
                    0,
                    max(metrics["known_rev"], metrics["exposure"]) / 1e6 * 1.3 or 1,
                ],
            )
            figure.update_yaxes(autorange="reversed", automargin=True)
            chart(figure, 290)
            st.caption(
                "La barre hachurée suppose un panier identique pour les commandes sans montant. Elle ne représente pas une perte mesurée."
            )
        with right:
            st.subheader("Ce qui limite le reporting", anchor=False)
            insight(
                f'<strong>{fmt(metrics["missing"])} montants à rapprocher.</strong> Le CA porte sur {fmt(metrics["complete_pct"], 1)} % des commandes. Il faut conserver cette couverture dans les restitutions.'
            )
            st.markdown(
                "Comparer les commandes avec et sans montant par **magasin, canal et période**, puis contrôler la collecte et les jointures."
            )
            if using_reference:
                st.caption(
                    "En démonstration, le CA est une approximation : commandes renseignées × panier arrondi."
                )
        with st.expander("Tester une hypothèse de panier"):
            st.caption(
                "Pour les seules commandes sans montant, faites varier le panier supposé par rapport au panier connu."
            )
            ratio = st.slider(
                "Panier supposé / panier connu",
                0.5,
                1.5,
                1.0,
                0.05,
                key=f"basket_ratio_{scenario}",
            )
            hypothesis = impact(metrics, basket_ratio=ratio)
            st.markdown(
                f"À **{fmt(ratio, 2)} fois** le panier connu, les **{fmt(hypothesis['missing'])} commandes sans montant** représenteraient **{money(hypothesis['amount'])}**. Leur montant réel reste à vérifier."
            )
    with deliveries:
        left, right = st.columns([1.2, 1], gap="large")
        with left:
            st.subheader("Ponctualité des livraisons évaluables", anchor=False)
            values = [metrics["deliveries"] - metrics["late"], metrics["late"]]
            figure = go.Figure(
                go.Bar(
                    x=["À l’heure", "En retard"],
                    y=values,
                    marker_color=[GREEN, RED],
                    text=[fmt(v) for v in values],
                    textposition="outside",
                    hovertemplate="%{x}<br>%{y:,} livraisons<extra></extra>",
                    width=0.48,
                )
            )
            figure.update_yaxes(
                title_text="Livraisons", range=[0, max(values) * 1.2 or 1]
            )
            chart(figure, 300)
            st.caption(
                "Seules les livraisons avec une date prévue et une date réelle sont évaluables."
            )
        with right:
            st.subheader("La prochaine vérification", anchor=False)
            insight(
                f'<strong>{fmt(metrics["late_pct"], 2)} % de retards.</strong> Ventiler les {fmt(metrics["late"])} cas par transporteur et zone avant de rechercher une cause.'
            )
            st.markdown(
                "**Contrôle**\n\nVérifier les dates, comparer les taux entre segments, puis examiner les cas atypiques."
            )
            st.caption(
                "Ces agrégats ne permettent pas de nommer un transporteur ou un magasin responsable."
            )

elif page == "Traçabilité des données":
    heading("Traçabilité des données")
    nodes = (
        [
            (
                "01",
                "Référence figée",
                "Volumes et paniers de démonstration conservés dans le code.",
            ),
            (
                "02",
                "Validation Python",
                "Contrôle des populations, calcul des taux et de la couverture.",
            ),
            (
                "03",
                "Restitution",
                "Indicateurs affichés et hypothèses identifiées séparément.",
            ),
        ]
        if using_reference
        else [
            ("01", "PostgreSQL", "Tables dw.fact_orders et dw.fact_shipments."),
            (
                "02",
                "Agrégats SQL / Python",
                "Requêtes autorisées en lecture seule, validation des résultats.",
            ),
            (
                "03",
                "Restitution",
                "Cache de cinq minutes, indicateurs et export des valeurs.",
            ),
        ]
    )
    st.markdown(
        '<div class="trace-path">'
        + "".join(
            f'<div class="trace-node"><span>{i}</span><strong>{esc(title)}</strong><small>{esc(detail)}</small></div>'
            for i, title, detail in nodes
        )
        + "</div>",
        unsafe_allow_html=True,
    )
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown(
            f'<div class="source-block"><strong>Commandes et montants</strong><p>{fmt(metrics["orders"])} commandes, dont {fmt(metrics["known"])} avec montant.<br>Couverture : {fmt(metrics["known"])} / {fmt(metrics["orders"])}.</p><p>En mode PostgreSQL : <code>dw.fact_orders</code>, fonction <code>overview()</code>.</p></div>',
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            f'<div class="source-block"><strong>Livraisons</strong><p>{fmt(metrics["deliveries"])} livraisons évaluables, dont {fmt(metrics["late"])} en retard.<br>Taux : {fmt(metrics["late"])} / {fmt(metrics["deliveries"])}.</p><p>En mode PostgreSQL : <code>dw.fact_shipments</code>, fonction <code>delivery()</code>.</p></div>',
            unsafe_allow_html=True,
        )
    st.caption(
        "Commandes et livraisons sont deux populations distinctes. NexaRetail est un cas d’étude sur des données synthétiques."
    )
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
    heading("Assistant IA")
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
                f"{'Question' if item['role'] == 'user' else 'Réponse'}\n\n{item['text']}"
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
    prompt = None
    if not messages:
        st.markdown(
            "Une question sur la qualité des montants, les livraisons ou les priorités ?"
        )
        for column, suggestion in zip(st.columns(3), PROMPTS):
            with column:
                if st.button(suggestion, key=f"quick_{suggestion}", width="stretch"):
                    prompt = suggestion
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
                    f"Réponse sur le scénario {SCENARIO_NAMES[item['scenario']].lower()}, demandé dans la question."
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
