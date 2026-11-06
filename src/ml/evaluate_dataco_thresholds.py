"""ConsultAI 360 | Step 7.5: validation-only threshold and error analysis.

Run from project root: python src/ml/evaluate_dataco_thresholds.py
Uses only train.csv and validation.csv; never loads test.csv.
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "reports" / "ml" / "processed"
OUT = ROOT / "reports" / "ml" / "threshold_analysis"
FIGURES = OUT / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)

FEATURES = [
    "shipping_mode",
    "market",
    "region",
    "n_items",
    "total_quantity",
    "total_sales",
    "order_month",
    "order_weekday",
    "order_hour",
    "order_weekend",
]
CATEGORICAL = ["shipping_mode", "market", "region"]
NUMERIC = [name for name in FEATURES if name not in CATEGORICAL]
THRESHOLDS = [0.30, 0.35, 0.40, 0.45, 0.50]
NAVY, GOLD, BLUE, BG, MUTED, GRID = (
    "#101F36",
    "#D4A84B",
    "#4276A4",
    "#F4F6FA",
    "#65758B",
    "#E2E8F0",
)


def load_split(name: str) -> pd.DataFrame:
    path = DATA / f"{name}.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Fichier absent : {path}. Lance prepare_dataco.py")
    frame = pd.read_csv(path)
    absent = sorted(set(FEATURES + ["late"]) - set(frame.columns))
    if absent:
        raise ValueError(f"Colonnes manquantes dans {path.name} : {absent}")
    if (
        frame.empty
        or frame[FEATURES].isna().any().any()
        or not frame["late"].isin([0, 1]).all()
    ):
        raise ValueError(f"Donnees manquantes ou invalides dans {path.name}")
    return frame


def make_model() -> Pipeline:
    prep = ColumnTransformer(
        [
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                CATEGORICAL,
            ),
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                NUMERIC,
            ),
        ]
    )
    return Pipeline(
        [
            ("preprocess", prep),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=120,
                    min_samples_leaf=15,
                    max_features="sqrt",
                    random_state=17,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def score_row(y: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict:
    pred = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = (int(v) for v in confusion_matrix(y, pred, labels=[0, 1]).ravel())
    return {
        "threshold": threshold,
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "alerts": int(pred.sum()),
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "tp": tp,
    }


def new_plot(title: str, subtitle: str):
    fig, ax = plt.subplots(figsize=(11, 6), facecolor=BG)
    ax.set_facecolor(BG)
    fig.subplots_adjust(left=0.12, right=0.94, top=0.76, bottom=0.18)
    fig.text(
        0.12,
        0.94,
        "CONSULTAI 360  /  MACHINE LEARNING",
        color=GOLD,
        fontsize=10,
        weight="bold",
    )
    fig.text(0.12, 0.86, title, color=NAVY, fontsize=18, weight="bold")
    fig.text(0.12, 0.805, subtitle, color=MUTED, fontsize=10)
    fig.text(
        0.12,
        0.055,
        "Source : DataCo | Validation chronologique uniquement",
        color=MUTED,
        fontsize=9,
    )
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED)
    ax.grid(axis="y", color=GRID, zorder=0)
    ax.set_axisbelow(True)
    return fig, ax


def save(fig, name: str):
    fig.savefig(FIGURES / name, dpi=190, bbox_inches="tight", facecolor=BG)
    plt.close(fig)


def main():
    train, valid = load_split("train"), load_split("validation")
    y_train = train["late"].to_numpy(dtype=int)
    y = valid["late"].to_numpy(dtype=int)
    if len(np.unique(y)) != 2:
        raise ValueError("La validation doit contenir les deux classes")
    print(f"Train : {len(train):,} | Validation : {len(valid):,} | Test non charge")
    model = make_model()
    model.fit(train[FEATURES], y_train)
    proba = model.predict_proba(valid[FEATURES])[:, 1]
    roc, pr = float(roc_auc_score(y, proba)), float(average_precision_score(y, proba))

    summary = pd.DataFrame([score_row(y, proba, t) for t in THRESHOLDS])
    summary.to_csv(OUT / "threshold_metrics.csv", index=False)
    print(f"\nROC-AUC={roc:.3f} | PR-AUC={pr:.3f} (independants du seuil)")
    print("\n=== COMPARAISON DES SEUILS ===")
    print(summary.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    segment_rows = []
    for threshold in THRESHOLDS:
        for mode in sorted(valid["shipping_mode"].unique()):
            mask = valid["shipping_mode"].eq(mode).to_numpy()
            row = score_row(y[mask], proba[mask], threshold)
            row["shipping_mode"] = mode
            row["orders"] = int(mask.sum())
            row["actual_late_rate"] = float(y[mask].mean())
            segment_rows.append(row)
    segments = pd.DataFrame(segment_rows)
    segments.to_csv(OUT / "thresholds_by_shipping_mode.csv", index=False)
    print("\n=== RAPPEL PAR MODE ===")
    print(
        segments.pivot(index="shipping_mode", columns="threshold", values="recall")
        .round(3)
        .to_string()
    )
    print("\n=== FAUX NEGATIFS PAR MODE ===")
    print(
        segments.pivot(
            index="shipping_mode", columns="threshold", values="fn"
        ).to_string()
    )

    # Graph 1: recall and precision trade-off.
    fig, ax = new_plot(
        "Precision et rappel selon le seuil",
        "Plus d'alertes peut signifier plus de retards detectes, mais aussi plus de faux positifs",
    )
    x = summary["threshold"].to_numpy(dtype=float) * 100
    ax.plot(
        x,
        summary["recall"].to_numpy(dtype=float) * 100,
        color=GOLD,
        marker="o",
        lw=2.5,
        label="Rappel",
    )
    ax.plot(
        x,
        summary["precision"].to_numpy(dtype=float) * 100,
        color=BLUE,
        marker="o",
        lw=2.5,
        label="Precision",
    )
    ax.set_xlabel("Seuil de decision (%)", color=MUTED)
    ax.set_ylabel("Pourcentage (%)", color=MUTED)
    ax.set_xticks(x)
    ax.set_ylim(0, 105)
    ax.legend(frameon=False)
    save(fig, "01_precision_recall_threshold.png")

    # Graph 2: errors by threshold.
    fig, ax = new_plot(
        "Erreurs selon le seuil de decision",
        "Faux negatifs = retards non detectes ; faux positifs = alertes injustifiees",
    )
    width = 3.5
    ax.bar(
        x - width / 2,
        summary["fn"].to_numpy(dtype=int),
        width=width,
        color=NAVY,
        label="Retards manques",
    )
    ax.bar(
        x + width / 2,
        summary["fp"].to_numpy(dtype=int),
        width=width,
        color=GOLD,
        label="Fausses alertes",
    )
    ax.set_xlabel("Seuil de decision (%)", color=MUTED)
    ax.set_ylabel("Nombre de commandes", color=MUTED)
    ax.set_xticks(x)
    ax.legend(frameon=False)
    save(fig, "02_errors_by_threshold.png")

    # Graph 3: recall by shipping mode.
    fig, ax = new_plot(
        "Detection des retards par mode",
        "Rappel par segment : attention aux performances masquees par la moyenne",
    )
    modes = sorted(valid["shipping_mode"].unique())
    palette = [BLUE, GOLD, NAVY, "#7892AA", "#A3AEBB"]
    positions = np.arange(len(modes), dtype=float)
    bar_width = 0.15
    for idx, threshold in enumerate(THRESHOLDS):
        values = [
            float(
                segments.loc[
                    (segments["threshold"] == threshold)
                    & (segments["shipping_mode"] == mode),
                    "recall",
                ].iloc[0]
            )
            * 100
            for mode in modes
        ]
        ax.bar(
            positions + (idx - 2) * bar_width,
            values,
            width=bar_width,
            label=f"{threshold:.0%}",
            color=palette[idx],
        )
    ax.set_xticks(positions, modes)
    ax.set_ylabel("Retards detectes (%)", color=MUTED)
    ax.set_ylim(0, 105)
    ax.legend(frameon=False, ncol=5, loc="upper center", bbox_to_anchor=(0.5, 1.12))
    save(fig, "03_recall_by_shipping_mode.png")

    # Graph 4: probability distributions by true class.
    fig, ax = new_plot(
        "Probabilites predites et retards reels",
        "Distribution des scores de risque selon le resultat observe",
    )
    bins = np.linspace(0, 1, 21)
    ax.hist(
        proba[y == 0],
        bins=bins.tolist(),
        alpha=0.65,
        density=True,
        color=BLUE,
        label="Sans retard",
    )
    ax.hist(
        proba[y == 1],
        bins=bins.tolist(),
        alpha=0.55,
        density=True,
        color=GOLD,
        label="Retard",
    )
    ax.set_xlabel("Probabilite predite de retard", color=MUTED)
    ax.set_ylabel("Densite", color=MUTED)
    ax.legend(frameon=False)
    save(fig, "04_score_distributions.png")

    # Do not auto-pick a threshold without explicit business cost constraints.
    metadata = {
        "source": "DataCo",
        "split_used_for_evaluation": "validation",
        "test_used": False,
        "train_orders": len(train),
        "validation_orders": len(valid),
        "features": FEATURES,
        "thresholds": THRESHOLDS,
        "roc_auc": roc,
        "pr_auc": pr,
        "random_forest": {
            "n_estimators": 120,
            "min_samples_leaf": 15,
            "max_features": "sqrt",
            "random_state": 17,
        },
        "selection": "No threshold selected automatically; compare operational costs and segment recall first.",
        "caution": "Changing thresholds cannot improve ROC-AUC or PR-AUC; these measure ranking quality.",
    }
    (OUT / "analysis_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n4 graphiques et 3 fichiers de synthese : {OUT}")
    print("Seuil non selectionne automatiquement : couts metier a definir.")


if __name__ == "__main__":
    main()
