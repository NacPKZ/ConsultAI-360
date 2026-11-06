from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/external/dataco/DataCoSupplyChainDataset.csv"
OUTPUT = ROOT / "reports/ml"
OUTPUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA, encoding="latin-1", low_memory=False)

# 1. Vérifier le grain des données
print("\n=== GRAIN ===")
print("Lignes :", len(df))
print("Commandes uniques :", df["Order Id"].nunique())
print("Articles uniques :", df["Order Item Id"].nunique())
print("Doublons exacts :", df.duplicated().sum())

# 2. Vérifier la cohérence de la cible par commande
target_counts = df.groupby("Order Id")["Late_delivery_risk"].nunique()
inconsistent = (target_counts > 1).sum()
print("Commandes avec cible incohérente :", inconsistent)

if inconsistent:
    raise ValueError("Cibles contradictoires dans une commande")

# 3. Vérifier les autres attributs de commande
order_columns = [
    "order date (DateOrders)",
    "Shipping Mode",
    "Days for shipment (scheduled)",
    "Order Status",
]

for col in order_columns:
    n = (df.groupby("Order Id")[col].nunique(dropna=False) > 1).sum()
    print(f"Incohérences {col} : {n}")
    if n:
        raise ValueError(f"Valeurs contradictoires : {col}")

# 4. Construire une table au niveau commande
orders = df.groupby("Order Id", as_index=False).agg(
    order_date=("order date (DateOrders)", "first"),
    late=("Late_delivery_risk", "first"),
    shipping_mode=("Shipping Mode", "first"),
    scheduled_days=("Days for shipment (scheduled)", "first"),
    order_status=("Order Status", "first"),
    market=("Market", "first"),
    region=("Order Region", "first"),
    n_items=("Order Item Id", "count"),
    total_quantity=("Order Item Quantity", "sum"),
    total_sales=("Order Item Total", "sum"),
)

orders["order_date"] = pd.to_datetime(
    orders["order_date"],
    format="%m/%d/%Y %H:%M",
    errors="raise",
)

orders = orders.sort_values(["order_date", "Order Id"]).reset_index(drop=True)

# 5. Audit de la cible et des annulations
print("\n=== CIBLE PAR COMMANDE ===")
print(orders["late"].value_counts())
print(orders["late"].value_counts(normalize=True).round(4))

print("\n=== STATUTS ===")
print(pd.crosstab(orders["order_status"], orders["late"]))

print("\n=== MODES D'EXPÉDITION ===")
print(
    pd.crosstab(
        orders["shipping_mode"],
        orders["late"],
        normalize="index",
    ).round(3)
)

# 6. Découpage chronologique indicatif 70/15/15
n = len(orders)
train_end = int(n * 0.70)
valid_end = int(n * 0.85)

orders["split"] = "test"
orders.loc[: train_end - 1, "split"] = "train"
orders.loc[train_end : valid_end - 1, "split"] = "validation"

print("\n=== DÉCOUPAGE CHRONOLOGIQUE ===")
print(
    orders.groupby("split").agg(
        n_orders=("Order Id", "count"),
        first_date=("order_date", "min"),
        last_date=("order_date", "max"),
        late_rate=("late", "mean"),
    )
)

# 7. Contrôler les chevauchements temporels
train_max = orders.loc[orders["split"] == "train", "order_date"].max()
valid_min = orders.loc[orders["split"] == "validation", "order_date"].min()
valid_max = orders.loc[orders["split"] == "validation", "order_date"].max()
test_min = orders.loc[orders["split"] == "test", "order_date"].min()

assert train_max <= valid_min
assert valid_max <= test_min

# 8. Export de l'audit
orders.to_csv(OUTPUT / "dataco_orders_audit.csv", index=False)

print("\nAUDIT 7.2 TERMINÉ")
