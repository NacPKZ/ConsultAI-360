from pathlib import Path
import csv
import getpass
import os

import psycopg
from psycopg import sql

BASE = Path("data")

SCENARIOS = {
    "original": "raw",
    "low": "corrupted/low",
    "medium": "corrupted/medium",
    "critical": "corrupted/critical",
}

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

password = os.getenv("PGPASSWORD")

if not password:
    password = getpass.getpass("Mot de passe PostgreSQL : ")

connection = psycopg.connect(
    host="localhost",
    port=5432,
    dbname="nexaretail_db",
    user="postgres",
    password=password,
)

print("\nCONSULTAI 360 — IMPORTATION RAW")
print("=" * 60)

try:
    with connection:
        for scenario, folder in SCENARIOS.items():

            print(f"\nSCENARIO : {scenario.upper()}")

            # Une transaction par scenario
            with connection.transaction():

                for table in TABLES:

                    path = BASE / folder / f"{table}.csv"

                    if not path.is_file():
                        raise FileNotFoundError(path)

                    with path.open(
                        encoding="utf-8-sig",
                        newline=""
                    ) as file:

                        reader = csv.reader(file)
                        columns = next(reader)

                        with connection.cursor() as cursor:

                            # Verification de la structure SQL
                            cursor.execute(
                                """
                                SELECT column_name
                                FROM information_schema.columns
                                WHERE table_schema = 'raw'
                                  AND table_name = %s
                                  AND column_name NOT IN (
                                      'raw_id',
                                      'scenario',
                                      'source_file',
                                      'source_row_number'
                                  )
                                ORDER BY ordinal_position
                                """,
                                (table,)
                            )

                            db_columns = [
                                row[0]
                                for row in cursor.fetchall()
                            ]

                            if columns != db_columns:
                                raise ValueError(
                                    f"Colonnes incompatibles : {path}"
                                )

                            # Suppression des anciennes lignes
                            # du scenario uniquement
                            cursor.execute(
                                sql.SQL(
                                    "DELETE FROM {} WHERE scenario = %s"
                                ).format(
                                    sql.Identifier("raw", table)
                                ),
                                (scenario,)
                            )

                            copy_columns = [
                                "scenario",
                                "source_file",
                                "source_row_number",
                                *columns,
                            ]

                            copy_query = sql.SQL(
                                "COPY {} ({}) FROM STDIN"
                            ).format(
                                sql.Identifier("raw", table),
                                sql.SQL(", ").join(
                                    map(sql.Identifier, copy_columns)
                                )
                            )

                            count = 0

                            with cursor.copy(copy_query) as copy:

                                for row_number, row in enumerate(
                                    reader, start=2
                                ):

                                    if len(row) != len(columns):
                                        raise ValueError(
                                            f"Ligne invalide : "
                                            f"{path}:{row_number}"
                                        )

                                    values = [
                                        scenario,
                                        str(path),
                                        row_number,
                                        *row,
                                    ]

                                    copy.write_row(values)
                                    count += 1

                            # Verification apres import
                            cursor.execute(
                                sql.SQL(
                                    "SELECT COUNT(*) FROM {} "
                                    "WHERE scenario = %s"
                                ).format(
                                    sql.Identifier("raw", table)
                                ),
                                (scenario,)
                            )

                            imported = cursor.fetchone()[0]

                            if imported != count:
                                raise ValueError(
                                    f"Volume incorrect : {table}"
                                )

                            print(
                                f"{table:15} | "
                                f"{imported:>9,} lignes"
                            )

            print(f"SCENARIO {scenario.upper()} VALIDE")

    print("\nIMPORTATION TERMINEE")

except Exception as error:
    print(f"\nERREUR : {error}")
    raise

finally:
    connection.close()
