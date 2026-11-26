"""Parcours interactif de la mission NexaRetail."""

import math
from html import escape

import streamlit as st

from src.assistant.console import (
    SCENARIOS,
    SCENARIO_NAMES,
    fmt,
    impact,
    mission_note,
    money,
)
from . import figures as fig
from .data import (
    FAMILIES,
    MEASURES,
    ROOT,
    STAGES,
    STAGE_NAMES,
    VIEWS,
    archive,
    distribution,
    recovery,
    stages,
)

REPO = "https://github.com/NacPKZ/ConsultAI-360/blob/main/"
BODY = {
    "CA déclaré": "Quand je présente le chiffre d’affaires, j’indique aussi combien de commandes ont un montant renseigné.",
    "Doublons": "J’ai conservé les copies en quarantaine. Je peux ainsi expliquer pourquoi le nombre de lignes baisse alors que le nombre de commandes distinctes reste stable.",
    "Panier utilisable": "Avant de commenter le panier moyen, je regarde quelles commandes entrent dans son calcul. Une moyenne stable peut cacher des montants manquants.",
}


def open_page(page):
    st.session_state["navigation"] = page


def ask_about(family, scenario):
    st.session_state["audit_handoff"] = (
        f"Après le nettoyage du scénario {SCENARIO_NAMES[scenario].lower()}, que reste-t-il pour les {FAMILIES[family].lower()} ?"
    )
    open_page("Assistant IA")


def pick(label, options, key):
    return st.radio(
        label, list(options), horizontal=True, key=key, label_visibility="collapsed"
    )


def show(figure, key):
    st.plotly_chart(
        figure,
        theme=None,
        key=key,
        config={
            "responsive": True,
            "displaylogo": False,
            "displayModeBar": "hover",
            "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
            "locale": "fr",
        },
    )


def readout(value, label, detail):
    st.markdown(
        f'<div class="readout"><span>{escape(label)}</span><strong>{escape(value)}</strong><p>{escape(detail)}</p></div>',
        unsafe_allow_html=True,
    )


def author_note(name, text):
    st.markdown(
        f'<aside class="fieldnote"><span>Note de {escape(name.split()[0]) if name.split() else "mission"}</span><p>{escape(text)}</p></aside>',
        unsafe_allow_html=True,
    )


def note_key(scenario, m):
    return f"{scenario}:{m['source']}"


def pin(text, scenario, m, kind):
    notes = st.session_state.setdefault("mission_pins", {}).setdefault(
        note_key(scenario, m), {}
    )
    current = notes.get(kind) == text
    if st.button(
        "Ajouté à la synthèse" if current else "Ajouter cette hypothèse à la synthèse",
        key=f"pin_{kind}",
        disabled=current,
    ):
        notes[kind] = text
        st.rerun()
    if current:
        st.button(
            "Ouvrir ma synthèse",
            key=f"open_{kind}",
            on_click=open_page,
            args=("Synthèse",),
        )


def receipt(scenario, measure):
    snapshots, _ = archive(scenario)
    with st.expander("Vérifier dans le fichier source"):
        stage = st.radio(
            "Version du fichier",
            STAGES,
            index=2,
            format_func=dict(zip(STAGES, STAGE_NAMES)).get,
            key="receipt_stage",
            horizontal=True,
        )
        row = snapshots[stage]
        if measure == "Doublons":
            calculation = (
                f"{fmt(row['orders_rows'])} lignes − {fmt(row['unique_orders'])} commandes distinctes"
                f" = **{fmt(row['duplicate_order_ids'])} doublons**."
            )
        elif measure == "Panier utilisable":
            calculation = (
                f"{fmt(row['nonnegative_order_total_sum'], 2)} € ÷ {fmt(row['orders_with_usable_amount'])} lignes exploitables"
                f" = **{fmt(row['usable_amount_average'], 2)} €** par panier."
            )
        else:
            calculation = (
                f"La somme des montants renseignés est de **{fmt(row['reported_order_total_sum'], 2)} €**. "
                f"Le fichier contient {fmt(row['orders_negative_amount'])} montants négatifs et {fmt(row['orders_missing_amount'])} montants absents."
            )
        st.markdown(calculation)
        st.markdown(
            f"[Ouvrir le rapport d’impact archivé]({REPO}reports/business_impact/{scenario}/business_impact_summary.json)"
        )


def home(scenario, allm, name):
    m = allm[scenario]
    # Chaque carreau représente un point de couverture, la valeur exacte reste lisible.
    tiles = round(m["complete_pct"])
    cells = "".join(
        f'<i class="{"filled" if i<tiles else "empty"}"></i>' for i in range(100)
    )
    first = escape(name)
    st.markdown(
        f'<section class="mission-cover"><div class="cover-copy"><div class="cover-over">NEXARETAIL <em>/</em> DOSSIER DE MISSION</div><h1>Peut-on publier ce<br>chiffre d’affaires&nbsp;?</h1><p>J’ai créé les commandes d’un distributeur fictif, puis j’y ai glissé des erreurs. À vous de voir lesquelles changent la décision.</p><div class="signature"><b>{first}</b><span>Conception et analyse</span></div></div><div class="coverage-sheet"><div class="sheet-label">COUVERTURE DES MONTANTS</div><div class="tile-field" aria-hidden="true">{cells}</div><div class="sheet-bottom"><b>{fmt(m["complete_pct"],1)} %</b><span>Scénario {escape(SCENARIO_NAMES[scenario].lower())}</span></div></div></section>',
        unsafe_allow_html=True,
    )
    with st.container(key="replay_panel"):
        st.subheader("Ce que le nettoyage change", anchor=False)
        measure = pick("Indicateur à explorer", MEASURES, "stage_measure")
        _, definition, unit = MEASURES[measure]
        values = stages(scenario, measure)
        chart_col, note_col = st.columns([1.65, 1], gap="medium")
        with chart_col:
            chart = (
                fig.duplicate_history(values)
                if measure == "Doublons"
                else fig.bridge(values, unit)
            )
            show(chart, "impact_bridge")
            st.caption(
                f"Rapport d’impact du scénario {SCENARIO_NAMES[scenario].lower()}. "
                + definition
            )
        with note_col:
            author_note(name, BODY[measure])
            receipt(scenario, measure)
    st.subheader("Comparer deux scénarios", anchor=False)
    chart_col, controls = st.columns(
        [1.85, 1], gap="medium", vertical_alignment="center"
    )
    with controls:
        others = [s for s in SCENARIOS if s != scenario]
        other = st.selectbox(
            "Comparer avec",
            others,
            format_func=SCENARIO_NAMES.get,
            key=f"compare_{scenario}",
        )
        ref = allm[other]
        delta = m["complete_pct"] - ref["complete_pct"]
        st.markdown(
            f"Le panier connu passe de **{fmt(m['basket'],2)} €** ({SCENARIO_NAMES[scenario].lower()}) à **{fmt(ref['basket'],2)} €** ({SCENARIO_NAMES[other].lower()}). L’écart de couverture est de **{fmt(abs(delta),1)} point{'s' if abs(delta)>1 else ''}**."
        )
    with chart_col:
        show(fig.benchmark(allm, (scenario, other)), "coverage_compare")
    has_notes = bool(
        st.session_state.get("mission_pins", {}).get(note_key(scenario, m))
    )
    with st.expander("Ma synthèse de mission", expanded=has_notes):
        st.markdown(
            f"**{fmt(m['missing'])} commandes** sans montant à rapprocher avec la source. Côté logistique, **{fmt(m['late'])} retards** sur **{fmt(m['deliveries'])} livraisons évaluables**."
        )
        notes = st.session_state.setdefault("mission_pins", {}).get(
            note_key(scenario, m), {}
        )
        if notes:
            for note in notes.values():
                st.markdown(note)
            if st.button("Retirer mes hypothèses", key="clear_pins"):
                notes.clear()
                st.rerun()
        else:
            st.caption(
                "Les hypothèses que vous retenez en cours d’analyse seront incluses dans l’export."
            )
        body = mission_note(m, scenario)
        if notes:
            body += "\n## Hypothèses retenues par le visiteur\n\n" + "\n\n".join(
                notes.values()
            )
        st.download_button(
            "Exporter la synthèse",
            body,
            file_name=f"consultai_synthese_{scenario}.md",
            mime="text/markdown",
        )


def audit(scenario):
    _, ev = archive(scenario)
    mode = pick(
        "État de l’audit", ["Avant nettoyage", "Après nettoyage"], "audit_stage"
    )
    after = mode == "Après nettoyage"
    by = ev["detection"]["by_type"]
    clean = ev["cleaning"]
    left, right = st.columns([1.65, 1], gap="medium")
    state = f"audit_family_{scenario}"
    plot = f"audit_plot_{scenario}_{int(after)}"
    selected = st.session_state.get(state, "broken_references")

    def select_bar():
        points = st.session_state[plot]["selection"]["points"]
        if points and points[-1].get("customdata") in by:
            st.session_state[state] = points[-1]["customdata"]

    with left:
        st.plotly_chart(
            fig.audit_plot(ev, selected, after),
            key=plot,
            on_select=select_bar,
            selection_mode="points",
            theme=None,
            config={"displayModeBar": False},
        )
        st.caption(
            "Cliquez sur une barre pour examiner la famille d’anomalies. Les alertes comptent des événements, pas des commandes uniques."
        )
    with right:
        family = st.selectbox(
            "Famille à examiner",
            ["broken_references", *(k for k in FAMILIES if k != "broken_references")],
            format_func=FAMILIES.get,
            key=state,
        )
        stats = by[family]
        count = (
            clean["remaining_alerts_by_type"].get(family, 0)
            if after
            else stats["detected_alerts"]
        )
        detail = (
            f"Avant nettoyage : {fmt(stats['detected_alerts'])}. Les positions des lignes changent après dédoublonnage ; on compare ici des volumes."
            if after
            else f"{fmt(stats['tp'])} alertes correspondent à une injection ; {fmt(stats['fp'])} ne figurent pas dans le journal d’injection."
        )
        readout(
            fmt(count),
            f"{FAMILIES[family]} / {'après' if after else 'avant'} nettoyage",
            detail,
        )
        if family == "broken_references":
            st.caption(
                "Une clé sans correspondance est signalée. Lui inventer une valeur rendrait la jointure trompeuse."
            )
        elif family == "negative_amounts":
            st.caption(
                "Un montant douteux peut être remplacé par NULL. Son montant d’origine n’est pas retrouvé pour autant."
            )
        st.button(
            "Examiner avec l’assistant", on_click=ask_about, args=(family, scenario)
        )
        st.link_button(
            "Ouvrir le rapport d’audit",
            REPO
            + f"reports/data_quality/evaluation/{scenario}/evaluation_summary.json",
        )
    st.caption(
        f"Rapport d’évaluation archivé du scénario {SCENARIO_NAMES[scenario].lower()}."
    )


def logistics(scenario, m):
    st.subheader("De combien faut-il réduire les retards ?", anchor=False)
    chart_col, controls = st.columns([1.4, 1], gap="medium")
    with controls:
        target = st.slider(
            "Taux de retard visé (%)",
            0.0,
            100.0,
            min(10.0, round(m["late_pct"], 1)),
            0.5,
            format="%.1f",
            key=f"delivery_goal_{scenario}",
        )
        allowed = math.floor(m["deliveries"] * target / 100)
        gap = max(0, m["late"] - allowed)
        detail = f"Au maximum {fmt(allowed)} retards sur {fmt(m['deliveries'])} livraisons évaluables."
        readout(
            fmt(gap), "Retards à éviter" if gap else "Objectif déjà atteint", detail
        )
    with chart_col:
        show(
            fig.delivery_target(m["deliveries"], m["late"], allowed), "delivery_target"
        )
        st.caption(
            f"{fmt(m['late'])} retards observés. Le curseur fixe le plafond admissible pour le même nombre de livraisons."
        )
    note = (
        f"**Objectif de livraison** — limiter les retards à {fmt(target,1)} % sur {fmt(m['deliveries'])} livraisons "
        f"évaluables demande d’éviter {fmt(gap)} retards par rapport aux {fmt(m['late'])} observés."
    )
    pin(note, scenario, m, "livraisons")


def dashboard(scenario):
    label = pick("Page Power BI", VIEWS, "bi_sheet")
    p = f"reports/powerbi/screenshots/{scenario}/{VIEWS[label]}.png"
    st.image(
        str(ROOT / p),
        caption=f"Mon rapport Power BI / {label} / scénario {SCENARIO_NAMES[scenario].lower()} — capture archivée.",
        width="stretch",
    )
    st.link_button("Ouvrir la capture originale", REPO + p)


def simulator(scenario, m, allm):
    mode = pick(
        "Simulation à construire",
        ["Panier inconnu", "Plan de rattrapage"],
        "simulation_mode",
    )
    if mode == "Panier inconnu":
        st.subheader("Que représentent les montants absents ?", anchor=False)
        left, right = st.columns([1, 1.8], gap="medium")
        with left:
            ratio = st.slider(
                "Panier supposé / panier connu",
                0.5,
                1.5,
                1.0,
                0.05,
                format="%.2f×",
                key=f"ratio_{scenario}",
            )
            h = impact(m, basket_ratio=ratio)
            readout(
                money(h["amount"]),
                "Montant à vérifier",
                f"{fmt(h['missing'])} commandes à {fmt(m['basket']*ratio,2)} € par panier supposé. Ce n’est pas une perte mesurée.",
            )
        with right:
            show(fig.sensitivity(allm, scenario, ratio), "sensitivity")
        note = f"**Hypothèse de panier :** {fmt(h['missing'])} montants absents × {fmt(m['basket']*ratio,2)} € (coefficient {fmt(ratio,2)}) représenteraient {money(h['amount'])}. Ce montant n’est pas un CA mesuré."
        pin(note, scenario, m, "panier")
        if st.toggle("Explorer l’incertitude du panier", key=f"show_spread_{scenario}"):
            sigma = st.slider(
                "Dispersion du panier supposé (σ logarithmique)",
                0.05,
                0.45,
                0.15,
                0.05,
                key=f"sigma_{scenario}",
            )
            figure, low, high = fig.spread(distribution(h["amount"], sigma))
            st.markdown(
                f"Dans cette simulation, **90 % des tirages** sont compris entre **{money(low)} et {money(high)}**."
            )
            show(figure, "spread")
            st.caption(
                "20 000 tirages reproductibles. Chaque tirage représente le panier moyen inconnu du groupe. La dispersion est une hypothèse, pas un intervalle de confiance observé."
            )
    else:
        st.subheader("Combien de jours pour fiabiliser les montants ?", anchor=False)
        left, right = st.columns([1, 1.8], gap="medium")
        with left:
            current = m["complete_pct"]
            target = (
                st.slider(
                    "Objectif de montants renseignés (%)",
                    float(current),
                    100.0,
                    max(float(current), 99.0),
                    0.1,
                    format="%.1f",
                    key=f"target_{scenario}",
                )
                if current < 100
                else 100.0
            )
            capacity = st.number_input(
                "Commandes vérifiables par jour",
                min_value=1,
                max_value=m["orders"],
                value=min(500, m["orders"]),
                step=1,
                key=f"capacity_{scenario}",
            )
            n, days = recovery(m, target, capacity)
            readout(
                f"{fmt(days)} jour{'s' if days!=1 else ''}",
                "Charge de vérification",
                f"{fmt(n)} montants à retrouver, à raison de {fmt(capacity)} commandes par jour.",
            )
        with right:
            show(fig.trajectory(m, n, days, capacity, target), "recovery")
        note = f"**Hypothèse de rattrapage :** passer de {fmt(current,1)} % à {fmt(target,1)} % demande de documenter {fmt(n)} montants. À {fmt(capacity)} par jour : {fmt(days)} jours de traitement, si chaque montant est retrouvé."
        pin(note, scenario, m, "rattrapage")
        st.caption(
            "Cette durée suppose une preuve source pour chaque montant traité. Aucune donnée n’est modifiée."
        )
