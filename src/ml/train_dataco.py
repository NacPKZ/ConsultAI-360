import json
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
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
NUMERIC = [x for x in FEATURES if x not in CATEGORICAL]


def load(split):
    path = DATA / f"{split}.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Fichier manquant : {path}. Lance prepare_dataco.py.")
    frame = pd.read_csv(path)
    expected = set(FEATURES + ["late"])
    if not expected.issubset(frame.columns):
        raise ValueError(
            f"Colonnes absentes dans {path.name}: {sorted(expected - set(frame.columns))}"
        )
    if not frame["late"].isin([0, 1]).all():
        raise ValueError("Cible invalide")
    return frame


train = load("train")
valid = load("validation")
print(f"Train : {len(train):,} | Validation : {len(valid):,} | Test non chargé")

preprocess = ColumnTransformer(
    transformers=[
        (
            "categorical",
            Pipeline(
                steps=[
                    ("imputer", SimpleImputer(strategy="most_frequent")),
                    ("encoder", OneHotEncoder(handle_unknown="ignore")),
                ]
            ),
            CATEGORICAL,
        ),
        (
            "numeric",
            Pipeline(
                steps=[
                    ("imputer", SimpleImputer(strategy="median")),
                    ("scaler", StandardScaler()),
                ]
            ),
            NUMERIC,
        ),
    ]
)
models = {
    "dummy": DummyClassifier(strategy="prior"),
    "logistic_regression": LogisticRegression(max_iter=1500, random_state=17),
    "random_forest": RandomForestClassifier(
        n_estimators=120,
        min_samples_leaf=15,
        max_features="sqrt",
        random_state=17,
        n_jobs=-1,
    ),
}
results = []
segment_results = []
for name, estimator in models.items():
    model = Pipeline([("preprocess", preprocess), ("model", estimator)])
    model.fit(train[FEATURES], train["late"])
    probabilities = model.predict_proba(valid[FEATURES])[:, 1]
    predictions = (probabilities >= 0.5).astype(int)
    y = valid["late"].to_numpy()
    tn, fp, fn, tp = confusion_matrix(y, predictions, labels=[0, 1]).ravel()
    row = {
        "model": name,
        "roc_auc": roc_auc_score(y, probabilities),
        "pr_auc": average_precision_score(y, probabilities),
        "balanced_accuracy": balanced_accuracy_score(y, predictions),
        "precision": precision_score(y, predictions, zero_division=0),
        "recall": recall_score(y, predictions, zero_division=0),
        "f1": f1_score(y, predictions, zero_division=0),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }
    results.append(row)
    for mode in sorted(valid["shipping_mode"].unique()):
        mask = valid["shipping_mode"].eq(mode).to_numpy()
        segment_results.append(
            {
                "model": name,
                "shipping_mode": mode,
                "n_orders": int(mask.sum()),
                "actual_late_rate": float(y[mask].mean()),
                "predicted_late_rate": float(predictions[mask].mean()),
                "recall": float(
                    recall_score(y[mask], predictions[mask], zero_division=0)
                ),
            }
        )
    print(
        f"{name:20} ROC-AUC={row['roc_auc']:.3f} PR-AUC={row['pr_auc']:.3f} F1={row['f1']:.3f} Recall={row['recall']:.3f}"
    )

pd.DataFrame(results).sort_values("roc_auc", ascending=False).to_csv(
    OUT / "validation_metrics.csv", index=False
)
pd.DataFrame(segment_results).to_csv(
    OUT / "validation_by_shipping_mode.csv", index=False
)
(OUT / "run_info.json").write_text(
    json.dumps(
        {
            "prediction_moment": "order finalized",
            "train_orders": len(train),
            "validation_orders": len(valid),
            "test_used": False,
            "threshold": 0.5,
            "features": FEATURES,
            "note": "Model selection based on validation only; test reserved for final evaluation.",
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)
print(f"\nRésultats enregistrés : {OUT}")
