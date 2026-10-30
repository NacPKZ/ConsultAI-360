from pathlib import Path
import csv

BASE = Path("data/raw")
OUTPUT = Path("sql/02_raw/01_create_raw_tables.sql")

tables = [
    "customers", "products", "stores",
    "employees", "orders", "order_items",
    "payments", "shipments", "inventory",
    "complaints"
]

sql = [
    "-- CONSULTAI 360 - PHASE 4.2",
    "-- Creation des tables RAW",
    "-- Colonnes metier conservees en TEXT",
    "",
    "CREATE SCHEMA IF NOT EXISTS raw;",
    ""
]

for table in tables:
    path = BASE / f"{table}.csv"

    with path.open(encoding="utf-8-sig", newline="") as f:
        columns = next(csv.reader(f))

    # Verification des noms de colonnes
    if len(columns) != len(set(columns)):
        raise ValueError(f"Colonnes dupliquees : {table}")

    if not all(
        col.isidentifier() and col.islower()
        for col in columns
    ):
        raise ValueError(f"Nom de colonne invalide : {table}")

    definitions = [
        "    raw_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY",
        "    scenario TEXT NOT NULL",
        "    source_file TEXT NOT NULL",
        "    source_row_number BIGINT NOT NULL"
    ]

    definitions += [
        f'    "{column}" TEXT'
        for column in columns
    ]

    statement = (
        f"CREATE TABLE IF NOT EXISTS raw.{table} (\n"
        + ",\n".join(definitions)
        + "\n);"
    )

    sql.append(statement)
    sql.append("")

    print(f"Table preparee : raw.{table}")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("\n".join(sql), encoding="utf-8")

print("\nSCRIPT SQL GENERE")
print(OUTPUT)
