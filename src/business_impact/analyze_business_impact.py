"""ConsultAI 360 — impact de la qualité sur les KPI NexaRetail.

Depuis la racine du dépôt :
    .\\.venv\\Scripts\\python.exe src/business_impact/analyze_business_impact.py --scenario medium
    .\\.venv\\Scripts\\python.exe src/business_impact/analyze_business_impact.py --scenario all

Lecture seule des données. Les écarts de reporting ne sont PAS des pertes financières.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

SCENARIOS = ("low", "medium", "critical")
TABLES = ("orders", "payments", "order_items", "customers")


def read_data(folder: Path) -> dict[str, pd.DataFrame]:
    result = {}
    for name in TABLES:
        path = folder / f"{name}.csv"
        if not path.is_file():
            raise FileNotFoundError(f"Fichier introuvable : {path}")
        result[name] = pd.read_csv(
            path,
            low_memory=False,
            dtype={
                "order_id": "string",
                "customer_id": "string",
                "payment_id": "string",
                "order_item_id": "string",
                "product_id": "string",
                "store_id": "string",
            },
        )
    return result


def metric_snapshot(tables: dict[str, pd.DataFrame]) -> dict:
    orders, payments, items, customers = (tables[t] for t in TABLES)
    amounts = pd.to_numeric(orders["order_total"], errors="coerce")
    pay_amounts = pd.to_numeric(payments["payment_amount"], errors="coerce")
    item_totals = pd.to_numeric(items["line_total"], errors="coerce")
    dates = pd.to_datetime(orders["order_date"], errors="coerce", format="mixed")
    valid_customer_ids = set(customers["customer_id"].dropna())
    customer_ref = orders["customer_id"].astype("string")
    invalid_customer = customer_ref.isna() | ~customer_ref.isin(valid_customer_ids)
    valid_order_ids = set(orders["order_id"].dropna())
    payment_order_ref = payments["order_id"].astype("string")
    orphan_payments = payment_order_ref.isna() | ~payment_order_ref.isin(
        valid_order_ids
    )
    item_order_ref = items["order_id"].astype("string")
    orphan_items = item_order_ref.isna() | ~item_order_ref.isin(valid_order_ids)
    valid_order_amount = amounts.notna() & amounts.ge(0)
    valid_payment_amount = pay_amounts.notna() & pay_amounts.ge(0)
    valid_item_total = item_totals.notna() & item_totals.ge(0)
    order_ids = orders["order_id"].astype("string")
    duplicate_orders = int(order_ids.notna().sum() - order_ids.dropna().nunique())
    paid = payments["payment_status"].astype("string").eq("paid").fillna(False)
    valid_paid = paid & valid_payment_amount
    # Intentionally naive: what a dashboard summing the column without DQ rules would display.
    raw_reported_orders = float(amounts.sum())
    raw_reported_payments = float(pay_amounts.sum())
    unique_order_count = int(order_ids.dropna().nunique())
    usable_order_count = int(valid_order_amount.sum())
    return {
        "orders_rows": len(orders),
        "unique_orders": unique_order_count,
        "duplicate_order_ids": duplicate_orders,
        "orders_with_usable_amount": usable_order_count,
        "orders_missing_amount": int(amounts.isna().sum()),
        "orders_negative_amount": int(amounts.lt(0).sum()),
        "orders_invalid_customer_reference": int(invalid_customer.sum()),
        "orders_invalid_date": int((orders["order_date"].notna() & dates.isna()).sum()),
        "orders_missing_date": int(orders["order_date"].isna().sum()),
        "reported_order_total_sum": round(raw_reported_orders, 2),
        "nonnegative_order_total_sum": round(
            float(amounts.where(valid_order_amount).sum()), 2
        ),
        "reported_average_order_value": round(raw_reported_orders / len(orders), 2)
        if len(orders)
        else None,
        "usable_amount_average": round(
            float(amounts.where(valid_order_amount).sum()) / usable_order_count, 2
        )
        if usable_order_count
        else None,
        "payments_rows": len(payments),
        "payments_missing_amount": int(pay_amounts.isna().sum()),
        "payments_negative_amount": int(pay_amounts.lt(0).sum()),
        "payments_invalid_order_reference": int(orphan_payments.sum()),
        "reported_payment_total_sum": round(raw_reported_payments, 2),
        "paid_payment_total_sum": round(float(pay_amounts.where(valid_paid).sum()), 2),
        "items_rows": len(items),
        "items_invalid_order_reference": int(orphan_items.sum()),
        "reported_line_total_sum": round(float(item_totals.sum()), 2),
        "nonnegative_line_total_sum": round(
            float(item_totals.where(valid_item_total).sum()), 2
        ),
    }


def differences(reference: dict, other: dict) -> dict:
    result = {}
    for key, ref in reference.items():
        value = other[key]
        if value is None or ref is None:
            result[key] = {"absolute": None, "relative_pct": None}
            continue
        delta = round(value - ref, 4)
        pct = round(delta / abs(ref) * 100, 4) if ref != 0 else None
        result[key] = {"absolute": delta, "relative_pct": pct}
    return result


def analyze_scenario(scenario: str, reference: dict, out_root: Path) -> dict:
    corrupted = metric_snapshot(read_data(Path("data/corrupted") / scenario))
    cleaned = metric_snapshot(read_data(Path("data/processed_v2") / scenario))
    snapshots = {"raw": reference, "corrupted": corrupted, "cleaned": cleaned}
    deltas = {
        "corrupted_vs_raw": differences(reference, corrupted),
        "cleaned_vs_raw": differences(reference, cleaned),
    }
    report = {
        "scenario": scenario,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "methodology": {
            "raw": "Données de référence synthétiques non corrompues",
            "corrupted": "Données volontairement dégradées, doublons inclus",
            "cleaned": "Données V2 nettoyées, doublons retirés et valeurs douteuses parfois nullifiées",
            "interpretation": "Les écarts mesurent des distorsions de reporting, jamais une perte financière avérée.",
            "reported_order_total_sum": "Somme naïve de order_total, valeurs négatives incluses; les NULL sont ignorés.",
            "reported_average_order_value": "Somme naïve de order_total / nombre de lignes de commandes, doublons inclus.",
            "usable_amount_average": "Somme des montants non négatifs / nombre de lignes avec montant non négatif.",
            "paid_payment_total_sum": "Somme des montants non négatifs de paiements dont le statut est paid.",
            "caveats": [
                "Les métriques naïves ne sont pas des KPI financiers comptables certifiés.",
                "La nullification peut réduire un montant sans restaurer sa valeur d'origine.",
                "Un customer_id cassé n'invalide pas nécessairement le montant commercial.",
                "Une date NULL n'est pas considérée comme date syntaxiquement invalide, mais elle est comptée séparément.",
                "Les résultats ne prouvent pas un impact monétaire réel sur l'entreprise fictive.",
            ],
        },
        "snapshots": snapshots,
        "deltas": deltas,
    }
    dest = out_root / scenario
    if dest.exists():
        raise FileExistsError(f"Rapport existant, aucun écrasement : {dest}")
    dest.mkdir(parents=True, exist_ok=False)
    (dest / "business_impact_summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    rows = []
    for metric in reference:
        rows.append(
            {
                "scenario": scenario,
                "metric": metric,
                "raw": reference[metric],
                "corrupted": corrupted[metric],
                "cleaned": cleaned[metric],
                "corrupted_delta": deltas["corrupted_vs_raw"][metric]["absolute"],
                "corrupted_delta_pct": deltas["corrupted_vs_raw"][metric][
                    "relative_pct"
                ],
                "cleaned_delta": deltas["cleaned_vs_raw"][metric]["absolute"],
                "cleaned_delta_pct": deltas["cleaned_vs_raw"][metric]["relative_pct"],
            }
        )
    pd.DataFrame(rows).to_csv(
        dest / "business_impact_kpis.csv", index=False, encoding="utf-8-sig"
    )
    print(f"\n{scenario.upper()} | KPI de référence / corrompus / nettoyés")
    for metric in (
        "reported_order_total_sum",
        "reported_average_order_value",
        "unique_orders",
        "orders_invalid_customer_reference",
        "orders_missing_amount",
    ):
        print(
            f"{metric:37} | {reference[metric]:>14,} | {corrupted[metric]:>14,} | {cleaned[metric]:>14,}"
        )
    print(f"Rapports : {dest}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ConsultAI 360 — impact business Data Quality"
    )
    parser.add_argument("--scenario", choices=(*SCENARIOS, "all"), default="medium")
    args = parser.parse_args()
    out_root = Path("reports/business_impact")
    scenarios = SCENARIOS if args.scenario == "all" else (args.scenario,)
    for scenario in scenarios:
        if (out_root / scenario).exists():
            raise FileExistsError(f"Rapport existant : {out_root / scenario}")
    reference = metric_snapshot(read_data(Path("data/raw")))
    for scenario in scenarios:
        analyze_scenario(scenario, reference, out_root)


if __name__ == "__main__":
    main()
