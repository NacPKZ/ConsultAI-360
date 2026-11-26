"""Vues Plotly de la mission, indépendantes de Streamlit."""

import plotly.graph_objects as go
import numpy as np
from src.assistant.console import SCENARIOS, SCENARIO_NAMES, fmt
from .data import FAMILIES

INK, GOLD, TEAL, CORAL, MIST = "#193954", "#B38129", "#197E76", "#BD6656", "#9DAFBE"
PALETTE = {"low": TEAL, "medium": GOLD, "critical": CORAL}


def layout(fig, height=305):
    fig.update_layout(
        template="plotly_white",
        height=height,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Inter, Arial, sans-serif", color=INK, size=13),
        margin=dict(l=18, r=18, t=34, b=18),
        separators=", ",
        hoverlabel=dict(bgcolor=INK, font_color="white"),
        transition_duration=200,
    )
    fig.update_xaxes(automargin=True, zeroline=False, showgrid=False)
    fig.update_yaxes(automargin=True, zeroline=False, gridcolor="#E7EEF1", nticks=5)
    return fig


def duplicate_history(values):
    labels = ["Référence", "Injection", "Nettoyage"]
    peak = max(max(values), 1)
    figure = go.Figure(
        go.Scatter(
            x=[0, 1, 2],
            y=values,
            mode="lines+markers+text",
            line=dict(color=MIST, width=3),
            marker=dict(
                size=13, color=[INK, CORAL, TEAL], line=dict(color="white", width=2)
            ),
            text=[fmt(value) for value in values],
            textposition="top center",
            textfont=dict(size=14, color=INK),
            customdata=labels,
            hovertemplate="%{customdata}<br>%{text} identifiants dupliqués<extra></extra>",
        )
    )
    layout(figure, 285)
    figure.update_xaxes(
        tickvals=[0, 1, 2], ticktext=labels, range=[-0.24, 2.24], fixedrange=True
    )
    figure.update_yaxes(
        range=[-0.10 * peak, 1.32 * peak],
        rangemode="normal",
        title_text="Identifiants dupliqués",
        tickformat=",.0f",
        fixedrange=True,
    )
    return figure


def delivery_target(deliveries, late, allowed):
    """Volumes observé et admissible, avec une échelle et un dénominateur communs."""
    rates = [100 * late / deliveries, 100 * allowed / deliveries]
    figure = go.Figure(
        go.Bar(
            x=rates,
            y=["Observé", "Objectif"],
            orientation="h",
            width=0.38,
            marker_color=[INK, TEAL],
            customdata=[late, allowed],
            text=[fmt(rate, 2) + " %" for rate in rates],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y} · %{customdata:,} livraisons<extra></extra>",
        )
    )
    layout(figure, 225)
    figure.update_layout(margin=dict(l=16, r=64, t=20, b=20))
    figure.update_yaxes(autorange="reversed", showgrid=False)
    figure.update_xaxes(
        range=[0, min(100, max(20, max(rates) * 1.12))],
        ticksuffix=" %",
        nticks=5,
        showgrid=True,
        gridcolor="#edf1f1",
    )
    return figure


def bridge(values, unit):
    # La cascade historique portait sur l'exposition. Ici les marches sont les
    # écarts mesurés entre trois états réellement exportés.
    scale = 1e6 if unit == "M€" else 1
    a, b, c = [v / scale for v in values]
    diffs = [a, b - a, c - b, 0]

    def label(v):
        return fmt(v, 0 if unit == "commandes" else 2) + (
            " " + unit if unit != "commandes" else ""
        )

    labels = [
        label(a),
        ("+" if b >= a else "") + label(b - a),
        ("+" if c >= b else "") + label(c - b),
        label(c),
    ]
    lower = max(
        0, min(a, b, c) - max(max(a, b, c) - min(a, b, c), max(a, b, c) * 0.018) * 0.43
    )
    upper = (
        max(a, b, c)
        + max(max(a, b, c) - min(a, b, c), max(a, b, c) * 0.018, 1e-4) * 0.45
    )
    fig = go.Figure(
        go.Waterfall(
            x=["Référence", "Injection", "Nettoyage", "Résultat"],
            y=diffs,
            measure=["absolute", "relative", "relative", "total"],
            text=labels,
            textposition="none",
            connector_line=dict(color=MIST, dash="dot"),
            increasing_marker_color=TEAL,
            decreasing_marker_color=CORAL,
            totals_marker_color=INK,
            customdata=labels,
            hovertemplate="%{x} : %{customdata}<extra></extra>",
            cliponaxis=False,
        )
    )
    for stage, height, text in zip(fig.data[0].x, [a, max(a, b), max(b, c), c], labels):
        fig.add_annotation(
            x=stage,
            y=height,
            text=text,
            showarrow=False,
            yanchor="bottom",
            yshift=5,
            font=dict(size=12, color=INK),
        )
    fig.update_yaxes(
        range=[lower, upper],
        title_text=unit,
        tickformat=",.0f" if unit == "commandes" else ",.2f",
    )
    return layout(fig)


def audit_plot(evaluation, selected, after):
    by = evaluation["detection"]["by_type"]
    remaining = evaluation["cleaning"]["remaining_alerts_by_type"]
    keys = sorted(
        by,
        key=lambda k: (
            remaining.get(k, 0) if after else by[k]["detected_alerts"],
            FAMILIES[k],
        ),
    )
    counts = [remaining.get(k, 0) if after else by[k]["detected_alerts"] for k in keys]
    fig = go.Figure(
        go.Bar(
            x=counts,
            y=[FAMILIES[k] for k in keys],
            orientation="h",
            marker_color=[TEAL if k == selected else "#AEBFCC" for k in keys],
            customdata=keys,
            hovertemplate="%{y} : %{x:,} alertes<extra></extra>",
            selected_marker_opacity=1,
            unselected_marker_opacity=1,
        )
    )
    fig.update_layout(clickmode="event+select", showlegend=False)
    fig.update_xaxes(title_text="Alertes dans le rapport", rangemode="tozero")
    return layout(fig, 335).update_yaxes(dtick=1)


def sensitivity(allm, scenario, ratio):
    fig = go.Figure()
    xs = [0.5 + i * 0.05 for i in range(21)]
    for s in SCENARIOS:
        amount = allm[s]["exposure"] / 1e6
        fig.add_scatter(
            x=xs,
            y=[x * amount for x in xs],
            name=SCENARIO_NAMES[s],
            mode="lines",
            line=dict(
                color=PALETTE[s],
                width=4 if s == scenario else 2,
                dash="solid" if s == scenario else "dot",
            ),
            hovertemplate=f"{SCENARIO_NAMES[s]} : %{{y:.2f}} M€<extra></extra>",
        )
    fig.add_vline(x=ratio, line_color=MIST, line_dash="dash")
    fig.add_scatter(
        x=[ratio],
        y=[allm[scenario]["exposure"] * ratio / 1e6],
        mode="markers",
        marker=dict(color=INK, size=13, line=dict(width=2, color="white")),
        showlegend=False,
        hovertemplate="Votre hypothèse : %{y:.2f} M€<extra></extra>",
    )
    fig.update_layout(
        legend=dict(orientation="h", y=1.03, x=0, yanchor="bottom"),
        hovermode="x unified",
    )
    fig.update_xaxes(title="Coefficient du panier inconnu", ticksuffix="×")
    fig.update_yaxes(title="Montant hypothétique (M€)", rangemode="tozero")
    return layout(fig)


def spread(samples):
    vals = samples / 1e6
    p5, p95 = np.percentile(vals, [5, 95])
    fig = go.Figure(
        go.Histogram(
            x=vals,
            nbinsx=45,
            marker_color=TEAL,
            hovertemplate="%{x} M€ : %{y:,} tirages<extra></extra>",
        )
    )
    fig.add_vrect(x0=p5, x1=p95, fillcolor=GOLD, opacity=0.16, line_width=0)
    fig.update_xaxes(title_text="Montant simulé (M€)")
    fig.update_yaxes(title_text="Tirages")
    return layout(fig), p5 * 1e6, p95 * 1e6


def trajectory(m, required, days, capacity, target):
    # Au plus 90 points affichés, y compris le jour exact d'atteinte.
    xs = sorted(
        set(
            [0, days]
            + np.linspace(0, max(1, days), min(90, max(1, days) + 1))
            .astype(int)
            .tolist()
        )
    )
    rates = [100 * (m["known"] + min(x * capacity, required)) / m["orders"] for x in xs]
    fig = go.Figure(
        go.Scatter(
            x=xs,
            y=rates,
            mode="lines+markers" if len(xs) < 25 else "lines",
            line=dict(color=TEAL, width=4),
            fill="tozeroy",
            fillcolor="rgba(25,126,118,.09)",
            hovertemplate="Jour %{x} : %{y:.2f} % documentés<extra></extra>",
        )
    )
    fig.add_hline(y=target, line_dash="dot", line_color=GOLD)
    fig.update_yaxes(
        title="Montants renseignés (%)",
        range=[max(0, min(rates) - 1), min(101, max(rates) + 1)],
    )
    fig.update_xaxes(title="Jours de traitement", rangemode="tozero")
    return layout(fig)


def flow(m, orders):
    total = m["orders"] if orders else m["deliveries"]
    remaining = m["missing"] if orders else m["late"]
    names = (
        ["Commandes", "Avec montant", "Sans montant"]
        if orders
        else ["Livraisons évaluables", "À l’heure", "En retard"]
    )
    fig = go.Figure(
        go.Sankey(
            arrangement="fixed",
            node=dict(
                label=names,
                x=[0.03, 0.83, 0.83],
                y=[0.48, 0.32, 0.84],
                pad=22,
                thickness=13,
                color=[INK, TEAL, CORAL],
                line_width=0,
                hovertemplate="%{label} : %{value:,}<extra></extra>",
            ),
            link=dict(
                source=[0, 0],
                target=[1, 2],
                value=[total - remaining, remaining],
                color=["rgba(25,126,118,.30)", "rgba(189,102,86,.42)"],
                hovertemplate="%{target.label} : %{value:,}<extra></extra>",
            ),
        )
    )
    fig.update_layout(margin=dict(l=10, r=18, t=10, b=10))
    return layout(fig, 225)


def benchmark(allm, pair):
    names = [SCENARIO_NAMES[s] for s in pair]
    fig = go.Figure()
    for key, label, color in (
        ("complete_pct", "Avec montant", TEAL),
        ("missing_pct", "Sans montant", GOLD),
    ):
        vals = [allm[s][key] for s in pair]
        counts = [
            allm[s]["known" if key == "complete_pct" else "missing"] for s in pair
        ]
        fig.add_bar(
            name=label,
            x=vals,
            y=names,
            orientation="h",
            width=0.46,
            marker_color=color,
            customdata=counts,
            hovertemplate=label
            + " : %{x:.1f} %<br>%{customdata:,} commandes<extra></extra>",
        )
    fig.update_layout(
        barmode="stack", legend=dict(orientation="h", y=1.05, x=0, yanchor="bottom")
    )
    fig.update_xaxes(range=[0, 100], ticksuffix=" %", dtick=25)
    fig.update_yaxes(autorange="reversed", type="category")
    return layout(fig, 215)
