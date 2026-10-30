from pathlib import Path

import numpy as np
import pandas as pd
import yaml


def load_config():
    with Path("config/generation.yaml").open(
        "r", encoding="utf-8"
    ) as file:
        return yaml.safe_load(file)


def generate_employees(config):
    seed = config["generation"]["seed"]
    rng = np.random.default_rng(seed + 2)

    stores_path = Path(config["output"]["directory"]) / "stores.csv"

    if not stores_path.exists():
        raise FileNotFoundError(
            "stores.csv introuvable. Génère d'abord les magasins."
        )

    stores = pd.read_csv(stores_path)

    expected_stores = config["volumes"]["stores"]

    if len(stores) != expected_stores:
        raise ValueError("Nombre de magasins incorrect")

    if stores["store_id"].duplicated().any():
        raise ValueError("Identifiants de magasins dupliqués")

    total_employees = config["volumes"]["employees"]

    headquarters_count = 30
    store_employees_count = total_employees - headquarters_count

    minimum_per_store = 5

    minimum_required = len(stores) * minimum_per_store

    if store_employees_count < minimum_required:
        raise ValueError(
            "Effectif insuffisant pour garantir le minimum par magasin"
        )

    remaining_employees = store_employees_count - minimum_required

    store_weights = (
        stores["store_size_m2"].to_numpy(dtype=float)
    )

    store_weights = store_weights / store_weights.sum()

    additional_employees = rng.multinomial(
        remaining_employees,
        store_weights
    )

    employees_per_store = (
        additional_employees + minimum_per_store
    )

    store_departments = {
        "Vente": [
            "Conseiller de vente",
            "Responsable de rayon"
        ],
        "Caisse": [
            "Hôte de caisse",
            "Responsable caisse"
        ],
        "Logistique": [
            "Magasinier",
            "Responsable stock"
        ],
        "Management": [
            "Directeur de magasin",
            "Directeur adjoint"
        ]
    }

    headquarters_departments = {
        "Data & IT": [
            "Data Analyst",
            "Data Engineer",
            "Responsable SI"
        ],
        "Finance": [
            "Contrôleur de gestion",
            "Comptable"
        ],
        "Marketing": [
            "Chargé marketing",
            "Responsable CRM"
        ],
        "RH": [
            "Chargé RH",
            "Responsable RH"
        ],
        "Direction": [
            "Directeur des opérations",
            "Responsable stratégie"
        ]
    }

    records = []
    employee_number = 1

    simulation_end = pd.Timestamp(
        config["generation"]["end_date"]
    )

    for store, count in zip(
        stores.to_dict("records"),
        employees_per_store
    ):
        opening_date = pd.Timestamp(store["opening_date"])

        for index in range(int(count)):

            if index == 0:
                department = "Management"
                job_title = "Directeur de magasin"
            else:
                department = rng.choice(
                    ["Vente", "Caisse", "Logistique", "Management"],
                    p=[0.50, 0.25, 0.20, 0.05]
                )

                job_title = rng.choice(
                    store_departments[department]
                )

            max_days = (
                simulation_end - opening_date
            ).days

            if max_days < 0:
                raise ValueError(
                    "Un magasin ouvre après la fin de la simulation"
                )

            hire_date = opening_date + pd.Timedelta(
                days=int(rng.integers(0, max_days + 1))
            )

            records.append({
                "employee_id": f"EMP{employee_number:04d}",
                "store_id": store["store_id"],
                "department": department,
                "job_title": job_title,
                "hire_date": hire_date.date()
            })

            employee_number += 1

    headquarters_start = pd.Timestamp("2015-01-01")

    for _ in range(headquarters_count):

        department = rng.choice(
            list(headquarters_departments.keys())
        )

        job_title = rng.choice(
            headquarters_departments[department]
        )

        max_days = (
            simulation_end - headquarters_start
        ).days

        hire_date = headquarters_start + pd.Timedelta(
            days=int(rng.integers(0, max_days + 1))
        )

        records.append({
            "employee_id": f"EMP{employee_number:04d}",
            "store_id": None,
            "department": department,
            "job_title": job_title,
            "hire_date": hire_date.date()
        })

        employee_number += 1

    employees = pd.DataFrame(records)

    if len(employees) != total_employees:
        raise ValueError("Nombre total d'employés incorrect")

    if employees["employee_id"].duplicated().any():
        raise ValueError("Identifiants employés dupliqués")

    valid_store_ids = set(stores["store_id"])

    assigned_store_ids = set(
        employees["store_id"].dropna()
    )

    if not assigned_store_ids.issubset(valid_store_ids):
        raise ValueError("Référence à un magasin inexistant")

    return employees


def main():
    config = load_config()

    employees = generate_employees(config)

    output_dir = Path(config["output"]["directory"])
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "employees.csv"

    employees.to_csv(
        output_path,
        index=False,
        encoding=config["output"]["encoding"]
    )

    headquarters_count = employees["store_id"].isna().sum()

    print("\nCONSULTAI 360 — EMPLOYEES GENERATION")
    print("-" * 45)

    print(f"Employés générés : {len(employees)}")
    print(f"Employés au siège : {headquarters_count}")
    print(
        f"Employés en magasin : "
        f"{len(employees) - headquarters_count}"
    )

    print("\nRépartition par département :")
    print(
        employees["department"]
        .value_counts()
        .to_string()
    )

    print("\nEffectifs par magasin :")
    print(
        employees["store_id"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print(f"\nFichier créé : {output_path}")

    print("\nAPERÇU :")
    print(employees.head().to_string(index=False))


if __name__ == "__main__":
    main()
