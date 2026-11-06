from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

DATA_PATH = ROOT / "data" / "external" / "dataco" / "DataCoSupplyChainDataset.csv"

if not DATA_PATH.exists():
    raise FileNotFoundError(f"Dataset introuvable : {DATA_PATH}")

df = pd.read_csv(
    DATA_PATH,
    encoding="latin-1",
    low_memory=False,
)

print("\n=== DIMENSIONS ===")
print("Lignes :", len(df))
print("Colonnes :", len(df.columns))

print("\n=== COLONNES ===")
print(df.columns.tolist())

print("\n=== VALEURS MANQUANTES ===")
print(df.isna().sum().sort_values(ascending=False).head(15))

print("\n=== DOUBLONS EXACTS ===")
print(df.duplicated().sum())

print("\n=== VARIABLE CIBLE ===")
target = "Late_delivery_risk"

if target not in df.columns:
    raise ValueError("Variable cible introuvable")

print(df[target].value_counts(dropna=False))
print(df[target].value_counts(normalize=True, dropna=False).mul(100).round(2))

print("\n=== COLONNES À RISQUE DE FUITE ===")
leakage_candidates = [
    "Delivery Status",
    "Days for shipping (real)",
    "shipping date (DateOrders)",
]

for column in leakage_candidates:
    print(column, ":", column in df.columns)

print("\nAUDIT INITIAL TERMINÉ")
