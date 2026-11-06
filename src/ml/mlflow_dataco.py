"""Track DataCo delivery-risk experiments in local MLflow.

Run from project root: python src/ml/mlflow_dataco.py
Uses train/validation only. Never loads test.csv.
"""

from pathlib import Path

import mlflow
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
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
TRACKING = ROOT / "reports" / "ml" / "mlruns"
TRACKING.mkdir(parents=True, exist_ok=True)
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
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}; run prepare_dataco.py first")
    df = pd.read_csv(path)
    required = set(FEATURES + ["late"])
    if not required.issubset(df.columns):
        raise ValueError(f"Missing columns: {sorted(required - set(df.columns))}")
    if df[FEATURES].isna().any().any() or not df["late"].isin([0, 1]).all():
        raise ValueError(f"Invalid features/target in {split}")
    return df


def preprocessor():
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


def evaluate(y, scores, threshold=0.5):
    pred = (scores >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "roc_auc": float(roc_auc_score(y, scores)),
        "pr_auc": float(average_precision_score(y, scores)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }


def main():
    train, valid = load("train"), load("validation")
    xtrain, ytrain = train[FEATURES], train["late"].to_numpy()
    xvalid, yvalid = valid[FEATURES], valid["late"].to_numpy()
    DB_PATH = ROOT / "reports" / "ml" / "mlflow.db"
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    mlflow.set_tracking_uri(f"sqlite:///{DB_PATH.as_posix()}")
    mlflow.set_experiment("ConsultAI360_DataCo_Delivery_Risk")
    print(f"Train {len(train):,} | Validation {len(valid):,} | Test non charge")
    models = [
        (
            "dummy",
            DummyClassifier(strategy="most_frequent"),
            {"strategy": "most_frequent"},
        ),
        (
            "logistic_regression",
            Pipeline(
                [
                    ("preprocess", preprocessor()),
                    ("model", LogisticRegression(max_iter=1000, random_state=17)),
                ]
            ),
            {"max_iter": 1000, "random_state": 17},
        ),
        (
            "random_forest",
            Pipeline(
                [
                    ("preprocess", preprocessor()),
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
            ),
            {
                "n_estimators": 120,
                "min_samples_leaf": 15,
                "max_features": "sqrt",
                "random_state": 17,
            },
        ),
    ]
    results = []
    for name, model, params in models:
        with mlflow.start_run(run_name=name):
            mlflow.set_tags(
                {
                    "project": "ConsultAI 360",
                    "dataset": "DataCo",
                    "split": "chronological",
                    "evaluation": "validation_only",
                    "test_used": "false",
                }
            )
            mlflow.log_params(
                {
                    "model": name,
                    "threshold": 0.5,
                    "train_orders": len(train),
                    "validation_orders": len(valid),
                    **params,
                }
            )
            model.fit(xtrain, ytrain)
            scores = model.predict_proba(xvalid)[:, 1]
            metrics = evaluate(yvalid, scores)
            mlflow.log_metrics(metrics)
            mlflow.log_dict(
                {
                    "features": FEATURES,
                    "categorical": CATEGORICAL,
                    "numeric": NUMERIC,
                    "notes": "Validation only. Do not infer causality or actual ROI.",
                },
                "metadata.json",
            )
            results.append({"model": name, **metrics})
            print(
                f"{name:20} ROC-AUC={metrics['roc_auc']:.3f} PR-AUC={metrics['pr_auc']:.3f} F1={metrics['f1']:.3f} Recall={metrics['recall']:.3f}"
            )
    print("\nResults logged to:", DB_PATH)
    print(pd.DataFrame(results).to_string(index=False))


print(
    '\nLaunch UI: python -m mlflow ui --backend-store-uri "'
    + mlflow.get_tracking_uri()
    + '" --port 5000'
)


if __name__ == "__main__":
    main()
