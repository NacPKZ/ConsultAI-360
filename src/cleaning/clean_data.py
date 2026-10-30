"""ConsultAI 360 - nettoyage conservateur V2.

Depuis la racine du projet :
    .\\.venv\\Scripts\\python.exe src/cleaning/clean_data.py --scenario medium

Ne consulte jamais les journaux d'injection et n'écrase aucune sortie.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

TABLES = (
    "customers",
    "stores",
    "employees",
    "products",
    "orders",
    "order_items",
    "payments",
    "shipments",
    "complaints",
    "inventory",
)
PRIMARY_KEYS = {
    "customers": "customer_id",
    "stores": "store_id",
    "employees": "employee_id",
    "products": "product_id",
    "orders": "order_id",
    "order_items": "order_item_id",
    "payments": "payment_id",
    "shipments": "shipment_id",
    "complaints": "complaint_id",
    "inventory": "inventory_id",
}
REFERENCES = (
    ("employees", "store_id", "stores", "store_id"),
    ("orders", "customer_id", "customers", "customer_id"),
    ("orders", "store_id", "stores", "store_id"),
    ("order_items", "order_id", "orders", "order_id"),
    ("order_items", "product_id", "products", "product_id"),
    ("payments", "order_id", "orders", "order_id"),
    ("shipments", "order_id", "orders", "order_id"),
    ("complaints", "order_id", "orders", "order_id"),
    ("complaints", "customer_id", "customers", "customer_id"),
    ("inventory", "store_id", "stores", "store_id"),
    ("inventory", "product_id", "products", "product_id"),
)
STATUS = {
    ("orders", "order_status"): {
        "delivered",
        "completed",
        "cancelled",
        "shipped",
        "processing",
    },
    ("payments", "payment_status"): {"paid", "failed", "cancelled", "refunded"},
    ("complaints", "complaint_status"): {"resolved", "in_progress", "open"},
}
DATES = {
    "orders": ("order_date",),
    "shipments": ("shipping_date", "estimated_delivery_date", "actual_delivery_date"),
    "complaints": ("complaint_date", "resolution_date"),
}
NONNEGATIVE = {
    "orders": ("order_total",),
    "payments": ("payment_amount",),
    "order_items": ("unit_price",),
}
FORMATS = (("customers", "first_name"), ("products", "product_name"))


def load_tables(folder: Path) -> dict[str, pd.DataFrame]:
    if not folder.is_dir():
        raise FileNotFoundError(folder)
    tables = {}
    for name in TABLES:
        path = folder / f"{name}.csv"
        if not path.is_file():
            raise FileNotFoundError(path)
        df = pd.read_csv(path, low_memory=False)
        df["_source_row_position"] = np.arange(len(df), dtype=np.int64)
        tables[name] = df
    return tables


def normalize_key(series: pd.Series) -> pd.Series:
    """Évite les fausses ruptures 42 vs 42.0 après lecture CSV.

    Les marqueurs alphanumériques restent inchangés et seront détectés.
    """
    value = series.astype("string").str.strip()
    return value.str.replace(r"^(\d+)\.0$", r"\1", regex=True)


def clean(tables: dict[str, pd.DataFrame]):
    actions = Counter()
    quarantine = {table: [] for table in TABLES}
    quality_events = []

    def record(table: str, mask: pd.Series, column: str, issue: str, action: str):
        positions = tables[table].loc[mask.fillna(False), "_source_row_position"]
        quality_events.extend(
            {
                "table": table,
                "source_row_position": int(pos),
                "column": column,
                "issue": issue,
                "action": action,
            }
            for pos in positions
        )
        actions[f"{action}:{issue}:{table}.{column}"] += len(positions)

    def remove_rows(table: str, mask: pd.Series, reason: str):
        df = tables[table]
        mask = mask.fillna(False).astype(bool)
        if not mask.any():
            return
        rejected = df.loc[mask].copy()
        rejected["_quarantine_reason"] = reason
        quarantine[table].append(rejected)
        tables[table] = df.loc[~mask].copy()
        actions[f"quarantine:{reason}:{table}"] += len(rejected)

    # Suppression des copies exactes, sans utiliser la colonne de provenance.
    for table in TABLES:
        df = tables[table]
        subset = [c for c in df.columns if c != "_source_row_position"]
        remove_rows(
            table, df.duplicated(subset=subset, keep="first"), "exact_duplicate"
        )

    # Une clé primaire vide/ambiguë ne permet pas de distinguer les lignes.
    # Pas de propagation de la quarantaine aux tables enfants.
    for table, key in PRIMARY_KEYS.items():
        df = tables[table]
        normalized = normalize_key(df[key])
        remove_rows(
            table,
            normalized.isna()
            | normalized.eq("").fillna(False)
            | normalized.duplicated(keep=False),
            "invalid_or_ambiguous_primary_key",
        )

    for (table, col), allowed in STATUS.items():
        df = tables[table]
        mask = df[col].notna() & ~df[col].isin(allowed)
        record(table, mask, col, "invalid_status", "nullified")
        df.loc[mask, col] = pd.NA

    for table, columns in NONNEGATIVE.items():
        df = tables[table]
        for col in columns:
            numeric = pd.to_numeric(df[col], errors="coerce")
            mask = numeric.lt(0)
            record(table, mask, col, "negative_amount", "nullified")
            df.loc[mask, col] = np.nan

    for table, columns in DATES.items():
        df = tables[table]
        for col in columns:
            parsed = pd.to_datetime(df[col], errors="coerce", format="mixed")
            mask = df[col].notna() & parsed.isna()
            record(table, mask, col, "invalid_date", "nullified")
            df.loc[mask, col] = pd.NA

    for table, col in FORMATS:
        df = tables[table]
        mask = (
            df[col].astype("string").str.contains(r"#{3}.*#{3}", regex=True, na=False)
        )
        record(table, mask, col, "invalid_format", "nullified")
        df.loc[mask, col] = pd.NA

    # Conserver les lignes avec FK cassée, mais signaler explicitement le risque.
    # L'audit des FK utilise toutes les tables déjà dédupliquées.
    for child, col, parent, parent_key in REFERENCES:
        child_values = normalize_key(tables[child][col])
        parent_values = set(normalize_key(tables[parent][parent_key]).dropna())
        mask = child_values.isna() | ~child_values.isin(parent_values)
        record(child, mask, col, f"broken_reference_to_{parent}", "flagged_not_deleted")

    items = tables["order_items"]
    qty = pd.to_numeric(items["quantity"], errors="coerce")
    price = pd.to_numeric(items["unit_price"], errors="coerce")
    discount = pd.to_numeric(items["discount_amount"], errors="coerce")
    actual = pd.to_numeric(items["line_total"], errors="coerce")
    valid = qty.gt(0) & price.ge(0) & discount.ge(0) & discount.le(qty * price)
    expected = (qty * price - discount).round(2)
    same = pd.Series(
        np.isclose(
            actual.to_numpy(dtype=float),
            expected.to_numpy(dtype=float),
            atol=0.02,
            rtol=0,
            equal_nan=False,
        ),
        index=items.index,
    )
    changed = valid & (actual.isna() | ~same)
    record(
        "order_items",
        changed,
        "line_total",
        "inconsistent_or_missing_total",
        "recomputed",
    )
    items.loc[changed, "line_total"] = expected.loc[changed]
    unverifiable = ~valid & items["line_total"].notna()
    record("order_items", unverifiable, "line_total", "unverifiable_total", "nullified")
    items.loc[unverifiable, "line_total"] = np.nan

    return (
        tables,
        quarantine,
        actions,
        pd.DataFrame(
            quality_events,
            columns=["table", "source_row_position", "column", "issue", "action"],
        ),
    )


def main():
    parser = argparse.ArgumentParser(
        description="ConsultAI 360 - nettoyage conservateur V2"
    )
    parser.add_argument(
        "--scenario", choices=("low", "medium", "critical"), default="medium"
    )
    args = parser.parse_args()
    source = Path("data/corrupted") / args.scenario
    output = Path("data/processed_v2") / args.scenario
    report = Path("reports/data_quality/cleaning_v2") / args.scenario
    if output.exists() or report.exists():
        raise FileExistsError(
            f"Sortie existante : {output} ou {report}. Aucun écrasement."
        )

    tables = load_tables(source)
    before = {name: len(df) for name, df in tables.items()}
    cleaned, quarantine, actions, events = clean(tables)

    spec = importlib.util.spec_from_file_location(
        "quality_audit", "src/quality/audit_quality.py"
    )
    if spec is None or spec.loader is None:
        raise ImportError("Audit introuvable")
    audit_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit_module)
    remaining = audit_module.audit(
        {
            name: df.drop(columns=["_source_row_position"])
            for name, df in cleaned.items()
        }
    )

    output.mkdir(parents=True, exist_ok=False)
    report.mkdir(parents=True, exist_ok=False)
    for name, df in cleaned.items():
        df.drop(columns=["_source_row_position"]).to_csv(
            output / f"{name}.csv", index=False, encoding="utf-8-sig"
        )
        if quarantine[name]:
            pd.concat(quarantine[name], ignore_index=True).to_csv(
                report / f"quarantine_{name}.csv", index=False, encoding="utf-8-sig"
            )
    events.to_csv(report / "quality_events.csv", index=False, encoding="utf-8-sig")
    remaining.to_csv(
        report / "remaining_anomalies.csv", index=False, encoding="utf-8-sig"
    )

    summary = {
        "scenario": args.scenario,
        "version": 2,
        "cleaned_at_utc": datetime.now(UTC).isoformat(),
        "independent_of_injection_logs": True,
        "rows_before": before,
        "rows_after": {name: len(df) for name, df in cleaned.items()},
        "quarantined_rows": {
            name: sum(len(part) for part in quarantine[name]) for name in TABLES
        },
        "actions": dict(sorted(actions.items())),
        "remaining_audit_alerts": len(remaining),
        "remaining_alerts_by_type": {
            key: int(count)
            for key, count in remaining["anomaly_type"].value_counts().items()
        },
        "limitations": [
            "Les FK invalides restent dans les données analytiques et sont signalées séparément.",
            "Les tables nettoyées ne sont pas garanties compatibles avec des FK SQL strictes.",
            "Les NULL et valeurs inconnues ne sont pas restaurés à partir des journaux.",
            "Le fichier quality_events.csv conserve les positions des lignes source.",
            "Les alertes restantes ne représentent pas nécessairement des erreurs distinctes.",
        ],
    }
    (report / "cleaning_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nScénario : {args.scenario} (V2)")
    print(f"Lignes avant : {sum(before.values()):,}")
    print(f"Lignes après : {sum(len(df) for df in cleaned.values()):,}")
    print(f"Lignes en quarantaine : {sum(summary['quarantined_rows'].values()):,}")
    print(f"Alertes restantes : {len(remaining):,}")
    print(f"Données : {output}")
    print(f"Rapports : {report}")


if __name__ == "__main__":
    main()
