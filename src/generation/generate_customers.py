from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from faker import Faker


def load_config():
    with Path("config/generation.yaml").open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def generate_customers(config):
    seed = config["generation"]["seed"]
    rng = np.random.default_rng(seed + 1)

    fake = Faker(config["generation"]["locale"])
    Faker.seed(seed + 1)

    n_customers = config["volumes"]["customers"]

    locations = {
        "Île-de-France": ["Paris", "Créteil", "Versailles", "Nanterre"],
        "Auvergne-Rhône-Alpes": ["Lyon", "Grenoble", "Annecy"],
        "Provence-Alpes-Côte d'Azur": ["Marseille", "Nice", "Toulon"],
        "Occitanie": ["Toulouse", "Montpellier", "Nîmes"],
        "Nouvelle-Aquitaine": ["Bordeaux", "Limoges", "Poitiers"],
        "Hauts-de-France": ["Lille", "Amiens", "Arras"],
        "Bretagne": ["Rennes", "Brest", "Vannes"],
        "Pays de la Loire": ["Nantes", "Angers", "Le Mans"],
        "Grand Est": ["Strasbourg", "Reims", "Metz"],
        "Normandie": ["Rouen", "Caen", "Le Havre"],
    }

    regions = list(locations.keys())

    region_weights = np.array(
        [0.25, 0.13, 0.11, 0.10, 0.09, 0.09, 0.07, 0.06, 0.06, 0.04]
    )

    loyalty_tiers = config["business"]["loyalty_tiers"]
    loyalty_weights = [0.65, 0.20, 0.11, 0.04]

    start_date = pd.Timestamp("2018-01-01")
    end_date = pd.Timestamp(config["generation"]["end_date"])

    max_days = (end_date - start_date).days

    records = []

    for i in range(n_customers):
        region = rng.choice(regions, p=region_weights)
        city = rng.choice(locations[region])

        registration_date = start_date + pd.Timedelta(
            days=int(rng.integers(0, max_days + 1))
        )

        records.append(
            {
                "customer_id": f"CUS{i + 1:06d}",
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "city": city,
                "region": region,
                "registration_date": registration_date.date(),
                "loyalty_tier": rng.choice(loyalty_tiers, p=loyalty_weights),
            }
        )

    customers = pd.DataFrame(records)

    if len(customers) != n_customers:
        raise ValueError("Nombre de clients incorrect")

    if customers["customer_id"].duplicated().any():
        raise ValueError("Identifiants clients dupliqués")

    if customers.isna().any().any():
        raise ValueError("Valeurs manquantes détectées")

    return customers


def main():
    config = load_config()

    customers = generate_customers(config)

    output_dir = Path(config["output"]["directory"])
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "customers.csv"

    customers.to_csv(output_path, index=False, encoding=config["output"]["encoding"])

    print("\nCONSULTAI 360 — CUSTOMERS GENERATION")
    print("-" * 45)

    print(f"Clients générés : {len(customers):,}")
    print(f"Régions : {customers['region'].nunique()}")

    print("\nRépartition des niveaux de fidélité :")
    print(
        customers["loyalty_tier"]
        .value_counts(normalize=True)
        .mul(100)
        .round(2)
        .to_string()
    )

    print("\nRépartition géographique :")
    print(customers["region"].value_counts().to_string())

    print(f"\nFichier créé : {output_path}")
    print("\nAPERÇU :")
    print(customers.head().to_string(index=False))


if __name__ == "__main__":
    main()
