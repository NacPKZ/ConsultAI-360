"""Compare a shipping-mode-only baseline with the existing Random Forest.

Run from project root: python src/ml/compare_shipping_baseline.py
Only train.csv and validation.csv are loaded; test.csv stays untouched.
"""

import json
from pathlib import Path

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
OUT = ROOT / "reports" / "ml" / "model_comparison"
OUT.mkdir(parents=True, exist_ok=True)

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
NUMERIC = [col for col in FEATURES if col not in CATEGORICAL]


def load(name: str) -> pd.DataFrame:
    path = DATA / f"{name}.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Fichier absent : {path}. Lance prepare_dataco.py")
    frame = pd.read_csv(path)
    missing = set(FEATURES + ["late"]) - set(frame.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes dans {path.name} : {sorted(missing)}")
    if not frame["late"].isin([0, 1]).all():
        raise ValueError(f"Cible invalide dans {path.name}")
    if frame[FEATURES].isna().any().any():
        raise ValueError(f"Features manquantes dans {path.name}")
    return frame


def make_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
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


def metrics(name: str, y: np.ndarray, scores: np.ndarray) -> dict:
    predicted = (scores >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, predicted, labels=[0, 1]).ravel()
    return {
        "model": name,
        "roc_auc": float(roc_auc_score(y, scores)),
        "pr_auc": float(average_precision_score(y, scores)),
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted, zero_division=0)),
        "f1": float(f1_score(y, predicted, zero_division=0)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }


def main() -> None:
    train = load("train")
    valid = load("validation")
    y_train = train["late"].to_numpy()
    y_valid = valid["late"].to_numpy()
    print(f"Train : {len(train):,} | Validation : {len(valid):,} | Test non charge")

    # Baseline metier: probability of delay observed in the training set
    # for each shipping mode; unseen modes use the global training rate.
    mode_rates = train.groupby("shipping_mode")["late"].mean()
    global_rate = float(train["late"].mean())
    baseline_scores = (
        valid["shipping_mode"].map(mode_rates).fillna(global_rate).to_numpy(dtype=float)
    )

    # Same Random Forest architecture and hyperparameters as train_dataco.py.
    forest = Pipeline(
        [
            ("preprocess", make_preprocessor()),
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
    forest.fit(train[FEATURES], y_train)
    forest_scores = forest.predict_proba(valid[FEATURES])[:, 1]

    rows = [
        metrics("shipping_mode_baseline", y_valid, baseline_scores),
        metrics("random_forest", y_valid, forest_scores),
    ]
    summary = pd.DataFrame(rows)
    summary.to_csv(OUT / "shipping_baseline_comparison.csv", index=False)

    segment_rows = []
    for name, scores in [
        ("shipping_mode_baseline", baseline_scores),
        ("random_forest", forest_scores),
    ]:
        predictions = (scores >= 0.5).astype(int)
        for mode in sorted(valid["shipping_mode"].unique()):
            mask = valid["shipping_mode"].eq(mode).to_numpy()
            actual = y_valid[mask]
            segment_rows.append(
                {
                    "model": name,
                    "shipping_mode": mode,
                    "orders": int(mask.sum()),
                    "actual_late_rate": float(actual.mean()),
                    "predicted_late_rate": float(predictions[mask].mean()),
                    "recall": float(
                        recall_score(actual, predictions[mask], zero_division=0)
                    ),
                    "false_negatives": int(
                        ((actual == 1) & (predictions[mask] == 0)).sum()
                    ),
                }
            )
    pd.DataFrame(segment_rows).to_csv(
        OUT / "shipping_baseline_by_mode.csv", index=False
    )

    info = {
        "train_orders": len(train),
        "validation_orders": len(valid),
        "test_used": False,
        "threshold": 0.5,
        "baseline": "Training-set mean delay rate per shipping_mode",
        "random_forest_parameters": {
            "n_estimators": 120,
            "min_samples_leaf": 15,
            "max_features": "sqrt",
            "random_state": 17,
        },
        "warning": "Compare on validation only. Do not claim causal effects.",
    }
    (OUT / "shipping_baseline_run_info.json").write_text(
        json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("\n=== COMPARAISON VALIDATION ===")
    print(summary.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print("\n=== TAUX DE RETARD APPRIS SUR TRAIN ===")
    print(mode_rates.round(3).to_string())
    print("\n=== RAPPEL PAR MODE ===")
    print(
        pd.DataFrame(segment_rows)[
            ["model", "shipping_mode", "orders", "recall", "false_negatives"]
        ].to_string(index=False, float_format=lambda x: f"{x:.3f}")
    )
    print(f"\nFichiers enregistres : {OUT}")


if __name__ == "__main__":
    main()
