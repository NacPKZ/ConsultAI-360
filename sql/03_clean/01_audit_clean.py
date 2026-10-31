from pathlib import Path
import csv

SCENARIOS = ["low", "medium", "critical"]

TABLES = [
    "customers", "products", "stores",
    "employees", "orders", "order_items",
    "payments", "shipments", "inventory",
    "complaints"
]

reference = Path("data/raw")

print("\nCONSULTAI 360 — AUDIT STRUCTURE CLEAN")
print("=" * 65)

for table in TABLES:

    with (reference / f"{table}.csv").open(
        encoding="utf-8-sig", newline=""
    ) as f:
        raw_columns = next(csv.reader(f))

    print(f"\n{table.upper()}")

    for scenario in SCENARIOS:

        path = Path("data/processed_v2") / scenario / f"{table}.csv"

        if not path.exists():
            print(f"  {scenario}: FICHIER ABSENT")
            continue

        with path.open(encoding="utf-8-sig", newline="") as f:
            clean_columns = next(csv.reader(f))

        if clean_columns == raw_columns:
            status = "OK"
        else:
            status = "COLONNES DIFFERENTES"

        print(
            f"  {scenario:8} | "
            f"{len(clean_columns):2} colonnes | {status}"
        )

        if status != "OK":
            print(f"    RAW   : {raw_columns}")
            print(f"    CLEAN : {clean_columns}")

print("\nAUDIT TERMINE")
