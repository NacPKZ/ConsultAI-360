from pathlib import Path

import numpy as np
import pandas as pd
import yaml


def load_config():
    config_path = Path("config/generation.yaml")

    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def generate_stores(config):
    seed = config["generation"]["seed"]
    rng = np.random.default_rng(seed)

    locations = {
        "Île-de-France": [
            "Paris",
            "Paris",
            "Paris",
            "Boulogne-Billancourt",
            "Saint-Denis",
            "Créteil",
            "Versailles",
            "Nanterre",
            "Montreuil",
        ],
        "Auvergne-Rhône-Alpes": [
            "Lyon",
            "Lyon",
            "Grenoble",
            "Annecy",
            "Clermont-Ferrand",
        ],
        "Provence-Alpes-Côte d'Azur": [
            "Marseille",
            "Marseille",
            "Nice",
            "Aix-en-Provence",
        ],
        "Occitanie": ["Toulouse", "Toulouse", "Montpellier", "Nîmes"],
        "Nouvelle-Aquitaine": ["Bordeaux", "Bordeaux", "Limoges"],
        "Hauts-de-France": ["Lille", "Lille", "Amiens"],
        "Bretagne": ["Rennes", "Brest"],
        "Pays de la Loire": ["Nantes", "Angers"],
        "Grand Est": ["Strasbourg", "Reims"],
        "Normandie": ["Rouen"],
    }

    records = []
    store_number = 1

    for region, cities in locations.items():
        for city in cities:
            opening_date = pd.Timestamp("2010-01-01") + pd.Timedelta(
                days=int(rng.integers(0, 5000))
            )

            store_size = int(rng.integers(250, 2501))

            records.append(
                {
                    "store_id": f"STR{store_number:03d}",
                    "store_name": f"NexaRetail {city} {store_number:03d}",
                    "city": city,
                    "region": region,
                    "opening_date": opening_date.date(),
                    "store_size_m2": store_size,
                }
            )

            store_number += 1

    stores = pd.DataFrame(records)

    expected = config["volumes"]["stores"]

    if len(stores) != expected:
        raise ValueError(
            f"Nombre de magasins incorrect : {len(stores)} au lieu de {expected}"
        )

    if stores["store_id"].duplicated().any():
        raise ValueError("Identifiants de magasins dupliqués")

    return stores


def main():
    config = load_config()

    stores = generate_stores(config)

    output_dir = Path(config["output"]["directory"])
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "stores.csv"

    stores.to_csv(output_path, index=False, encoding=config["output"]["encoding"])

    print("\nCONSULTAI 360 — STORES GENERATION")
    print("-" * 45)

    print(f"Magasins générés : {len(stores)}")
    print(f"Régions : {stores['region'].nunique()}")
    print(f"Surface moyenne : {stores['store_size_m2'].mean():.0f} m²")

    print("\nRépartition géographique :")
    print(stores["region"].value_counts().to_string())

    print(f"\nFichier créé : {output_path}")

    print("\nAPERÇU :")
    print(stores.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
