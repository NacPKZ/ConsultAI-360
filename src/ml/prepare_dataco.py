from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "reports/ml/dataco_orders_audit.csv"
OUTPUT = ROOT / "reports/ml/processed"

OUTPUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(INPUT, parse_dates=["order_date"])

# Vérifications de sécurité
assert df["Order Id"].is_unique, "Commandes dupliquées"
assert df["late"].isin([0, 1]).all(), "Cible invalide"
assert df["order_date"].notna().all(), "Dates manquantes"
assert df["split"].isin(["train", "validation", "test"]).all(), "Split invalide"

# Variables calendaires connues à la commande
df["order_month"] = df["order_date"].dt.month
df["order_weekday"] = df["order_date"].dt.dayofweek
df["order_hour"] = df["order_date"].dt.hour
df["order_weekend"] = (df["order_weekday"] >= 5).astype(int)

# Variables retenues pour le modèle
features = [
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

categorical_features = [
    "shipping_mode",
    "market",
    "region",
]

numeric_features = [column for column in features if column not in categorical_features]

# Vérification des variables interdites
forbidden = {
    "late",
    "order_status",
    "scheduled_days",
    "Delivery Status",
    "Days for shipping (real)",
    "shipping date (DateOrders)",
    "Order Id",
}

assert not forbidden.intersection(features)

# Vérifier les données utilisées
print("\n=== VALEURS MANQUANTES ===")
print(df[features].isna().sum())

print("\n=== VALEURS NUMÉRIQUES ===")
print(df[numeric_features].describe().round(2))

print("\n=== CATÉGORIES ===")
for column in categorical_features:
    print(column, ":", df[column].nunique(), "modalités")

# Contrôle des ensembles
ids = {
    name: set(df.loc[df["split"] == name, "Order Id"])
    for name in ["train", "validation", "test"]
}

assert ids["train"].isdisjoint(ids["validation"])
assert ids["train"].isdisjoint(ids["test"])
assert ids["validation"].isdisjoint(ids["test"])

# Les ensembles doivent rester chronologiques
train_max = df.loc[df["split"] == "train", "order_date"].max()

validation_min = df.loc[df["split"] == "validation", "order_date"].min()

validation_max = df.loc[df["split"] == "validation", "order_date"].max()

test_min = df.loc[df["split"] == "test", "order_date"].min()

assert train_max < validation_min
assert validation_max < test_min

# Exports séparés : variables + cible
for split in ["train", "validation", "test"]:
    subset = df.loc[df["split"] == split]

    result = subset[features + ["late"]].copy()

    result.to_csv(
        OUTPUT / f"{split}.csv",
        index=False,
    )

    print(f"{split}: {len(result):,} commandes, {result['late'].mean():.2%} de retards")

# Liste des variables autorisées
pd.Series(features, name="feature").to_csv(
    OUTPUT / "feature_list.csv",
    index=False,
)

print("\nPRÉPARATION 7.3 TERMINÉE")
