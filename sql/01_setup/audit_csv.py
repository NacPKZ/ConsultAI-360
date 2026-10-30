from pathlib import Path
import csv

BASE = Path("data")

tables = [
    "customers",
    "products",
    "stores",
    "employees",
    "orders",
    "order_items",
    "payments",
    "shipments",
    "inventory",
    "complaints"
]

folders = [
    "raw",
    "corrupted/low",
    "corrupted/medium",
    "corrupted/critical",
    "processed/medium",
    "processed_v2/low",
    "processed_v2/medium",
    "processed_v2/critical"
]

print("\n" + "=" * 90)
print("CONSULTAI 360 — AUDIT STRUCTUREL CSV")
print("=" * 90)

for folder in folders:

    print(f"\n### {folder.upper()}")

    for table in tables:

        path = BASE / folder / f"{table}.csv"

        if not path.exists():
            print(f"{table:15} | FICHIER ABSENT")
            continue

        try:
            with path.open(
                "r",
                encoding="utf-8-sig",
                newline=""
            ) as f:

                reader = csv.reader(f)

                header = next(reader, None)

                if header is None:
                    print(f"{table:15} | FICHIER VIDE")
                    continue

                rows = sum(1 for _ in reader)

                print(
                    f"{table:15} | "
                    f"{rows:>9,} lignes | "
                    f"{len(header):>2} colonnes"
                )

                if folder == "raw":
                    print(f"    Colonnes : {', '.join(header)}")

        except Exception as e:
            print(f"{table:15} | ERREUR : {e}")

print("\nAUDIT TERMINE")
