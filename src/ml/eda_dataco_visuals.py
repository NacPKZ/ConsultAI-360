"""ConsultAI 360 — DataCo: visualisations EDA au niveau commande."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter, PercentFormatter

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "reports" / "ml" / "dataco_orders_audit.csv"
OUTPUT = ROOT / "reports" / "ml" / "figures"
OUTPUT.mkdir(parents=True, exist_ok=True)

NAVY = "#101F36"
GOLD = "#D4A84B"
BLUE = "#4276A4"
PALE = "#F4F6FA"
MUTED = "#65758B"
GRID = "#E2E8F0"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "figure.facecolor": PALE,
        "axes.facecolor": PALE,
        "savefig.facecolor": PALE,
        "axes.edgecolor": GRID,
        "axes.labelcolor": NAVY,
        "text.color": NAVY,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


def canvas(title: str, subtitle: str):
    fig, ax = plt.subplots(figsize=(11.8, 6.6))
    fig.subplots_adjust(left=0.19, right=0.90, top=0.72, bottom=0.20)
    fig.text(
        0.08,
        0.94,
        "CONSULTAI 360",
        color=GOLD,
        fontsize=11,
        fontweight="bold",
    )
    fig.text(0.08, 0.86, title, color=NAVY, fontsize=19, fontweight="bold")
    fig.text(0.08, 0.81, subtitle, color=MUTED, fontsize=10)
    fig.text(
        0.08,
        0.055,
        "Source : DataCo  |  Grain : commande  |  Analyse descriptive",
        color=MUTED,
        fontsize=9,
    )
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    return fig, ax


def save(fig, filename: str):
    fig.savefig(OUTPUT / filename, dpi=190, bbox_inches="tight")
    plt.close(fig)


def summary(frame: pd.DataFrame, group: str) -> pd.DataFrame:
    """Une ligne par modalité, sans agrégation nommée ambiguë pour Pylance."""
    result = frame.groupby(group, dropna=False)["late"].agg(["mean", "count"])
    result = result.rename(columns={"mean": "rate", "count": "orders"})
    result["rate"] = result["rate"] * 100.0
    return result


def label_count(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def main():
    if not INPUT.is_file():
        raise FileNotFoundError(
            f"Audit introuvable : {INPUT}. Lance d'abord eda_dataco.py"
        )
    df = pd.read_csv(INPUT, parse_dates=["order_date"])
    required = {
        "Order Id",
        "order_date",
        "late",
        "shipping_mode",
        "scheduled_days",
        "split",
    }
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Colonnes absentes : {sorted(missing)}")
    if not df["Order Id"].is_unique:
        raise ValueError("Plusieurs lignes par commande dans l'audit")
    if df[list(required)].isna().any().any():
        raise ValueError("Valeurs manquantes dans les colonnes nécessaires")
    if not df["late"].isin([0, 1]).all():
        raise ValueError("La cible doit être binaire : 0 ou 1")

    # 01 — Risque et volume par mode
    shipping = summary(df, "shipping_mode").sort_values(by="rate", ascending=True)
    fig, ax = canvas(
        "Quels modes présentent le plus de retards ?",
        "Taux de retard et nombre de commandes par mode d'expédition",
    )
    names = shipping.index.astype(str).tolist()
    rates = shipping["rate"].to_numpy(dtype=float).tolist()
    counts = shipping["orders"].to_numpy(dtype=int).tolist()
    ax.barh(names, rates, color=[BLUE if x < 70 else GOLD for x in rates], height=0.54)
    ax.set_xlim(0, 115)
    ax.xaxis.set_major_formatter(PercentFormatter(xmax=100))
    ax.set_xlabel("Part des commandes en retard")
    for i, (rate, count) in enumerate(zip(rates, counts)):
        ax.text(
            rate + 1.2,
            i,
            f"{rate:.1f}%  ·  {label_count(count)} cmd",
            va="center",
            fontsize=10,
            color=NAVY,
        )
    save(fig, "01_shipping_risk.png")

    # 02 — Tendance mensuelle avec volume
    monthly = df.set_index("order_date").resample("MS")["late"].agg(["mean", "count"])
    monthly = monthly.rename(columns={"mean": "rate", "count": "orders"})
    monthly["rate"] = monthly["rate"] * 100.0
    fig, ax = canvas(
        "Le risque de retard évolue-t-il dans le temps ?",
        "Taux mensuel ; ligne dorée = moyenne sur la période",
    )
    ax.plot(
        monthly.index, monthly["rate"].to_numpy(dtype=float), color=BLUE, linewidth=2.4
    )
    ax.axhline(
        float(df["late"].mean() * 100),
        color=GOLD,
        linewidth=2,
        linestyle="--",
        label="Moyenne",
    )
    ax.grid(axis="y", color=GRID)
    ax.set_ylabel("Commandes en retard")
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=100))
    ax.legend(frameon=False, loc="upper right")
    save(fig, "02_monthly_trend.png")

    # 03 — Délai promis
    scheduled = summary(df, "scheduled_days").sort_index()
    fig, ax = canvas(
        "Le délai promis est-il associé au risque ?",
        "Taux de retard par délai d'expédition prévu ; volumes annotés",
    )
    days = scheduled.index.astype(str).tolist()
    rates = scheduled["rate"].to_numpy(dtype=float).tolist()
    counts = scheduled["orders"].to_numpy(dtype=int).tolist()
    ax.barh(days, rates, color=BLUE, height=0.55)
    ax.set_xlim(0, 115)
    ax.xaxis.set_major_formatter(PercentFormatter(xmax=100))
    ax.set_xlabel("Part des commandes en retard")
    ax.set_ylabel("Délai prévu (jours)")
    for i, (rate, count) in enumerate(zip(rates, counts)):
        ax.text(
            rate + 1.2,
            i,
            f"{rate:.1f}%  ·  n={label_count(count)}",
            va="center",
            fontsize=10,
            color=NAVY,
        )
    save(fig, "03_scheduled_days.png")

    # 04 — Répartition des volumes
    volumes = df["shipping_mode"].value_counts().sort_values(ascending=True)
    fig, ax = canvas(
        "Où se concentre le volume logistique ?",
        "Nombre de commandes par mode d'expédition",
    )
    names = volumes.index.astype(str).tolist()
    counts = volumes.to_numpy(dtype=int).tolist()
    ax.barh(names, counts, color=BLUE, height=0.55)
    max_count = max(counts)
    ax.set_xlim(0, max_count * 1.22)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: label_count(int(x))))
    ax.set_xlabel("Nombre de commandes")
    for i, count in enumerate(counts):
        ax.text(
            count + max_count * 0.025,
            i,
            label_count(count),
            va="center",
            fontsize=10,
            color=NAVY,
        )
    save(fig, "04_shipping_volumes.png")

    # 05 — Stabilité du split
    split = summary(df, "split").reindex(["train", "validation", "test"])
    if split.isna().any().any():
        raise ValueError("Split train/validation/test incomplet")
    fig, ax = canvas(
        "Les ensembles ML sont-ils comparables ?",
        "Contrôle méthodologique : proportion de retards par période",
    )
    labels = ["Entraînement", "Validation", "Test"]
    rates = split["rate"].to_numpy(dtype=float).tolist()
    counts = split["orders"].to_numpy(dtype=int).tolist()
    ax.barh(labels, rates, color=[BLUE, BLUE, GOLD], height=0.48)
    ax.set_xlim(0, 75)
    ax.xaxis.set_major_formatter(PercentFormatter(xmax=100))
    ax.set_xlabel("Part des commandes en retard")
    for i, (rate, count) in enumerate(zip(rates, counts)):
        ax.text(
            rate + 1,
            i,
            f"{rate:.2f}%  ·  n={label_count(count)}",
            va="center",
            color=NAVY,
            fontsize=10,
        )
    save(fig, "05_split_stability.png")

    print("\n=== DÉLAI PRÉVU ===")
    print(scheduled.round(2).to_string())
    print("\n=== VOLUMES PAR MODE ===")
    print(volumes.to_string())
    print("\n=== TAUX PAR SPLIT ===")
    print(split.round(2).to_string())
    print("\n5 GRAPHIQUES GÉNÉRÉS :", OUTPUT)


if __name__ == "__main__":
    main()
