import argparse
import json
import shutil
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

# ============================================================
# 1. CONFIGURATION
# ============================================================


def load_config():
    """Charge la configuration YAML du projet."""

    config_path = Path("config/corruption.yaml")

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration introuvable : {config_path}")

    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict):
        raise TypeError("La configuration YAML doit être un dictionnaire.")

    return config


# ============================================================
# 2. CHARGEMENT DES DONNÉES
# ============================================================


def load_raw_data(config):
    """Charge les dix tables originales."""

    raw_path = Path(config["paths"]["raw"])

    if not raw_path.exists():
        raise FileNotFoundError(f"Dossier introuvable : {raw_path}")

    tables = {}

    for csv_file in sorted(raw_path.glob("*.csv")):
        table_name = csv_file.stem
        tables[table_name] = pd.read_csv(csv_file)

        print(f"{table_name} : {len(tables[table_name]):,} lignes")

    if len(tables) != 10:
        raise ValueError(f"10 tables attendues, {len(tables)} trouvées.")

    return tables


# ============================================================
# 3. COPIE DES TABLES
# ============================================================


def copy_tables(tables):
    """Crée des copies indépendantes des DataFrames."""

    return {name: dataframe.copy(deep=True) for name, dataframe in tables.items()}


# ============================================================
# 4. SÉLECTION ALÉATOIRE
# ============================================================


def select_rows(dataframe, rate, rng, eligible_mask=None):
    """Sélectionne des positions éligibles sans remplacement."""

    if not 0 <= rate <= 1:
        raise ValueError("Le taux doit être compris entre 0 et 1.")

    if eligible_mask is None:
        eligible_positions = np.arange(len(dataframe))

    else:
        mask = np.asarray(eligible_mask, dtype=bool)

        if len(mask) != len(dataframe):
            raise ValueError("Le masque doit avoir la taille du DataFrame.")

        eligible_positions = np.flatnonzero(mask)

    number_to_select = round(len(eligible_positions) * rate)

    if number_to_select == 0:
        return np.array([], dtype=int)

    return rng.choice(
        eligible_positions,
        size=number_to_select,
        replace=False,
    )


# ============================================================
# 5. JOURNALISATION CENTRALISÉE
# ============================================================


def inject_values(
    tables,
    table_name,
    column_name,
    positions,
    new_values,
    anomaly_type,
    injection_log,
    modified_cells,
):
    """
    Modifie les cellules sélectionnées et journalise les changements.

    Une cellule ne peut être modifiée qu'une seule fois.
    """

    dataframe = tables[table_name]

    column_position = dataframe.columns.get_loc(column_name)

    if np.isscalar(new_values) or new_values is pd.NA:
        values = [new_values] * len(positions)
    else:
        values = list(new_values)

    if len(values) != len(positions):
        raise ValueError("Le nombre de valeurs doit correspondre aux positions.")

    injected_count = 0

    for position, new_value in zip(positions, values):
        position = int(position)

        cell_key = (table_name, position, column_name)

        if cell_key in modified_cells:
            continue

        original_value = dataframe.iat[position, column_position]

        # Comparaison scalaire : évite les ambiguïtés de typage Pylance.
        original_missing = original_value is None or original_value is pd.NA
        new_missing = new_value is None or new_value is pd.NA

        if original_missing and new_missing:
            continue

        if not original_missing and not new_missing and original_value == new_value:
            continue

        injection_log.append(
            {
                "table": table_name,
                "row_position": position,
                "column": column_name,
                "anomaly_type": anomaly_type,
                "original_value": str(original_value),
                "corrupted_value": (None if new_missing else str(new_value)),
            }
        )

        dataframe.iat[position, column_position] = new_value

        modified_cells.add(cell_key)

        injected_count += 1

    return injected_count


# ============================================================
# 6. VALEURS MANQUANTES
# ============================================================


def inject_missing_values(
    tables,
    rate,
    rng,
    injection_log,
    modified_cells,
):
    """Injecte des valeurs manquantes."""

    targets = {
        "customers": "city",
        "products": "category",
        "orders": "sales_channel",
    }

    for table_name, column_name in targets.items():
        dataframe = tables[table_name]

        eligible_mask = dataframe[column_name].notna()

        positions = select_rows(
            dataframe,
            rate,
            rng,
            eligible_mask,
        )

        count = inject_values(
            tables,
            table_name,
            column_name,
            positions,
            pd.NA,
            "missing_values",
            injection_log,
            modified_cells,
        )

        print(f"{table_name}.{column_name} : {count:,} valeurs manquantes")


# ============================================================
# 7. MONTANTS NÉGATIFS
# ============================================================


def inject_negative_amounts(
    tables,
    rate,
    rng,
    injection_log,
    modified_cells,
):
    """Transforme des montants positifs en montants négatifs."""

    targets = {
        "orders": "order_total",
        "payments": "payment_amount",
        "order_items": "unit_price",
    }

    for table_name, column_name in targets.items():
        dataframe = tables[table_name]

        eligible_mask = dataframe[column_name] > 0

        positions = select_rows(
            dataframe,
            rate,
            rng,
            eligible_mask,
        )

        original_values = dataframe.iloc[positions][column_name].to_numpy()

        negative_values = -np.abs(original_values)

        count = inject_values(
            tables,
            table_name,
            column_name,
            positions,
            negative_values,
            "negative_amounts",
            injection_log,
            modified_cells,
        )

        print(f"{table_name}.{column_name} : {count:,} montants négatifs")


# ============================================================
# 8. STATUTS INVALIDES
# ============================================================


def inject_invalid_status(
    tables,
    rate,
    rng,
    injection_log,
    modified_cells,
):
    """Remplace des statuts valides par une valeur inconnue."""

    targets = {
        "orders": "order_status",
        "payments": "payment_status",
        "complaints": "complaint_status",
    }

    for table_name, column_name in targets.items():
        dataframe = tables[table_name]

        eligible_mask = dataframe[column_name].notna()

        positions = select_rows(
            dataframe,
            rate,
            rng,
            eligible_mask,
        )

        count = inject_values(
            tables,
            table_name,
            column_name,
            positions,
            "UNKNOWN_STATUS",
            "invalid_status",
            injection_log,
            modified_cells,
        )

        print(f"{table_name}.{column_name} : {count:,} statuts invalides")


# ============================================================
# 9. EXÉCUTION PRINCIPALE
# ============================================================


# ============================================================
# 9. DATES INVALIDES
# ============================================================


def inject_invalid_dates(tables, rate, rng, log, modified):
    targets = {
        "orders": "order_date",
        "shipments": "shipping_date",
        "complaints": "complaint_date",
    }
    for table, column in targets.items():
        df = tables[table]
        mask = df[column].notna()
        positions = select_rows(df, rate, rng, mask)
        count = inject_values(
            tables,
            table,
            column,
            positions,
            "NOT_A_DATE",
            "invalid_dates",
            log,
            modified,
        )
        print(f"{table}.{column} : {count:,} dates invalides")


# ============================================================
# 10. RÉFÉRENCES CASSÉES
# ============================================================


def inject_broken_references(tables, rate, rng, log, modified):
    targets = [
        ("orders", "customer_id", "customers", "customer_id"),
        ("order_items", "product_id", "products", "product_id"),
        ("payments", "order_id", "orders", "order_id"),
    ]
    for table, column, parent, parent_key in targets:
        df = tables[table]
        valid_keys = set(tables[parent][parent_key].dropna())
        mask = df[column].isin(valid_keys)
        positions = select_rows(df, rate, rng, mask)
        # Chaîne garantie absente de la table parent ; type volontairement invalide.
        marker = f"BROKEN_REF_{parent.upper()}"
        while marker in valid_keys:
            marker += "_X"
        count = inject_values(
            tables, table, column, positions, marker, "broken_references", log, modified
        )
        print(f"{table}.{column} : {count:,} références cassées")


# ============================================================
# 11. FORMATS INVALIDES
# ============================================================


def inject_invalid_formats(tables, rate, rng, log, modified):
    targets = {
        "customers": ("first_name", "###INVALID_NAME###"),
        "products": ("product_name", "###INVALID_PRODUCT###"),
    }
    for table, (column, marker) in targets.items():
        df = tables[table]
        mask = df[column].notna() & df[column].ne(marker)
        positions = select_rows(df, rate, rng, mask)
        count = inject_values(
            tables, table, column, positions, marker, "invalid_formats", log, modified
        )
        print(f"{table}.{column} : {count:,} formats invalides")


# ============================================================
# 12. TOTAUX INCOHÉRENTS
# ============================================================


def inject_inconsistent_totals(tables, rate, rng, log, modified):
    table = "order_items"
    df = tables[table]
    # Uniquement des lignes dont les composants sont numériques et positifs,
    # et dont le prix unitaire n'a pas déjà été corrompu.
    q = pd.to_numeric(df["quantity"], errors="coerce")
    price = pd.to_numeric(df["unit_price"], errors="coerce")
    discount = pd.to_numeric(df["discount_amount"], errors="coerce")
    total = pd.to_numeric(df["line_total"], errors="coerce")
    expected = (q * price - discount).round(2)
    mask = (
        q.gt(0)
        & price.gt(0)
        & discount.ge(0)
        & total.notna()
        & np.isclose(total, expected, atol=0.02, rtol=0)
    )
    positions = select_rows(df, rate, rng, mask)
    # Une majoration de 100 € produit un écart explicite et détectable.
    changed = (total.iloc[positions] + 100).round(2).to_numpy()
    count = inject_values(
        tables,
        table,
        "line_total",
        positions,
        changed,
        "inconsistent_totals",
        log,
        modified,
    )
    print(f"{table}.line_total : {count:,} totaux incohérents")


# ============================================================
# 13. DOUBLONS DE LIGNES (OPÉRATION STRUCTURELLE)
# ============================================================


def inject_duplicates(tables, rate, rng, log):
    targets = ("customers", "orders", "order_items")
    for table in targets:
        df = tables[table]
        positions = select_rows(df, rate, rng)
        new_rows = df.iloc[positions].copy(deep=True)
        start = len(df)
        # ignore_index=True garantit des positions 0..N-1 après ajout.
        tables[table] = pd.concat([df, new_rows], ignore_index=True)
        for offset, source_position in enumerate(positions):
            log.append(
                {
                    "table": table,
                    "row_position": start + offset,
                    "column": None,
                    "anomaly_type": "duplicates",
                    "original_value": None,
                    "corrupted_value": None,
                    "source_row_position": int(source_position),
                    "operation": "row_insert",
                }
            )
        print(f"{table} : {len(positions):,} lignes dupliquées")


# ============================================================
# 14. TESTS ET EXÉCUTION
# ============================================================


def run_scenario(config, original, scenario, output_root, report_root):
    """Génère un scénario, valide les injections puis publie les fichiers."""
    rate = float(config["scenarios"][scenario]["rate"])
    seed = int(config["project"]["random_seed"])
    # Chaque scénario repart de la même référence et de la même graine.
    rng = np.random.default_rng(seed)
    corrupted = copy_tables(original)
    log = []
    modified = set()

    print(f"\n{'=' * 60}\nSCÉNARIO {scenario} ({rate:.0%})\n{'=' * 60}")
    steps = [
        ("Valeurs manquantes", inject_missing_values),
        ("Montants négatifs", inject_negative_amounts),
        ("Statuts invalides", inject_invalid_status),
        ("Dates invalides", inject_invalid_dates),
        ("Références cassées", inject_broken_references),
        ("Formats invalides", inject_invalid_formats),
        ("Totaux incohérents", inject_inconsistent_totals),
    ]
    for label, function in steps:
        if config["anomalies"][
            {
                "Valeurs manquantes": "missing_values",
                "Montants négatifs": "negative_amounts",
                "Statuts invalides": "invalid_status",
                "Dates invalides": "invalid_dates",
                "Références cassées": "broken_references",
                "Formats invalides": "invalid_formats",
                "Totaux incohérents": "inconsistent_totals",
            }[label]
        ]["enabled"]:
            print(f"\n{label}")
            function(corrupted, rate, rng, log, modified)
    if config["anomalies"]["duplicates"]["enabled"]:
        print("\nDoublons")
        inject_duplicates(corrupted, rate, rng, log)

    report = pd.DataFrame(log)
    if report.empty:
        raise AssertionError("Aucune anomalie injectée")
    cells = report[report["anomaly_type"] != "duplicates"]
    duplicates = report[report["anomaly_type"] == "duplicates"]
    journal_ok = (
        len(cells) == len(modified)
        and not cells.duplicated(["table", "row_position", "column"]).any()
        and len(duplicates)
        == sum(len(corrupted[t]) - len(original[t]) for t in original)
    )
    enabled = {k for k, v in config["anomalies"].items() if v["enabled"]}
    types_ok = set(report["anomaly_type"]) == enabled
    if not (journal_ok and types_ok):
        raise AssertionError(
            f"Contrôles échoués : journal={journal_ok}, types={types_ok}"
        )

    # Les positions dans le journal désignent les CSV de ce scénario.
    summary = {
        "scenario": scenario,
        "rate_per_eligible_rule": rate,
        "random_seed": seed,
        "total_events": len(report),
        "modified_cells": len(cells),
        "inserted_rows": len(duplicates),
        "events_by_type": {
            str(k): int(v) for k, v in report.groupby("anomaly_type").size().items()
        },
        "events_by_table": {
            str(k): int(v) for k, v in report.groupby("table").size().items()
        },
        "row_counts": {k: len(v) for k, v in corrupted.items()},
        "journal_coherent": bool(journal_ok),
        "enabled_families_present": bool(types_ok),
        "note": "Les taux s'appliquent aux lignes éligibles de chaque règle, pas au dataset global.",
    }

    # Répertoires temporaires dans les dossiers parents : publication seulement
    # après écriture complète. Aucun fichier raw n'est écrit.
    output_root.mkdir(parents=True, exist_ok=True)
    report_root.mkdir(parents=True, exist_ok=True)
    temp_data = Path(tempfile.mkdtemp(prefix=f".{scenario}_data_", dir=output_root))
    temp_reports = Path(
        tempfile.mkdtemp(prefix=f".{scenario}_report_", dir=report_root)
    )
    try:
        for name, df in corrupted.items():
            df.to_csv(temp_data / f"{name}.csv", index=False, encoding="utf-8")
        report.to_csv(temp_reports / "injection_log.csv", index=False, encoding="utf-8")
        (temp_reports / "injection_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        data_dest = output_root / scenario
        report_dest = report_root / scenario
        if data_dest.exists() or report_dest.exists():
            raise FileExistsError(
                f"Sorties déjà présentes pour {scenario} : aucune modification effectuée"
            )
        temp_data.rename(data_dest)
        try:
            temp_reports.rename(report_dest)
        except Exception:
            shutil.rmtree(data_dest)
            raise
        print(
            f"\n{scenario} : {len(report):,} événements, {len(duplicates):,} doublons ajoutés"
        )
        print(f"Données : {data_dest} | Rapport : {report_dest}")
    finally:
        if temp_data.exists():
            shutil.rmtree(temp_data)
        if temp_reports.exists():
            shutil.rmtree(temp_reports)
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="ConsultAI 360 — génération des scénarios de corruption"
    )
    parser.add_argument(
        "--scenario", choices=["low", "medium", "critical", "all"], default="all"
    )
    args = parser.parse_args()
    config = load_config()
    if not all(
        config["safety"].get(k) is True
        for k in ("preserve_raw", "log_injections", "deterministic")
    ):
        raise ValueError(
            "Les protections preserve_raw, log_injections et deterministic doivent être activées"
        )
    if config["safety"].get("overwrite_corrupted") is not False:
        raise ValueError("overwrite_corrupted doit être false")

    raw_path = Path(config["paths"]["raw"]).resolve()
    output_root = Path(config["paths"]["corrupted"]).resolve()
    # Préserver les rapports d'audit existants dans reports/data_quality.
    report_root = Path("reports/data_quality/injections").resolve()
    if (
        raw_path == output_root
        or raw_path in output_root.parents
        or output_root in raw_path.parents
    ):
        raise ValueError("Les chemins raw et corrupted ne doivent pas se chevaucher")
    if (
        raw_path == report_root
        or raw_path in report_root.parents
        or report_root in raw_path.parents
    ):
        raise ValueError("Le dossier de rapports ne doit pas se trouver dans raw")

    scenarios = list(config["scenarios"]) if args.scenario == "all" else [args.scenario]
    # Vérifier toutes les destinations AVANT la première écriture.
    existing = [
        str(path)
        for s in scenarios
        for path in (output_root / s, report_root / s)
        if path.exists()
    ]
    if existing:
        raise FileExistsError(
            "Sorties déjà présentes, écrasement interdit : " + ", ".join(existing)
        )

    print("Chargement des dix tables originales...")
    original = load_raw_data(config)
    for scenario in scenarios:
        run_scenario(config, original, scenario, output_root, report_root)
    print("\nTerminé. Aucun fichier de data/raw n'a été écrit.")


if __name__ == "__main__":
    main()
