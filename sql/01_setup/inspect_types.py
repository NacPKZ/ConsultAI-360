from pathlib import Path
import csv

base = Path("data/raw")

tables = [
    "customers", "products", "stores",
    "employees", "orders", "order_items",
    "payments", "shipments", "inventory",
    "complaints"
]

print("\nCONSULTAI 360 — INSPECTION DES TYPES")
print("=" * 80)

for table in tables:
    path = base / f"{table}.csv"

    print(f"\n### {table.upper()}")

    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        rows = []
        for _, row in zip(range(3), reader):
            rows.append(row)

        for column in reader.fieldnames or []:
            examples = [row.get(column, "") for row in rows]

            print(
                f"{column:25} | "
                f"{str(examples)[:100]}"
            )

print("\nINSPECTION TERMINEE")
