"""ConsultAI 360 | 7.5.2: explainability and illustrative alert-cost scenarios.

Run from repository root: python src/ml/explain_dataco.py
Reads train/validation only. Never opens test.csv.
"""

from __future__ import annotations

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
from sklearn.inspection import permutation_importance
from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "reports" / "ml" / "processed"
OUT = ROOT / "reports" / "ml" / "explainability"
FIG = OUT / "figures"
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
NUMERIC = [x for x in FEATURES if x not in CATEGORICAL]
THRESHOLDS = [0.30, 0.35, 0.40, 0.45, 0.50]
# Illustrative euro values, NOT empirical DataCo costs. All combinations are evaluated.
FALSE_ALERT_COSTS = [2, 5, 10, 20]
MISSED_DELAY_COSTS = [10, 25, 50, 100]
NAVY, GOLD, BLUE, MUTED, BG = "#14243B", "#D5A63F", "#457DA8", "#6F8299", "#F5F7FA"


def load(name: str) -> pd.DataFrame:
    path = DATA / f"{name}.csv"
    if not path.is_file():
        raise FileNotFoundError(f"{path} absent. Exécuter prepare_dataco.py.")
    df = pd.read_csv(path)
    missing = set(FEATURES + ["late"]) - set(df.columns)
    if missing:
        raise ValueError(f"{name}: colonnes manquantes: {sorted(missing)}")
    if df[FEATURES].isna().any().any() or not df["late"].isin([0, 1]).all():
        raise ValueError(f"{name}: données invalides (NaN ou cible non binaire).")
    return df


def model() -> Pipeline:
    pre = ColumnTransformer(
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
            ("preprocess", pre),
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


def style(ax, title: str, subtitle: str) -> None:
    ax.set_facecolor(BG)
    ax.figure.patch.set_facecolor(BG)
    ax.set_title(title, loc="left", fontsize=16, color=NAVY, fontweight="bold", pad=34)
    ax.text(
        0, 1.025, subtitle, transform=ax.transAxes, color=MUTED, fontsize=9, va="bottom"
    )
    ax.grid(axis="x", color="#DCE4ED", alpha=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=MUTED)
    for spine in ax.spines.values():
        spine.set_visible(False)


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    train, valid = load("train"), load("validation")
    y_train, y_valid = train["late"].to_numpy(), valid["late"].to_numpy()
    print(f"Train: {len(train):,} | Validation: {len(valid):,} | Test non chargé")
    forest = model()
    forest.fit(train[FEATURES], y_train)
    proba = forest.predict_proba(valid[FEATURES])[:, 1]
    print(f"ROC-AUC validation: {roc_auc_score(y_valid, proba):.3f}")
    print(f"PR-AUC validation: {average_precision_score(y_valid, proba):.3f}")

    # Use a fixed reproducible subset of validation for faster permutation importance.
    rng = np.random.default_rng(17)
    idx = np.sort(rng.choice(len(valid), size=min(2500, len(valid)), replace=False))
    X_sample = valid.iloc[idx][FEATURES]
    y_sample = y_valid[idx]
    result = permutation_importance(
        forest,
        X_sample,
        y_sample,
        scoring="roc_auc",
        n_repeats=3,
        random_state=17,
        n_jobs=1,
    )
    importance = pd.DataFrame(
        {
            "feature": FEATURES,
            "auc_drop_mean": np.asarray(result["importances_mean"]),
            "auc_drop_std": np.asarray(result["importances_std"]),
        }
    ).sort_values("auc_drop_mean", ascending=False)
    importance.to_csv(OUT / "permutation_importance.csv", index=False)
    print("\n=== IMPORTANCE DES VARIABLES (baisse ROC-AUC) ===")
    print(importance.to_string(index=False, float_format=lambda v: f"{v:.4f}"))

    fig, ax = plt.subplots(figsize=(11, 6.5))
    fig.subplots_adjust(left=0.24, right=0.96, top=0.79, bottom=0.13)
    ordered = importance.iloc[::-1]
    ax.barh(
        ordered["feature"],
        ordered["auc_drop_mean"],
        color=[GOLD if x == "shipping_mode" else BLUE for x in ordered["feature"]],
    )
    ax.axvline(0, color=NAVY, linewidth=1)
    ax.set_xlabel("Diminution moyenne de ROC-AUC après permutation", color=MUTED)
    style(
        ax,
        "Quelles variables comptent vraiment ?",
        "Permutation importance sur 2 500 commandes de validation maximum | 3 répétitions",
    )
    fig.text(
        0.04,
        0.96,
        "CONSULTAI 360 / MACHINE LEARNING",
        color=GOLD,
        fontsize=10,
        fontweight="bold",
    )
    fig.savefig(FIG / "01_permutation_importance.png", dpi=180, facecolor=BG)
    plt.close(fig)

    # Confusion counts are computed on ALL validation rows for each threshold.
    counts = []
    for threshold in THRESHOLDS:
        predicted = (proba >= threshold).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_valid, predicted, labels=[0, 1]).ravel()
        counts.append(
            {
                "threshold": threshold,
                "tn": int(tn),
                "fp": int(fp),
                "fn": int(fn),
                "tp": int(tp),
                "precision": float(tp / (tp + fp)) if tp + fp else 0.0,
                "recall": float(tp / (tp + fn)) if tp + fn else 0.0,
            }
        )
    count_df = pd.DataFrame(counts)
    count_df.to_csv(OUT / "threshold_confusion_counts.csv", index=False)

    # Theoretical cost = false alerts * intervention cost + missed delays * missed-delay cost.
    # No assumption that intervention actually prevents a late delivery.
    scenarios = []
    for fp_cost in FALSE_ALERT_COSTS:
        for fn_cost in MISSED_DELAY_COSTS:
            for row in counts:
                scenarios.append(
                    {
                        "false_alert_cost_eur": fp_cost,
                        "missed_delay_cost_eur": fn_cost,
                        "threshold": row["threshold"],
                        "fp": row["fp"],
                        "fn": row["fn"],
                        "simulated_cost_eur": row["fp"] * fp_cost + row["fn"] * fn_cost,
                    }
                )
    cost_df = pd.DataFrame(scenarios)
    cost_df.to_csv(OUT / "illustrative_cost_scenarios.csv", index=False)
    best = (
        cost_df.sort_values(
            [
                "false_alert_cost_eur",
                "missed_delay_cost_eur",
                "simulated_cost_eur",
                "threshold",
            ]
        )
        .groupby(["false_alert_cost_eur", "missed_delay_cost_eur"], as_index=False)
        .first()
    )
    best.to_csv(OUT / "best_threshold_by_cost_scenario.csv", index=False)

    # Visualize three explicit, illustrative scenarios; no universal optimum is asserted.
    selected = [(5, 25), (10, 25), (5, 50)]
    fig, ax = plt.subplots(figsize=(11, 6.5))
    fig.subplots_adjust(left=0.12, right=0.95, top=0.78, bottom=0.22)
    for (fp_cost, fn_cost), color in zip(selected, [BLUE, NAVY, GOLD]):
        part = cost_df[
            (cost_df.false_alert_cost_eur == fp_cost)
            & (cost_df.missed_delay_cost_eur == fn_cost)
        ]
        ax.plot(
            part.threshold * 100,
            part.simulated_cost_eur,
            marker="o",
            linewidth=2.5,
            color=color,
            label=f"Fausse alerte {fp_cost} € / Retard manqué {fn_cost} €",
        )
    ax.set_xlabel("Seuil de décision (%)", color=MUTED)
    ax.set_ylabel("Coût simulé (€) sur la validation", color=MUTED)
    ax.grid(axis="y", color="#DCE4ED")
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.15),
        ncol=1,
        frameon=False,
        fontsize=9,
    )
    style(
        ax,
        "Coût simulé selon le seuil",
        "Hypothèses illustratives uniquement | Coût = FP × coût alerte + FN × coût retard manqué",
    )
    fig.text(
        0.04,
        0.96,
        "CONSULTAI 360 / SIMULATION MÉTIER",
        color=GOLD,
        fontsize=10,
        fontweight="bold",
    )
    fig.savefig(FIG / "02_simulated_cost_by_threshold.png", dpi=180, facecolor=BG)
    plt.close(fig)

    metadata = {
        "data_used": ["train.csv", "validation.csv"],
        "test_used": False,
        "model": "RandomForestClassifier",
        "parameters": {
            "n_estimators": 120,
            "min_samples_leaf": 15,
            "max_features": "sqrt",
            "random_state": 17,
        },
        "importance_method": "permutation_importance",
        "importance_scoring": "roc_auc",
        "importance_sample_size": len(idx),
        "importance_repeats": 3,
        "thresholds": THRESHOLDS,
        "simulation_warning": "Illustrative costs only. Not actual ROI; no causal intervention effect measured.",
    }
    (OUT / "analysis_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("\n=== MATRICES DE CONFUSION PAR SEUIL ===")
    print(count_df.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print("\n=== MEILLEUR SEUIL PAR HYPOTHÈSE DE COÛTS (simulation) ===")
    print(
        best[
            [
                "false_alert_cost_eur",
                "missed_delay_cost_eur",
                "threshold",
                "simulated_cost_eur",
            ]
        ].to_string(index=False)
    )
    print(f"\nFichiers enregistrés : {OUT}")


if __name__ == "__main__":
    main()
