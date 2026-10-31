import csv
import getpass
import os
from pathlib import Path

import psycopg
from psycopg import sql

# =====================================================
# CONFIGURATION
# =====================================================

BASE = Path("data/processed_v2")

SCENARIOS = ["low", "medium", "critical"]

TABLES = [
    "customers",
    "products",
    "stores",
    "employees",
    "orders",
    "order_items",
    "payments",
    "shipments",
    "inventory",
    "complaints",
]

password = os.getenv("PGPASSWORD") or getpass.getpass("Mot de passe PostgreSQL : ")


# =====================================================
# CONNEXION POSTGRESQL
# =====================================================

connection = psycopg.connect(
    host="localhost",
    port=5432,
    dbname="nexaretail_db",
    user="postgres",
    password=password,
)

print("\nCONSULTAI 360 — IMPORTATION CLEAN")
print("=" * 60)


# =====================================================
# IMPORTATION
# =====================================================

try:
    with connection:
        for scenario in SCENARIOS:
            print(f"\nSCENARIO : {scenario.upper()}")

            # Transaction : tout le scenario réussit
            # ou ses modifications sont annulées.
            with connection.transaction():
                for table in TABLES:
                    path = BASE / scenario / f"{table}.csv"

                    if not path.exists():
                        raise FileNotFoundError(path)

                    with path.open(encoding="utf-8-sig", newline="") as file:
                        reader = csv.reader(file)
                        columns = next(reader)

                        with connection.cursor() as cursor:
                            # Vérifier les colonnes PostgreSQL
                            cursor.execute(
                                """
                                SELECT column_name
                                FROM information_schema.columns
                                WHERE table_schema = 'clean'
                                  AND table_name = %s
                                  AND column_name NOT IN (
                                      'clean_id',
                                      'scenario',
                                      'source_file',
                                      'source_row_number'
                                  )
                                ORDER BY ordinal_position
                                """,
                                (table,),
                            )

                            db_columns = [row[0] for row in cursor.fetchall()]

                            if columns != db_columns:
                                raise ValueError(f"Structure incompatible : {path}")

                            # Supprimer uniquement l'ancienne
                            # version du scénario concerné.
                            cursor.execute(
                                sql.SQL("DELETE FROM {} WHERE scenario = %s").format(
                                    sql.Identifier("clean", table)
                                ),
                                (scenario,),
                            )

                            copy_columns = [
                                "scenario",
                                "source_file",
                                "source_row_number",
                                *columns,
                            ]

                            copy_query = sql.SQL("COPY {} ({}) FROM STDIN").format(
                                sql.Identifier("clean", table),
                                sql.SQL(", ").join(map(sql.Identifier, copy_columns)),
                            )

                            count = 0

                            with cursor.copy(copy_query) as copy:
                                for row_number, row in enumerate(reader, start=2):
                                    if len(row) != len(columns):
                                        raise ValueError(
                                            f"Ligne invalide : {path}:{row_number}"
                                        )

                                    # Convertir les champs vides
                                    # en valeurs SQL NULL.
                                    values = [
                                        scenario,
                                        str(path),
                                        row_number,
                                        *[
                                            None if value == "" else value
                                            for value in row
                                        ],
                                    ]

                                    copy.write_row(values)
                                    count += 1

                            # Contrôle du volume importé
                            cursor.execute(
                                sql.SQL(
                                    "SELECT COUNT(*) FROM {} WHERE scenario = %s"
                                ).format(sql.Identifier("clean", table)),
                                (scenario,),
                            )

                            result = cursor.fetchone()

                            if result is None:
                                raise RuntimeError(
                                    f"Aucun résultat SQL pour la table {table}"
                                )
                            imported = result[0]

                            if imported != count:
                                raise ValueError(f"Volume incorrect : {table}")

                            print(f"{table:15} | {imported:>9,} lignes")

            print(f"SCENARIO {scenario.upper()} VALIDE")

    print("\nIMPORTATION CLEAN TERMINEE")

except Exception as error:
    print(f"\nERREUR : {error}")
    raise

finally:
    connection.close()
