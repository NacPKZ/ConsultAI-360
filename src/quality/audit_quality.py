"""ConsultAI 360 — audit indépendant des données corrompues.

Utilisation : python src/quality/audit_quality.py --scenario all
L'audit ne consulte jamais les journaux d'injection.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

DATE_COLUMNS = {
    "orders": ["order_date"],
    "shipments": ["shipping_date", "estimated_delivery_date", "actual_delivery_date"],
    "complaints": ["complaint_date", "resolution_date"],
}
STATUS_ALLOWED = {
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
MISSING_REQUIRED = {
    "customers": ["city"],
    "products": ["category"],
    "orders": ["sales_channel"],
}
NONNEGATIVE = {
    "orders": ["order_total"],
    "payments": ["payment_amount"],
    "order_items": ["unit_price"],
}
REFERENCES = [
    ("orders", "customer_id", "customers", "customer_id"),
    ("order_items", "product_id", "products", "product_id"),
    ("payments", "order_id", "orders", "order_id"),
]


def load_config() -> dict:
    with Path("config/corruption.yaml").open(encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle)
    if not isinstance(cfg, dict):
        raise TypeError("Configuration YAML invalide")
    return cfg


def load_scenario(root: Path) -> dict[str, pd.DataFrame]:
    if not root.is_dir():
        raise FileNotFoundError(f"Scénario absent : {root}")
    tables = {
        p.stem: pd.read_csv(p, low_memory=False) for p in sorted(root.glob("*.csv"))
    }
    if len(tables) != 10:
        raise ValueError(f"10 CSV attendus dans {root}, trouvés : {len(tables)}")
    return tables


def audit(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    events: list[dict] = []
    seen: set[tuple] = set()

    def flag(table: str, rows, column: str | None, kind: str, detail: str):
        for row in rows:
            row = int(row)
            key = (table, row, column, kind)
            if key in seen:
                continue
            seen.add(key)
            events.append(
                {
                    "table": table,
                    "row_position": row,
                    "column": column,
                    "anomaly_type": kind,
                    "rule": detail,
                }
            )

    for table, df in tables.items():
        # Les lignes insérées par le générateur sont des copies intégrales.
        # Un doublon initial éventuel peut aussi être détecté : c'est un vrai
        # résultat de l'audit, à évaluer ensuite comme possible faux positif.
        duplicates = df.duplicated(keep="first")
        flag(
            table,
            np.flatnonzero(duplicates.to_numpy()),
            None,
            "duplicates",
            "exact_row_duplicate",
        )

    for table, cols in MISSING_REQUIRED.items():
        df = tables[table]
        for col in cols:
            mask = df[col].isna() | df[col].astype("string").str.strip().eq("").fillna(
                False
            )
            flag(
                table,
                np.flatnonzero(mask.to_numpy(dtype=bool)),
                col,
                "missing_values",
                "required_value_missing",
            )

    for table, cols in NONNEGATIVE.items():
        df = tables[table]
        for col in cols:
            values = pd.to_numeric(df[col], errors="coerce")
            mask = values.lt(0).fillna(False)
            flag(
                table,
                np.flatnonzero(mask.to_numpy(dtype=bool)),
                col,
                "negative_amounts",
                "negative_monetary_value",
            )

    for (table, col), allowed in STATUS_ALLOWED.items():
        values = tables[table][col]
        mask = values.notna() & ~values.isin(allowed)
        flag(
            table,
            np.flatnonzero(mask.to_numpy(dtype=bool)),
            col,
            "invalid_status",
            "not_in_allowed_statuses",
        )

    for table, cols in DATE_COLUMNS.items():
        df = tables[table]
        for col in cols:
            parsed = pd.to_datetime(df[col], errors="coerce", format="mixed")
            mask = df[col].notna() & parsed.isna()
            flag(
                table,
                np.flatnonzero(mask.to_numpy(dtype=bool)),
                col,
                "invalid_dates",
                "unparseable_date",
            )

    for child, col, parent, parent_key in REFERENCES:
        # Normalisation en chaînes : fonctionne même si l'injection a converti
        # une colonne d'identifiants numériques en objet/texte.
        child_values = tables[child][col].astype("string")
        parent_values = set(tables[parent][parent_key].dropna().astype("string"))
        mask = child_values.notna() & ~child_values.isin(parent_values)
        flag(
            child,
            np.flatnonzero(mask.to_numpy(dtype=bool)),
            col,
            "broken_references",
            f"missing_parent:{parent}.{parent_key}",
        )

    for table, col in [("customers", "first_name"), ("products", "product_name")]:
        values = tables[table][col].astype("string")
        # Règle de format : le marqueur non alphabétique n'est pas un nom.
        # Cette règle cible les chaînes avec délimiteurs ###, sans accéder
        # aux logs d'injection ; d'autres formats seront étudiés ensuite.
        mask = values.str.contains(r"#{3}.*#{3}", regex=True, na=False)
        flag(
            table,
            np.flatnonzero(mask.to_numpy(dtype=bool)),
            col,
            "invalid_formats",
            "forbidden_hash_delimiters",
        )

    df = tables["order_items"]
    quantity = pd.to_numeric(df["quantity"], errors="coerce")
    unit_price = pd.to_numeric(df["unit_price"], errors="coerce")
    discount = pd.to_numeric(df["discount_amount"], errors="coerce")
    line_total = pd.to_numeric(df["line_total"], errors="coerce")
    expected = (quantity * unit_price - discount).round(2)
    valid_components = (
        quantity.gt(0) & unit_price.gt(0) & discount.ge(0) & line_total.notna()
    )
    discrepancy = ~np.isclose(
        line_total.to_numpy(dtype=float),
        expected.to_numpy(dtype=float),
        atol=0.02,
        rtol=0,
        equal_nan=False,
    )
    mask = valid_components.to_numpy(dtype=bool) & discrepancy
    flag(
        "order_items",
        np.flatnonzero(mask),
        "line_total",
        "inconsistent_totals",
        "line_total_not_quantity_times_price_minus_discount",
    )

    columns = ["table", "row_position", "column", "anomaly_type", "rule"]
    return (
        pd.DataFrame(events, columns=columns)
        .sort_values(
            ["table", "row_position", "anomaly_type", "column"], na_position="last"
        )
        .reset_index(drop=True)
    )


def run_scenario(cfg: dict, scenario: str) -> None:
    root = Path(cfg["paths"]["corrupted"]) / scenario
    output = Path("reports/data_quality/audits") / scenario
    if output.exists():
        raise FileExistsError(f"Rapport déjà présent (pas d'écrasement) : {output}")
    tables = load_scenario(root)
    detected = audit(tables)
    summary = {
        "scenario": scenario,
        "audit_independent_of_injection_logs": True,
        "audited_at_utc": datetime.now(UTC).isoformat(),
        "total_detected_events": len(detected),
        "events_by_type": {
            k: int(v) for k, v in detected["anomaly_type"].value_counts().items()
        },
        "events_by_table": {
            k: int(v) for k, v in detected["table"].value_counts().items()
        },
        "rows_by_table": {k: len(v) for k, v in tables.items()},
        "caveats": [
            "Les doublons sont des lignes exactement identiques, pas des doublons de clé.",
            "Les formats invalides détectés utilisent une règle de délimiteurs ###.",
            "Les anomalies multiples sur une cellule peuvent générer plusieurs alertes de types différents.",
            "Les résultats n'ont pas encore été comparés au journal de référence.",
        ],
    }
    output.mkdir(parents=True, exist_ok=False)
    detected.to_csv(
        output / "detected_anomalies.csv", index=False, encoding="utf-8-sig"
    )
    (output / "audit_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n{scenario}: {len(detected):,} alertes | {len(tables)} tables")
    print(detected["anomaly_type"].value_counts().to_string())
    print(f"Rapports : {output}")


def main():
    parser = argparse.ArgumentParser(description="Audit indépendant ConsultAI 360")
    parser.add_argument(
        "--scenario", choices=["low", "medium", "critical", "all"], default="medium"
    )
    args = parser.parse_args()
    cfg = load_config()
    scenarios = list(cfg["scenarios"]) if args.scenario == "all" else [args.scenario]
    for scenario in scenarios:
        run_scenario(cfg, scenario)


if __name__ == "__main__":
    main()
