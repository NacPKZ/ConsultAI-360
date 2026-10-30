from pathlib import Path

import numpy as np
import pandas as pd
import yaml


def load_config():
    with Path("config/generation.yaml").open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def generate_products(config):
    rng = np.random.default_rng(config["generation"]["seed"] + 3)
    n_products = config["volumes"]["products"]

    catalog = {
        "Électronique": {
            "weight": 0.25,
            "subcategories": ["Audio", "Informatique", "Téléphonie", "Accessoires"],
            "price_range": (15, 1500),
        },
        "Maison": {
            "weight": 0.20,
            "subcategories": ["Cuisine", "Décoration", "Mobilier", "Rangement"],
            "price_range": (8, 800),
        },
        "Mode": {
            "weight": 0.20,
            "subcategories": ["Vêtements", "Chaussures", "Sacs", "Accessoires"],
            "price_range": (10, 350),
        },
        "Beauté": {
            "weight": 0.15,
            "subcategories": ["Soins", "Parfums", "Maquillage", "Hygiène"],
            "price_range": (5, 200),
        },
        "Sport": {
            "weight": 0.12,
            "subcategories": ["Fitness", "Running", "Outdoor", "Équipement"],
            "price_range": (10, 900),
        },
        "Loisirs": {
            "weight": 0.08,
            "subcategories": ["Jeux", "Livres", "Créativité", "Multimédia"],
            "price_range": (5, 300),
        },
    }

    brands = [
        "Nexa Essentials",
        "Velora",
        "Orvian",
        "Lumera",
        "Altis",
        "Novexa",
        "Kivora",
        "Solven",
    ]

    categories = list(catalog)
    weights = [catalog[c]["weight"] for c in categories]

    records = []

    for i in range(n_products):
        category = rng.choice(categories, p=weights)
        details = catalog[category]

        subcategory = rng.choice(details["subcategories"])
        brand = rng.choice(brands)

        min_price, max_price = details["price_range"]

        # Distribution asymétrique : beaucoup de produits
        # accessibles et moins de produits très coûteux.
        price_factor = rng.beta(1.4, 4.0)

        base_price = round(min_price + price_factor * (max_price - min_price), 2)

        # Coût d'achat compris entre 45 % et 85 % du prix.
        cost_ratio = rng.uniform(0.45, 0.85)
        unit_cost = round(base_price * cost_ratio, 2)

        records.append(
            {
                "product_id": f"PRD{i + 1:05d}",
                "product_name": f"{subcategory} {brand} {i + 1:05d}",
                "category": category,
                "subcategory": subcategory,
                "brand": brand,
                "base_price": base_price,
                "unit_cost": unit_cost,
            }
        )

    products = pd.DataFrame(records)

    if len(products) != n_products:
        raise ValueError("Nombre de produits incorrect")

    if products["product_id"].duplicated().any():
        raise ValueError("Identifiants produits dupliqués")

    if products.isna().any().any():
        raise ValueError("Valeurs manquantes détectées")

    if (products["base_price"] <= 0).any():
        raise ValueError("Prix de vente invalide")

    if (products["unit_cost"] < 0).any():
        raise ValueError("Coût négatif détecté")

    if (products["unit_cost"] >= products["base_price"]).any():
        raise ValueError("Coût supérieur ou égal au prix de vente")

    return products


def main():
    config = load_config()
    products = generate_products(config)

    output_dir = Path(config["output"]["directory"])
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "products.csv"

    products.to_csv(
        output_path,
        index=False,
        encoding=config["output"]["encoding"],
    )

    print("\nCONSULTAI 360 — PRODUCTS GENERATION")
    print("-" * 45)

    print(f"Produits générés : {len(products):,}")
    print(f"Catégories : {products['category'].nunique()}")
    print(f"Prix moyen : {products['base_price'].mean():.2f} €")

    products["unit_margin"] = products["base_price"] - products["unit_cost"]

    print(f"Marge brute unitaire moyenne : {products['unit_margin'].mean():.2f} €")

    print("\nRépartition des catégories :")
    print(products["category"].value_counts().to_string())

    print(f"\nFichier créé : {output_path}")

    print("\nAPERÇU :")
    print(products.head().to_string(index=False))


if __name__ == "__main__":
    main()
