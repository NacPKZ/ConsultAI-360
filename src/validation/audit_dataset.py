from pathlib import Path

import numpy as np
import pandas as pd
import yaml


# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

CONFIG_PATH = ROOT / "config" / "generation.yaml"

TABLES = [
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
]

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

FOREIGN_KEYS = [
    ("orders", "customer_id", "customers", "customer_id"),
    ("order_items", "order_id", "orders", "order_id"),
    ("order_items", "product_id", "products", "product_id"),
    ("payments", "order_id", "orders", "order_id"),
    ("shipments", "order_id", "orders", "order_id"),
    ("complaints", "order_id", "orders", "order_id"),
    ("complaints", "customer_id", "customers", "customer_id"),
    ("inventory", "store_id", "stores", "store_id"),
    ("inventory", "product_id", "products", "product_id"),
]

results = []


# ============================================================
# OUTILS
# ============================================================

def add_check(category, check_name, errors, details=""):

    count = int(errors)

    results.append({
        "category": category,
        "check": check_name,
        "errors": count,
        "status": "PASS" if count == 0 else "FAIL",
        "details": details,
    })

    symbol = "PASS" if count == 0 else "FAIL"

    print(f"[{symbol}] {check_name}: {count}")


def require_columns(df, columns, table_name):

    missing = sorted(set(columns) - set(df.columns))

    if missing:
        raise ValueError(
            f"{table_name}: colonnes manquantes : {missing}"
        )


def numeric(series):

    return pd.to_numeric(series, errors="coerce")


def dates(series):

    return pd.to_datetime(series, errors="coerce")


def compare_money(left, right, tolerance=0.02):

    return (
        (left - right).abs() > tolerance
    )


# ============================================================
# CHARGEMENT
# ============================================================

def load_data():

    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    raw_directory = (
        ROOT / str(config["output"]["directory"])
    )

    data = {}

    for table in TABLES:

        path = raw_directory / f"{table}.csv"

        if not path.exists():
            raise FileNotFoundError(
                f"Fichier manquant : {path}"
            )

        data[table] = pd.read_csv(
            path,
            low_memory=False,
            dtype={
                PRIMARY_KEYS[table]: "string"
            },
        )

        print(
            f"Charge : {table:<15} "
            f"{len(data[table]):>10,} lignes"
        )

    return config, data


# ============================================================
# 1. STRUCTURE ET IDENTIFIANTS
# ============================================================

def audit_structure(data):

    print("\n=== STRUCTURE ET IDENTIFIANTS ===")

    for table in TABLES:

        df = data[table]
        primary_key = PRIMARY_KEYS[table]

        require_columns(df, [primary_key], table)

        add_check(
            "structure",
            f"{table}: table vide",
            int(df.empty),
        )

        add_check(
            "structure",
            f"{table}: cles primaires nulles",
            df[primary_key].isna().sum(),
        )

        add_check(
            "structure",
            f"{table}: cles primaires dupliquees",
            df[primary_key].duplicated().sum(),
        )


# ============================================================
# 2. INTEGRITE REFERENTIELLE
# ============================================================

def audit_foreign_keys(data):

    print("\n=== INTEGRITE REFERENTIELLE ===")

    for child, child_col, parent, parent_col in FOREIGN_KEYS:

        child_df = data[child]
        parent_df = data[parent]

        require_columns(
            child_df,
            [child_col],
            child,
        )

        require_columns(
            parent_df,
            [parent_col],
            parent,
        )

        child_values = child_df[child_col].astype("string")
        parent_values = parent_df[parent_col].astype("string")

        invalid = (
            child_values.notna()
            & ~child_values.isin(parent_values)
        )

        add_check(
            "foreign_keys",
            f"{child}.{child_col} -> {parent}.{parent_col}",
            invalid.sum(),
        )


# ============================================================
# 3. COMMANDES ET LIGNES DE COMMANDES
# ============================================================

def audit_orders(data):

    print("\n=== COMMANDES ===")

    orders = data["orders"]
    items = data["order_items"]

    require_columns(
        orders,
        [
            "order_id",
            "order_date",
            "order_total",
            "sales_channel",
            "order_status",
        ],
        "orders",
    )

    require_columns(
        items,
        [
            "order_id",
            "quantity",
            "unit_price",
            "discount_amount",
            "line_total",
        ],
        "order_items",
    )

    add_check(
        "orders",
        "Commandes avec montant negatif",
        (numeric(orders["order_total"]) < 0).sum(),
    )

    add_check(
        "orders",
        "Quantites d'articles invalides",
        (numeric(items["quantity"]) <= 0).sum(),
    )

    add_check(
        "orders",
        "Prix unitaires negatifs",
        (numeric(items["unit_price"]) < 0).sum(),
    )

    # Total theorique des lignes
    expected_line_total = (
        numeric(items["quantity"])
        * numeric(items["unit_price"])
        - numeric(items["discount_amount"])
    )

    actual_line_total = numeric(items["line_total"])

    add_check(
        "orders",
        "Lignes avec montant incoherent",
        compare_money(
            expected_line_total,
            actual_line_total,
        ).sum(),
    )

    # Somme des lignes par commande
    item_totals = (
        items.assign(
            line_total_num=actual_line_total
        )
        .groupby("order_id")["line_total_num"]
        .sum()
    )

    order_totals = numeric(orders["order_total"])

    expected_order_totals = (
        orders["order_id"].map(item_totals)
    )

    add_check(
        "orders",
        "Commandes sans lignes",
        expected_order_totals.isna().sum(),
    )

    valid = expected_order_totals.notna()

    add_check(
        "orders",
        "Totaux commandes incoherents",
        compare_money(
            order_totals.loc[valid],
            expected_order_totals.loc[valid],
        ).sum(),
    )

    channels = {"online", "in_store"}

    add_check(
        "orders",
        "Canaux de vente inconnus",
        (~orders["sales_channel"].isin(channels)).sum(),
    )


# ============================================================
# 4. PAIEMENTS
# ============================================================

def audit_payments(data):

    print("\n=== PAIEMENTS ===")

    orders = data["orders"]
    payments = data["payments"]

    require_columns(
        payments,
        [
            "order_id",
            "payment_status",
            "payment_amount",
        ],
        "payments",
    )

    valid_statuses = {
        "paid",
        "failed",
        "cancelled",
        "refunded",
    }

    add_check(
        "payments",
        "Statuts de paiement inconnus",
        (
            ~payments["payment_status"].isin(valid_statuses)
        ).sum(),
    )

    payment_amount = numeric(
        payments["payment_amount"]
    )

    add_check(
        "payments",
        "Montants de paiement non numeriques",
        payment_amount.isna().sum(),
    )

    # Paiements nets : paiements positifs moins remboursements
    payment_totals = (
        payments.assign(
            amount_num=payment_amount
        )
        .groupby("order_id")["amount_num"]
        .sum()
    )

    paid_orders = orders[
        orders["order_status"] != "cancelled"
    ].copy()

    paid_totals = paid_orders[
        "order_id"
    ].map(payment_totals)

    add_check(
        "payments",
        "Commandes actives sans paiement",
        paid_totals.isna().sum(),
    )

    valid = paid_totals.notna()

    add_check(
        "payments",
        "Montants nets incoherents",
        compare_money(
            paid_totals.loc[valid],
            numeric(
                paid_orders.loc[valid, "order_total"]
            ),
        ).sum(),
    )


# ============================================================
# 5. LIVRAISONS
# ============================================================

def audit_shipments(data, simulation_end):

    print("\n=== LIVRAISONS ===")

    orders = data["orders"]
    shipments = data["shipments"]

    require_columns(
        shipments,
        [
            "order_id",
            "shipment_status",
            "shipping_date",
            "estimated_delivery_date",
            "actual_delivery_date",
            "is_late",
            "delivery_delay_days",
        ],
        "shipments",
    )

    add_check(
        "shipments",
        "Livraisons multiples par commande",
        shipments["order_id"].duplicated().sum(),
    )

    active_online = orders[
        (orders["sales_channel"] == "online")
        & (orders["order_status"] != "cancelled")
    ]

    add_check(
        "shipments",
        "Commandes en ligne sans livraison",
        (
            ~active_online["order_id"].isin(
                shipments["order_id"]
            )
        ).sum(),
    )

    order_info = orders.set_index("order_id")

    channels = shipments["order_id"].map(
        order_info["sales_channel"]
    )

    add_check(
        "shipments",
        "Livraisons de ventes en magasin",
        (channels != "online").sum(),
    )

    shipping_dates = dates(
        shipments["shipping_date"]
    )

    delivery_dates = dates(
        shipments["actual_delivery_date"]
    )

    estimated_dates = dates(
        shipments["estimated_delivery_date"]
    )

    order_dates = dates(
        shipments["order_id"].map(
            order_info["order_date"]
        )
    )

    add_check(
        "shipments",
        "Expeditions avant commande",
        (
            shipping_dates.notna()
            & (shipping_dates < order_dates)
        ).sum(),
    )

    add_check(
        "shipments",
        "Livraisons avant expedition",
        (
            delivery_dates.notna()
            & shipping_dates.notna()
            & (delivery_dates < shipping_dates)
        ).sum(),
    )

    delivered = (
        shipments["shipment_status"] == "delivered"
    )

    add_check(
        "shipments",
        "Commandes livrees sans date",
        (
            delivered & delivery_dates.isna()
        ).sum(),
    )

    add_check(
        "shipments",
        "Livraisons futures",
        (
            delivery_dates.notna()
            & (delivery_dates > simulation_end)
        ).sum(),
    )

    # Recalcul du retard
    calculated_delay = (
        delivery_dates - estimated_dates
    ).dt.days.clip(lower=0)

    recorded_delay = numeric(
        shipments["delivery_delay_days"]
    )

    add_check(
        "shipments",
        "Retards incoherents",
        (
            delivered
            & compare_money(
                calculated_delay,
                recorded_delay,
                tolerance=0,
            )
        ).sum(),
    )


# ============================================================
# 6. RECLAMATIONS
# ============================================================

def audit_complaints(data, simulation_end):

    print("\n=== RECLAMATIONS ===")

    complaints = data["complaints"]
    orders = data["orders"]

    require_columns(
        complaints,
        [
            "order_id",
            "customer_id",
            "complaint_date",
            "complaint_status",
            "resolution_date",
        ],
        "complaints",
    )

    order_info = orders.set_index("order_id")

    complaint_dates = dates(
        complaints["complaint_date"]
    )

    order_dates = dates(
        complaints["order_id"].map(
            order_info["order_date"]
        )
    )

    resolution_dates = dates(
        complaints["resolution_date"]
    )

    add_check(
        "complaints",
        "Reclamations avant commande",
        (complaint_dates < order_dates).sum(),
    )

    add_check(
        "complaints",
        "Reclamations futures",
        (complaint_dates > simulation_end).sum(),
    )

    add_check(
        "complaints",
        "Resolutions avant reclamation",
        (
            resolution_dates.notna()
            & (resolution_dates < complaint_dates)
        ).sum(),
    )

    add_check(
        "complaints",
        "Resolutions futures",
        (
            resolution_dates.notna()
            & (resolution_dates > simulation_end)
        ).sum(),
    )

    resolved = (
        complaints["complaint_status"] == "resolved"
    )

    add_check(
        "complaints",
        "Reclamations resolues sans date",
        (
            resolved & resolution_dates.isna()
        ).sum(),
    )


# ============================================================
# 7. STOCKS
# ============================================================

def audit_inventory(data):

    print("\n=== STOCKS ===")

    inventory = data["inventory"]

    require_columns(
        inventory,
        [
            "store_id",
            "product_id",
            "stock_quantity",
            "reorder_point",
            "reorder_quantity",
            "stock_status",
        ],
        "inventory",
    )

    add_check(
        "inventory",
        "Couples magasin-produit dupliques",
        inventory.duplicated(
            ["store_id", "product_id"]
        ).sum(),
    )

    quantity = numeric(
        inventory["stock_quantity"]
    )

    threshold = numeric(
        inventory["reorder_point"]
    )

    reorder_quantity = numeric(
        inventory["reorder_quantity"]
    )

    add_check(
        "inventory",
        "Stocks negatifs",
        (quantity < 0).sum(),
    )

    add_check(
        "inventory",
        "Seuils invalides",
        (threshold <= 0).sum(),
    )

    add_check(
        "inventory",
        "Quantites de reapprovisionnement invalides",
        (reorder_quantity <= 0).sum(),
    )

    expected_status = np.select(
        [
            quantity == 0,
            quantity > threshold * 4,
            quantity <= threshold,
        ],
        [
            "out_of_stock",
            "overstock",
            "low_stock",
        ],
        default="normal",
    )

    add_check(
        "inventory",
        "Statuts de stock incoherents",
        (
            inventory["stock_status"].to_numpy()
            != expected_status
        ).sum(),
    )


# ============================================================
# 8. RAPPORT FINAL
# ============================================================

def save_report(config):

    report_dir = (
        ROOT / "reports" / "data_quality"
    )

    report_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    results_df = pd.DataFrame(results)

    csv_path = report_dir / "audit_results.csv"

    results_df.to_csv(
        csv_path,
        index=False,
        encoding="utf-8",
    )

    total_checks = len(results_df)

    passed_checks = int(
        (results_df["status"] == "PASS").sum()
    )

    failed_checks = int(
        (results_df["status"] == "FAIL").sum()
    )

    total_errors = int(
        results_df["errors"].sum()
    )

    summary = [
        "CONSULTAI 360 - DATA QUALITY AUDIT",
        "=" * 55,
        f"Controles executes : {total_checks}",
        f"Controles reussis : {passed_checks}",
        f"Controles echoues : {failed_checks}",
        f"Anomalies detectees : {total_errors}",
        "",
        "RESULTAT GLOBAL",
        "PASS" if failed_checks == 0 else "FAIL",
    ]

    txt_path = report_dir / "audit_summary.txt"

    txt_path.write_text(
        "\n".join(summary),
        encoding="utf-8",
    )

    print("\n" + "=" * 55)
    print("RESULTAT GLOBAL")
    print("=" * 55)

    print(f"Controles executes : {total_checks}")
    print(f"Controles reussis : {passed_checks}")
    print(f"Controles echoues : {failed_checks}")
    print(f"Anomalies detectees : {total_errors}")

    print("\nRapports :")
    print(csv_path)
    print(txt_path)

    if failed_checks > 0:
        print("\nAUDIT : FAIL")
    else:
        print("\nAUDIT : PASS")

    return failed_checks


# ============================================================
# MAIN
# ============================================================

def main():

    print("CONSULTAI 360 - AUDIT GLOBAL")
    print("=" * 55)

    config, data = load_data()

    simulation_end = pd.Timestamp(
        str(config["generation"]["end_date"])
    )

    audit_structure(data)
    audit_foreign_keys(data)
    audit_orders(data)
    audit_payments(data)
    audit_shipments(data, simulation_end)
    audit_complaints(data, simulation_end)
    audit_inventory(data)

    failed_checks = save_report(config)

    if failed_checks > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
