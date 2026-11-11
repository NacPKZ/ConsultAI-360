"""One-time held-out evaluation of the frozen DataCo delivery-risk pipeline.

Run at the project root: python src/ml/final_evaluation_dataco.py
Train+validation refit; test is used only for final evaluation.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
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
OUT = ROOT / "reports" / "ml" / "final_evaluation"
REPORT = ROOT / "docs" / "08_rapport_final_prediction.md"
THRESHOLD = 0.40  # FROZEN before reading test
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
NUMERIC = [f for f in FEATURES if f not in CATEGORICAL]
PARAMS = {
    "n_estimators": 120,
    "min_samples_leaf": 15,
    "max_features": "sqrt",
    "random_state": 17,
    "n_jobs": -1,
}


def load(split: str) -> pd.DataFrame:
    path = DATA / f"{split}.csv"
    if not path.is_file():
        raise FileNotFoundError(
            f"Fichier manquant : {path}. Exécuter prepare_dataco.py"
        )
    df = pd.read_csv(path)
    missing = set(FEATURES + ["late"]) - set(df.columns)
    if missing:
        raise ValueError(f"{split}: colonnes manquantes : {sorted(missing)}")
    if df[FEATURES].isna().any().any() or not df["late"].isin([0, 1]).all():
        raise ValueError(f"{split}: valeurs manquantes ou cible invalide")
    if "Order Id" in df and df["Order Id"].duplicated().any():
        raise ValueError(f"{split}: commandes dupliquées")
    return df


def evaluate(name: str, y: np.ndarray, scores: np.ndarray) -> dict:
    pred = (scores >= THRESHOLD).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "model": name,
        "threshold": THRESHOLD,
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


def make_model() -> Pipeline:
    preprocess = ColumnTransformer(
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
        [("preprocess", preprocess), ("model", RandomForestClassifier(**PARAMS))]
    )


def fmt(x: float) -> str:
    return f"{x:.3f}"


def main() -> None:
    # Refuse accidental re-testing. To rerun for a genuine technical failure,
    # investigate first rather than deleting the lock simply to improve scores.
    if (OUT / "final_metrics.csv").exists():
        raise RuntimeError(
            "Test final déjà évalué : résultats existants. Ne pas retester."
        )

    # Read and validate development data first.
    train, valid = load("train"), load("validation")
    if "Order Id" in train and "Order Id" in valid:
        if set(train["Order Id"]) & set(valid["Order Id"]):
            raise ValueError("Chevauchement train/validation")
    development = pd.concat([train, valid], ignore_index=True)
    model = make_model()
    print(
        f"Entraînement final sur {len(development):,} commandes (train + validation)..."
    )
    model.fit(development[FEATURES], development["late"].to_numpy())
    mode_rates = development.groupby("shipping_mode")["late"].mean()
    global_rate = float(development["late"].mean())

    # Only now open the held-out test dataset.
    test_path = DATA / "test.csv"
    test_hash = hashlib.sha256(test_path.read_bytes()).hexdigest()
    test = load("test")
    if "Order Id" in development and "Order Id" in test:
        if set(development["Order Id"]) & set(test["Order Id"]):
            raise ValueError("Fuite : commandes présentes dans développement et test")
    y = test["late"].to_numpy()
    if len(np.unique(y)) != 2:
        raise ValueError("Test : une seule classe, métriques AUC impossibles")
    scores = model.predict_proba(test[FEATURES])[:, 1]
    baseline = (
        test["shipping_mode"].map(mode_rates).fillna(global_rate).to_numpy(dtype=float)
    )
    rows = [
        evaluate("shipping_mode_baseline", y, baseline),
        evaluate("random_forest", y, scores),
    ]
    results = pd.DataFrame(rows)
    segment_rows = []
    for name, probabilities in [
        ("shipping_mode_baseline", baseline),
        ("random_forest", scores),
    ]:
        predictions = (probabilities >= THRESHOLD).astype(int)
        for mode in sorted(test["shipping_mode"].unique()):
            mask = test["shipping_mode"].eq(mode).to_numpy()
            actual, predicted = y[mask], predictions[mask]
            segment_rows.append(
                {
                    "model": name,
                    "shipping_mode": mode,
                    "orders": int(mask.sum()),
                    "actual_late_rate": float(actual.mean()),
                    "precision": float(
                        precision_score(actual, predicted, zero_division=0)
                    ),
                    "recall": float(recall_score(actual, predicted, zero_division=0)),
                    "false_positives": int(((actual == 0) & (predicted == 1)).sum()),
                    "false_negatives": int(((actual == 1) & (predicted == 0)).sum()),
                }
            )
    segments = pd.DataFrame(segment_rows)
    OUT.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUT / "final_metrics.csv", index=False)
    segments.to_csv(OUT / "final_by_shipping_mode.csv", index=False)
    metadata = {
        "evaluated_at_utc": datetime.now(UTC).isoformat(),
        "train_orders": len(train),
        "validation_orders": len(valid),
        "test_orders": len(test),
        "test_sha256": test_hash,
        "decision_threshold": THRESHOLD,
        "model_params": PARAMS,
        "features": FEATURES,
        "selection": "Fixed from validation before opening test",
        "baseline": "Training+validation late rate per shipping_mode",
        "caveats": [
            "DataCo late shipping risk is not verified final-mile delivery delay",
            "Synthetic cost scenarios are not observed savings",
            "This is one held-out evaluation; no test-driven retuning",
        ],
    }
    (OUT / "final_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    rf = rows[1]
    baseline_row = rows[0]
    report = f"""# ConsultAI 360 — Évaluation finale Machine Learning (DataCo)

## Résumé exécutif

Problème : prédire le **risque de retard d'expédition** d'une commande DataCo à partir des informations disponibles au moment de la commande. Le jeu de données ne permet pas de vérifier la date de livraison finale au client.

**Modèle retenu avant test :** Random Forest (120 arbres, minimum 15 observations par feuille, `max_features=sqrt`, graine 17). **Seuil fixé avant test : 40 %.**

## Protocole

- Train : {len(train):,} commandes ; validation : {len(valid):,} ; test indépendant : {len(test):,}.
- Sélection du modèle et du seuil réalisée sur validation uniquement.
- Réentraînement sur train + validation, puis **une seule évaluation** sur test.
- Aucune variable postérieure à la commande (`Days for shipping (real)`, `Delivery Status`, date d'expédition réelle, etc.) utilisée.

## Résultats du test final

| Modèle | ROC-AUC | PR-AUC | Précision | Rappel | F1 | Faux positifs | Faux négatifs |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline mode d'expédition | {fmt(baseline_row["roc_auc"])} | {fmt(baseline_row["pr_auc"])} | {fmt(baseline_row["precision"])} | {fmt(baseline_row["recall"])} | {fmt(baseline_row["f1"])} | {baseline_row["fp"]} | {baseline_row["fn"]} |
| Random Forest | {fmt(rf["roc_auc"])} | {fmt(rf["pr_auc"])} | {fmt(rf["precision"])} | {fmt(rf["recall"])} | {fmt(rf["f1"])} | {rf["fp"]} | {rf["fn"]} |

Le seuil de 40 % est une **hypothèse de décision opérationnelle** et non un optimum financier prouvé. Les résultats par mode d'expédition figurent dans `reports/ml/final_evaluation/final_by_shipping_mode.csv` (sortie locale non versionnée).

## Lecture métier

Le modèle peut servir à **prioriser l'examen** des commandes présentant un risque de retard d'expédition. Une alerte ne prouve pas qu'une action préventive évitera le retard. Le coût des alertes et celui des retards manqués doivent être validés avec un client avant toute décision de déploiement.

## Limites et risques

1. **Cible :** `Late_delivery_risk` n'est pas une preuve de retard de livraison finale.
2. **Dominance du mode d'expédition :** l'importance par permutation sur validation était de 0,2577 de ROC-AUC pour `shipping_mode`, contre 0,0473 pour `order_hour`. Risque de dépendance à une règle structurelle du dataset.
3. **Étiquetage :** commandes annulées ou suspectées de fraude étiquetées sans retard ; définition métier à clarifier.
4. **Transférabilité :** aucun résultat ne prouve une généralisation aux données synthétiques NexaRetail.
5. **ROI :** simulations de coûts d'erreurs, pas économies réalisées ni effet causal démontré.
6. **Validation :** découpage chronologique, mais une seule période de test ; vérifier stabilité, calibration, dérive et équité avant production.

## Recommandation consultant

**Prototype analytique / démonstration de faisabilité**, non déploiement automatique. Confronter le modèle à une règle simple basée sur le mode d'expédition, mesurer les interventions réelles et leur efficacité, puis piloter un test terrain avant d'annoncer un ROI.

## Reproductibilité

Script : `src/ml/final_evaluation_dataco.py`. Jeu de test identifié par SHA-256 dans `reports/ml/final_evaluation/final_metadata.json` (local). Historique d'expériences MLflow local. Les CSV bruts et les données intermédiaires ne sont pas publiés.
"""
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")
    print("\n=== TEST FINAL — NE PAS OPTIMISER SUR CES RÉSULTATS ===")
    print(results.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print("\n=== RÉSULTATS PAR MODE D'EXPÉDITION ===")
    print(segments.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print(f"\nRapport : {REPORT}\nRésultats locaux : {OUT}")


if __name__ == "__main__":
    main()
