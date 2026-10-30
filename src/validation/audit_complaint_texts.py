import re
from pathlib import Path

import pandas as pd

# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUTPUT = ROOT / "reports" / "enrichment"

OUTPUT.mkdir(parents=True, exist_ok=True)

SEED = 20261030


# ============================================================
# 1. CHARGEMENT
# ============================================================

complaints = pd.read_csv(RAW / "complaints.csv")
items = pd.read_csv(RAW / "order_items.csv", usecols=["order_id", "product_id"])
products = pd.read_csv(
    RAW / "products.csv",
    usecols=["product_id", "product_name", "category", "subcategory"],
)

text_df = complaints[complaints["complaint_text"].notna()].copy()

print("\nAUDIT DES COMMENTAIRES")
print("=" * 60)


# ============================================================
# 2. CONTROLES AUTOMATIQUES
# ============================================================

total = len(complaints)
with_text = len(text_df)

duplicate_count = int(text_df["complaint_text"].duplicated().sum())

invalid_ratings = int((~text_df["review_rating"].isin([1, 2])).sum())

invalid_languages = int((text_df["text_language"] != "fr").sum())

missing_source = int(text_df["text_source"].isna().sum())

missing_method = int(text_df["text_match_method"].isna().sum())

empty_texts = int(text_df["complaint_text"].astype(str).str.strip().eq("").sum())

# Vérifier les champs associés aux lignes sans texte.
without_text = complaints[complaints["complaint_text"].isna()]

orphan_metadata = int(
    without_text[
        [
            "review_rating",
            "text_language",
            "text_source",
            "text_match_method",
            "text_match_confidence",
        ]
    ]
    .notna()
    .any(axis=1)
    .sum()
)

print(f"Réclamations totales : {total:,}")
print(f"Textes présents : {with_text:,}")
print(f"Textes absents structurels : {total - with_text:,}")
print(f"Taux de couverture : {with_text / total * 100:.2f} %")

print(f"\nTextes dupliqués : {duplicate_count}")
print(f"Notes invalides : {invalid_ratings}")
print(f"Langues invalides : {invalid_languages}")
print(f"Sources manquantes : {missing_source}")
print(f"Méthodes manquantes : {missing_method}")
print(f"Textes vides : {empty_texts}")
print(f"Métadonnées sans texte : {orphan_metadata}")


# ============================================================
# 3. DETECTION DES TEXTES SUSPECTS
# ============================================================

brand_pattern = (
    r"\b(?:Amazon|Prime|Wiko|Xiaomi|Samsung|Apple|"
    r"AliExpress|Cdiscount|Fnac|Temu|Mi Home)\b"
)

email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"

phone_pattern = r"(?<!\d)(?:\+33|0)[1-9](?:[\s.\-]?\d{2}){4}(?!\d)"

brand_mask = text_df["complaint_text"].str.contains(
    brand_pattern, flags=re.IGNORECASE, regex=True, na=False
)

email_mask = text_df["complaint_text"].str.contains(email_pattern, regex=True, na=False)

phone_mask = text_df["complaint_text"].str.contains(phone_pattern, regex=True, na=False)

suspect_mask = brand_mask | email_mask | phone_mask

print("\nTEXTES SUSPECTS")
print("=" * 60)
print(f"Marques externes détectées : {int(brand_mask.sum())}")
print(f"E-mails potentiels : {int(email_mask.sum())}")
print(f"Téléphones potentiels : {int(phone_mask.sum())}")
print(f"Textes suspects distincts : {int(suspect_mask.sum())}")


# ============================================================
# 4. COHERENCE AVEC LES PRODUITS COMMANDES
# ============================================================

order_products = items.merge(
    products, on="product_id", how="left", validate="many_to_one"
)

if order_products["category"].isna().any():
    raise ValueError("Certains produits commandés n'ont pas de catégorie.")

order_products["product_description"] = (
    order_products["product_name"].astype(str)
    + " ["
    + order_products["category"].astype(str)
    + " / "
    + order_products["subcategory"].astype(str)
    + "]"
)

order_summary = (
    order_products.groupby("order_id")
    .agg(
        products_ordered=(
            "product_description",
            lambda values: " | ".join(sorted(set(values))),
        ),
        product_categories=("category", lambda values: " | ".join(sorted(set(values)))),
    )
    .reset_index()
)


# ============================================================
# 5. ECHANTILLON POUR CONTROLE MANUEL
# ============================================================

samples = []

for reason, group in text_df.groupby("complaint_reason"):
    sample_size = min(20, len(group))

    sample = group.sample(n=sample_size, random_state=SEED)

    samples.append(sample)

audit_sample = pd.concat(samples, ignore_index=True)

audit_sample = audit_sample.merge(
    order_summary, on="order_id", how="left", validate="many_to_one"
)

audit_sample["verdict"] = ""
audit_sample["error_reason"] = ""

columns = [
    "complaint_id",
    "order_id",
    "complaint_reason",
    "complaint_text",
    "review_rating",
    "text_match_method",
    "products_ordered",
    "product_categories",
    "verdict",
    "error_reason",
]

sample_path = OUTPUT / "manual_review_sample.csv"

audit_sample[columns].to_csv(sample_path, index=False, encoding="utf-8-sig")


# ============================================================
# 6. EXPORT DES TEXTES SUSPECTS
# ============================================================

suspect_path = OUTPUT / "suspect_texts.csv"

text_df.loc[suspect_mask].to_csv(suspect_path, index=False, encoding="utf-8-sig")


# ============================================================
# 7. RESULTAT
# ============================================================

print("\nECHANTILLON MANUEL")
print("=" * 60)

print(f"Textes sélectionnés : {len(audit_sample)}")

print("\nRépartition :")

print(audit_sample["complaint_reason"].value_counts().to_string())

print("\nFICHIERS GENERES")
print(sample_path)
print(suspect_path)

print("\nAUDIT TEXTUEL TERMINE")
