"""ConsultAI 360 · console analytique NexaRetail."""
from __future__ import annotations

import html
import json
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.assistant.console import (
    DEFAULT_TH, SCENARIOS, SCENARIO_NAME, VERDICT, conversational_answer,
    eur_m, evidence_payload, fmt, load_metrics, local_models, memo_markdown,
    monte_carlo, ollama_answer, recommendations,
)
from src.assistant.decision_rules import gate, safe_th
from src.assistant.health_score import health

st.set_page_config(page_title="ConsultAI 360", layout="wide", initial_sidebar_state="collapsed")
st.html("""
<style>
.block-container{max-width:1240px;padding-top:4.75rem;padding-bottom:3rem}
.console-brand{font-size:.82rem;font-weight:750;letter-spacing:.09em;color:#475b71}
.console-metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:.67rem;margin:0}
.console-metrics div{padding:12px 14px;border-radius:8px;background:#f1f5f8;border-top:2px solid #90a9bc}
.console-metrics dt{color:#40546a;font-size:.8rem}
.console-metrics dd{margin:.32rem 0 0;font-size:clamp(1rem,2.3vw,1.65rem);font-weight:720;font-variant-numeric:tabular-nums;color:#172c43}
@media(max-width:470px){.console-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}}
[data-testid="stMetricValue"]{font-variant-numeric:tabular-nums;font-size:clamp(1.05rem,2.2vw,1.85rem)}
@media(max-width:640px){.block-container{padding-top:4.3rem}}
</style>
""")

ORIGINAL_CA = 72_056_406.60
PAGES = ("Vue d’ensemble", "Analyse des données", "Comparaison", "Recommandations", "Assistant")
SOURCE = "https://github.com/NacPKZ/ConsultAI-360/blob/main/docs/"
MAX_HISTORY = 30


def column_chart(labels, values, title, unit, note):
    figure = go.Figure(go.Bar(x=labels, y=values, marker_color="#275479",
                              texttemplate="%{y:.2f}", textposition="auto",
                              hovertemplate="%{x}<br>%{y:.2f} " + unit + "<extra></extra>"))
    figure.update_layout(height=305, margin=dict(t=45, l=12, r=12, b=20),
                         title=dict(text=title, font=dict(size=16)), yaxis_title=unit,
                         yaxis_rangemode="tozero")
    st.plotly_chart(figure, width="stretch", config={"displayModeBar": False})
    st.caption(note)


def metric_grid(entries):
    cells = "".join(
        f"<div><dt>{html.escape(label)}</dt><dd>{html.escape(value)}</dd></div>"
        for label, value in entries
    )
    st.html(f'<dl class="console-metrics">{cells}</dl>')


st.session_state.setdefault("console_page", PAGES[0])
st.session_state.setdefault("console_scenario", "medium")
with st.sidebar:
    st.header("NexaRetail")
    st.caption("Entreprise fictive de distribution omnicanale")
    use_db = bool(os.getenv("ASSISTANT_DATABASE_URL")) and st.toggle("PostgreSQL en lecture seule")
    st.link_button("Code et documentation", "https://github.com/NacPKZ/ConsultAI-360")
    st.link_button("Portfolio de Can Pekgoz", "https://nacpkz-portfolio.vercel.app/")

try:
    all_metrics = load_metrics(not use_db)
except Exception:
    st.warning("PostgreSQL est indisponible. La console utilise les données de référence.")
    use_db = False
    all_metrics = load_metrics(True)

st.html('<div class="console-brand">CONSULTAI 360 / NEXARETAIL</div>')
page = st.radio("Navigation principale", PAGES, horizontal=True, key="console_page", label_visibility="collapsed")
control, marker = st.columns([1, 3])
with control:
    scenario = st.selectbox("Scénario de données", SCENARIOS, format_func=SCENARIO_NAME.get, key="console_scenario")
with marker:
    st.caption("PostgreSQL en lecture seule" if use_db else "Données synthétiques de référence")
data = all_metrics[scenario]
thresholds = safe_th(st.session_state.get("thresholds", DEFAULT_TH))
decision = gate(data, thresholds)
actions = recommendations(data, thresholds)
GUIDE = (
    (PAGES[0], "Repérez le nombre de commandes sans montant dans le scénario moyen."),
    (PAGES[2], "Comparez Moyen et Critique. L’écart au scénario Original décrit la mesure du CA."),
    (PAGES[3], "Vérifiez quelle condition déclenche la réserve ou le blocage de publication."),
    (PAGES[4], "Demandez : « Est-ce une perte réelle ? »"),
)

def guide_step(step):
    st.session_state.guide_step = step
    st.session_state.console_page = GUIDE[step][0]

if "guide_step" in st.session_state:
    step = st.session_state.guide_step
    st.info(f"Étape {step + 1}/{len(GUIDE)} · {GUIDE[step][1]}")
    first, second = st.columns(2)
    if step + 1 < len(GUIDE):
        first.button("Étape suivante", on_click=guide_step, args=(step + 1,))
    second.button("Quitter la démo", on_click=lambda: st.session_state.pop("guide_step", None))

if page == PAGES[0]:
    st.title("Vue d’ensemble")
    st.write("NexaRetail est un distributeur omnicanal fictif. Cette mission examine la fiabilité de ses indicateurs commerciaux et logistiques.")
    metric_grid([
        ("Commandes", fmt(data["orders"])), ("CA documenté", f"{fmt(data['known_rev']/1e6,2)} M€"),
        ("Complétude", f"{fmt(data['complete_pct'], 1)} %"),
        ("Panier connu", f"{fmt(data['basket'], 2)} €"), ("Taux de retard", f"{fmt(data['late_pct'], 2)} %"),
    ])
    a, b = st.columns([1.6, 1])
    with a:
        column_chart([SCENARIO_NAME[s] for s in SCENARIOS], [all_metrics[s]["missing_pct"] for s in SCENARIOS],
                     "Commandes sans montant par scénario", "%", "Dénominateur : commandes du scénario.")
    with b:
        st.subheader("Le point à traiter")
        st.write(f"**{fmt(data['missing'])} commandes** n’ont pas de montant. Le CA affiché couvre les commandes dont le montant est connu.")
        st.write(f"**Priorité :** {actions[0]['t']}.")
        st.button("Analyser les données", on_click=lambda: st.session_state.update(console_page=PAGES[1]))
        st.button("Interroger l’assistant", on_click=lambda: st.session_state.update(console_page=PAGES[4]))
    with st.expander("Démo guidée · 3 minutes"):
        st.markdown("1. Repérez les montants manquants.\n2. Comparez le scénario moyen au critique.\n3. Consultez la décision de publication.\n4. Demandez à l’assistant d’expliquer le CA exposé.")
        st.button("Commencer la démo", on_click=guide_step, args=(0,))

elif page == PAGES[1]:
    st.title("Analyse des données")
    tab1, tab2, tab3 = st.tabs(("Commerce", "Qualité", "Logistique"))
    with tab1:
        metric_grid([("CA documenté", f"{fmt(data['known_rev'],2)} €"), ("Panier moyen connu", f"{fmt(data['basket'],2)} €")])
        st.write(f"Le panier moyen porte sur **{fmt(data['known'])} commandes** avec montant.")
        st.write("Les agrégats disponibles ne permettent pas d’isoler des effets par magasin, canal ou catégorie.")
    with tab2:
        st.dataframe(pd.DataFrame({"État du montant": ["Connu", "Absent"], "Commandes": [data["known"], data["missing"]]}), hide_index=True)
        st.write(f"La complétude est de **{fmt(data['complete_pct'],2)} %**. Examiner l’origine des valeurs absentes avant d’imputer un montant.")
    with tab3:
        metric_grid([("Livraisons évaluables", fmt(data["deliveries"])), ("Retards", fmt(data["late"])), ("Taux", f"{fmt(data['late_pct'],2)} %")])
        if len({m["late_pct"] for m in all_metrics.values()}) == 1:
            st.write("Le taux de retard est identique dans les scénarios visibles. Ces données ne permettent pas de relier les retards à l’absence de montants.")
    payload = evidence_payload(data, scenario, not use_db, thresholds)
    st.download_button("Exporter les données du scénario", json.dumps(payload, ensure_ascii=False, indent=2), "nexaretail-indicateurs.json", "application/json")

elif page == PAGES[2]:
    st.title("Comparaison des scénarios")
    st.write("Les scénarios font varier la dégradation des montants. Le scénario Original sert de référence au rapprochement Power BI.")
    rows = [{"Scénario": SCENARIO_NAME[s], "Commandes": m["orders"], "Montants absents": m["missing"], "CA documenté (€)": round(m["known_rev"],2),
             "Complétude (%)": round(m["complete_pct"],2), "Retards (%)": round(m["late_pct"],2)} for s, m in all_metrics.items()]
    if not use_db:
        rows.insert(0, {"Scénario": "Original", "Commandes": 120_000, "Montants absents": None,
                        "CA documenté (€)": ORIGINAL_CA, "Complétude (%)": None, "Retards (%)": None})
        for row in rows:
            row["Écart de mesure (€)"] = round(row["CA documenté (€)"] - ORIGINAL_CA, 2)
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    column_chart([r["Scénario"] for r in rows], [r["CA documenté (€)"]/1e6 for r in rows],
                 "Chiffre d’affaires documenté", "M€", "Les montants non renseignés sont exclus du total.")
    if not use_db:
        selected_delta = data["known_rev"] - ORIGINAL_CA
        st.caption(f"Écart du scénario actif par rapport à Original : {fmt(selected_delta, 2)} €. C’est un écart de mesure.")
    with st.expander("Tester une hypothèse de montants manquants"):
        missing = st.slider("Part de commandes sans montant (%)", 0.0, 30.0, float(min(data["missing_pct"], 30)), step=.5)
        ratio = st.slider("Panier inconnu / panier connu", .5, 1.5, 1.0, step=.05)
        st.metric("CA non vérifiable sous cette hypothèse", eur_m(data["orders"]*missing/100*data["basket"]*ratio))
        st.caption("Estimation conditionnelle. Elle ne représente pas une perte de chiffre d’affaires mesurée.")
        if st.checkbox("Afficher les tirages de sensibilité"):
            spread = st.slider("Dispersion log-normale (σ)", .05, .60, .15, step=.05)
            simulated = dict(data, missing=round(data["orders"]*missing/100), basket=data["basket"]*ratio)
            p5, p95 = np.percentile(monte_carlo(simulated, spread), (5,95))
            st.write(f"Sur 20 000 tirages, P5–P95 : **{fmt(p5,2)} à {fmt(p95,2)} M€**.")
            st.caption("Distribution d’hypothèses sur le panier inconnu. Ces percentiles ne sont pas un intervalle de confiance.")

elif page == PAGES[3]:
    st.title("Recommandations")
    st.write(f"**Décision selon les seuils pédagogiques : {VERDICT[decision['overall']][0]}.**")
    for rec in actions:
        st.markdown(f"**{rec['t']}**")
        st.write(rec["why"])
    with st.expander("Seuils de décision"):
        st.caption("Seuils de démonstration, modifiables pour tester une politique de publication.")
        cap = st.number_input("Blocage si montants absents au-delà de (%)", min_value=1., max_value=100., value=float(thresholds["m_fail"]))
        warning = st.number_input("Réserve si montants absents au-delà de (%)", min_value=0., max_value=100., value=float(thresholds["m_warn"]))
        if st.button("Appliquer les seuils"):
            if warning >= cap:
                st.error("Le seuil de réserve doit être inférieur au seuil de blocage.")
            else:
                st.session_state.thresholds = dict(thresholds, m_fail=cap, m_warn=warning)
                st.rerun()
    memo = memo_markdown(data, scenario, decision, health(data), actions)
    st.download_button("Télécharger la note de décision", memo, f"note-{scenario}.md", "text/markdown")

else:
    st.title("Assistant NexaRetail")
    models, model_note = local_models()
    model_mode = bool(models) and st.toggle("Reformulation par le modèle local", help="Les calculs et scénarios restent déterministes.")
    st.caption(model_note)
    if "console_history" not in st.session_state:
        st.session_state.console_history = []
        st.session_state.console_context = {}
    history = st.session_state.console_history
    if st.button("Nouvelle conversation"):
        history.clear()
        st.session_state.console_context.clear()
        st.rerun()
    prompt = None
    if not history:
        for col, example in zip(st.columns(3), ("Combien de commandes sont sans montant ?", "Compare les scénarios", "Est-ce une perte réelle ?")):
            if col.button(example, width="stretch"):
                prompt = example
    for entry in history:
        with st.chat_message(entry["role"]):
            st.markdown(entry["content"])
            if entry.get("evidence"):
                with st.expander("Vérifications"):
                    st.markdown("\n".join(f"- {item}" for item in entry["evidence"]))
    typed = st.chat_input("Posez votre question sur NexaRetail", max_chars=1200)
    prompt = typed or prompt
    if prompt and prompt.strip():
        with st.spinner("Analyse de la question…"):
            context = st.session_state.console_context
            result = conversational_answer(prompt, scenario, all_metrics, thresholds, context, history, "Conversation")
            if model_mode and result["intent"] in {"method", "glossary", "actions"}:
                try:
                    result = ollama_answer(prompt, all_metrics, history, result)
                except (OSError, ValueError, KeyError):
                    result["evidence"].append("Modèle local indisponible. Réponse du moteur analytique.")
        history.extend([{"role":"user", "content":prompt}, {"role":"assistant", "content":result["text"], "scenario":result["scenario"], "evidence":result["evidence"]}])
        del history[:-MAX_HISTORY]
        st.rerun()
    if history:
        with st.expander("Copier la dernière réponse"):
            st.code(history[-1]["content"], language=None, wrap_lines=True)
        st.download_button("Télécharger le dernier échange", history[-1]["content"], "reponse-nexaretail.md", "text/markdown")

with st.expander("Méthode et sources"):
    st.markdown(
        "Le chiffre d’affaires documenté est la somme des montants connus. "
        "La complétude rapporte les commandes avec montant au total des commandes. "
        "Le taux de retard porte sur les livraisons évaluables. Les montants absents ne sont pas imputés."
    )
    st.markdown(f"[Dictionnaire des KPI]({SOURCE}04_dictionnaire_indicateurs.md) · [Rapport de conseil]({SOURCE}12_rapport_final_conseil.md)")
