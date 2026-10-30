from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from faker import Faker


def main():
    print("=" * 45)
    print("CONSULTAI 360 - ENVIRONMENT CHECK")
    print("=" * 45)

    config_path = Path("config/generation.yaml")

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration introuvable : {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    seed = config["generation"]["seed"]
    locale = config["generation"]["locale"]

    fake = Faker(locale)
    Faker.seed(seed)

    rng = np.random.default_rng(seed)

    print(f"Entreprise : {config['project']['company']}")
    print(f"Graine aléatoire : {seed}")
    print(f"Langue : {locale}")

    print("\nVolumes prévus :")

    for table, volume in config["volumes"].items():
        print(f"  {table}: {volume:,}")

    print("\nTest Faker :")
    print(fake.name())

    print("\nTest NumPy :")
    print(rng.integers(1, 101, size=5))

    print("\nVersion Pandas :")
    print(pd.__version__)

    print("\nENVIRONNEMENT OPERATIONNEL")


if __name__ == "__main__":
    main()
