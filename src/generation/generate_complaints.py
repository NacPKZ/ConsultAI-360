from pathlib import Path

import numpy as np
import pandas as pd
import yaml

# ============================================================
# 1. CONFIGURATION
# ============================================================


def load_config():
    with Path("config/generation.yaml").open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


# ============================================================
# 2. GENERATION DES RECLAMATIONS
# ============================================================


def generate_complaints(config):

    seed = int(config["generation"]["seed"]) + 8
    rng = np.random.default_rng(seed)

    data_dir = Path(config["output"]["directory"])

    orders = pd.read_csv(data_dir / "orders.csv", parse_dates=["order_date"])

    shipments = pd.read_csv(
        data_dir / "shipments.csv", parse_dates=["actual_delivery_date"]
    )

    payments = pd.read_csv(data_dir / "payments.csv")

    simulation_end = pd.Timestamp(str(config["generation"]["end_date"]))

    # --------------------------------------------------------
    # Verification des donnees sources
    # --------------------------------------------------------

    required_orders = {
        "order_id",
        "customer_id",
        "order_date",
        "order_status",
        "sales_channel",
    }

    if not required_orders.issubset(orders.columns):
        raise ValueError("Colonnes manquantes dans orders.csv")

    required_shipments = {
        "order_id",
        "shipment_status",
        "is_late",
        "actual_delivery_date",
    }

    if not required_shipments.issubset(shipments.columns):
        raise ValueError("Colonnes manquantes dans shipments.csv")

    if orders["order_id"].duplicated().any():
        raise ValueError("Commandes dupliquees")

    if shipments["order_id"].duplicated().any():
        raise ValueError("Livraisons dupliquees")

    # --------------------------------------------------------
    # Preparation des informations logistiques
    # --------------------------------------------------------

    shipment_info = shipments[
        ["order_id", "shipment_status", "is_late", "actual_delivery_date"]
    ].copy()

    data = orders.merge(shipment_info, on="order_id", how="left", validate="one_to_one")

    # Identification des commandes remboursees
    refunded_orders = set(
        payments.loc[payments["payment_status"] == "refunded", "order_id"].astype(str)
    )

    records = []
    complaint_counter = 1

    # --------------------------------------------------------
    # Parcours des commandes
    # --------------------------------------------------------

    for order in data.to_dict("records"):
        order_id = str(order["order_id"])
        customer_id = str(order["customer_id"])
        order_status = str(order["order_status"])
        channel = str(order["sales_channel"])

        order_date = pd.Timestamp(str(order["order_date"]))

        shipment_status = str(order["shipment_status"])

        late_value = order["is_late"]

        is_late = pd.notna(late_value) and float(str(late_value)) == 1.0

        # ----------------------------------------------------
        # Probabilite de reclamation
        # ----------------------------------------------------

        complaint_probability = 0.07

        if is_late:
            complaint_probability = 0.25

        elif order_status == "cancelled":
            complaint_probability = 0.12

        elif channel == "in_store":
            complaint_probability = 0.04

        if rng.random() >= complaint_probability:
            continue

        # ----------------------------------------------------
        # Selection du motif
        # ----------------------------------------------------

        if order_status == "cancelled":
            if order_id in refunded_orders:
                reasons = ["refund_issue", "customer_service"]
                weights = [0.80, 0.20]

            else:
                reasons = ["customer_service"]
                weights = [1.0]

        elif is_late:
            reasons = ["late_delivery", "damaged_product", "customer_service"]

            weights = [0.75, 0.15, 0.10]

        elif channel == "in_store":
            reasons = ["product_quality", "wrong_product", "customer_service"]

            weights = [0.55, 0.20, 0.25]

        elif shipment_status == "delivered":
            reasons = [
                "damaged_product",
                "wrong_product",
                "product_quality",
                "customer_service",
            ]

            weights = [0.35, 0.20, 0.25, 0.20]

        else:
            reasons = ["customer_service"]
            weights = [1.0]

        reason = str(rng.choice(reasons, p=weights))

        # ----------------------------------------------------
        # Date de reclamation
        # ----------------------------------------------------

        if (
            reason
            in {"late_delivery", "damaged_product", "wrong_product", "product_quality"}
            and shipment_status == "delivered"
        ):
            delivery_date = pd.Timestamp(str(order["actual_delivery_date"]))

            earliest_date = delivery_date

        else:
            earliest_date = order_date

        days_after = int(rng.integers(0, 15))

        complaint_date = earliest_date + pd.Timedelta(days=days_after)

        # Pas de reclamation apres la fin de simulation
        if complaint_date > simulation_end:
            continue

        # ----------------------------------------------------
        # Gravite
        # ----------------------------------------------------

        severity = str(rng.choice(["low", "medium", "high"], p=[0.40, 0.45, 0.15]))

        # ----------------------------------------------------
        # Statut de traitement
        # ----------------------------------------------------

        age_days = int((simulation_end - complaint_date).days)

        if age_days <= 3:
            status = str(
                rng.choice(["open", "in_progress", "resolved"], p=[0.65, 0.30, 0.05])
            )

        elif age_days <= 14:
            status = str(
                rng.choice(["open", "in_progress", "resolved"], p=[0.15, 0.45, 0.40])
            )

        else:
            status = str(
                rng.choice(["open", "in_progress", "resolved"], p=[0.05, 0.15, 0.80])
            )

        # ----------------------------------------------------
        # Date de resolution
        # ----------------------------------------------------

        resolution_date = pd.NaT

        if status == "resolved":
            max_resolution_days = min(age_days, 21)

            resolution_days = int(rng.integers(0, max_resolution_days + 1))

            resolution_date = complaint_date + pd.Timedelta(days=resolution_days)

        # ----------------------------------------------------
        # Satisfaction client apres reclamation
        # ----------------------------------------------------

        satisfaction_score = None

        if status == "resolved":
            satisfaction_score = int(
                rng.choice([1, 2, 3, 4, 5], p=[0.12, 0.18, 0.30, 0.25, 0.15])
            )

        # ----------------------------------------------------
        # Enregistrement
        # ----------------------------------------------------

        records.append(
            {
                "complaint_id": f"CMP{complaint_counter:07d}",
                "order_id": order_id,
                "customer_id": customer_id,
                "complaint_date": complaint_date,
                "complaint_reason": reason,
                "severity": severity,
                "complaint_status": status,
                "resolution_date": resolution_date,
                "satisfaction_score": satisfaction_score,
            }
        )

        complaint_counter += 1

    complaints = pd.DataFrame(records)

    return orders, shipments, complaints


# ============================================================
# 3. CONTROLES QUALITE
# ============================================================


def validate_complaints(orders, shipments, complaints, config):

    simulation_end = pd.Timestamp(str(config["generation"]["end_date"]))

    duplicate_ids = int(complaints["complaint_id"].duplicated().sum())

    duplicate_orders = int(complaints["order_id"].duplicated().sum())

    unknown_orders = int((~complaints["order_id"].isin(orders["order_id"])).sum())

    order_reference = orders.set_index("order_id")

    reference_dates = complaints["order_id"].map(order_reference["order_date"])

    early_complaints = int((complaints["complaint_date"] < reference_dates).sum())

    future_complaints = int((complaints["complaint_date"] > simulation_end).sum())

    resolved = complaints["complaint_status"] == "resolved"

    missing_resolutions = int(complaints.loc[resolved, "resolution_date"].isna().sum())

    unresolved = ~resolved

    unexpected_resolutions = int(
        complaints.loc[unresolved, "resolution_date"].notna().sum()
    )

    invalid_resolution_order = int(
        (
            complaints.loc[resolved, "resolution_date"]
            < complaints.loc[resolved, "complaint_date"]
        ).sum()
    )

    future_resolutions = int(
        (complaints.loc[resolved, "resolution_date"] > simulation_end).sum()
    )

    invalid_scores = int(
        (~complaints["satisfaction_score"].dropna().between(1, 5)).sum()
    )

    # --------------------------------------------------------
    # Controle des reclamations pour retard
    # --------------------------------------------------------

    late_orders = set(
        shipments.loc[
            (shipments["shipment_status"] == "delivered") & (shipments["is_late"] == 1),
            "order_id",
        ].astype(str)
    )

    late_complaints = complaints[complaints["complaint_reason"] == "late_delivery"]

    invalid_late_complaints = int(
        (~late_complaints["order_id"].isin(late_orders)).sum()
    )

    # --------------------------------------------------------
    # Rapport
    # --------------------------------------------------------

    checks = {
        "Identifiants dupliques": duplicate_ids,
        "Reclamations multiples par commande": duplicate_orders,
        "Commandes inexistantes": unknown_orders,
        "Reclamations avant commande": early_complaints,
        "Reclamations apres simulation": future_complaints,
        "Reclamations resolues sans date": missing_resolutions,
        "Reclamations ouvertes avec resolution": unexpected_resolutions,
        "Resolution avant reclamation": invalid_resolution_order,
        "Resolution apres simulation": future_resolutions,
        "Scores de satisfaction invalides": invalid_scores,
        "Retards sans retard reel": invalid_late_complaints,
    }

    print("\nCONTROLES RECLAMATIONS")
    print("=" * 55)

    for name, value in checks.items():
        print(f"{name} : {value}")

    if any(value != 0 for value in checks.values()):
        raise ValueError("Echec des controles des reclamations")


# ============================================================
# 4. EXECUTION PRINCIPALE
# ============================================================


def main():

    config = load_config()

    orders, shipments, complaints = generate_complaints(config)

    validate_complaints(orders, shipments, complaints, config)

    output_dir = Path(config["output"]["directory"])

    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "complaints.csv"

    complaints.to_csv(output_path, index=False, encoding=config["output"]["encoding"])

    print("\nCONSULTAI 360 - COMPLAINTS GENERATION")
    print("=" * 55)

    print(f"Commandes : {len(orders):,}")
    print(f"Reclamations : {len(complaints):,}")

    print("\nMOTIFS")
    print(complaints["complaint_reason"].value_counts().to_string())

    print("\nSTATUTS")
    print(complaints["complaint_status"].value_counts().to_string())

    print("\nGRAVITE")
    print(complaints["severity"].value_counts().to_string())

    print("\nFICHIER CREE")
    print(output_path)

    print("\nGENERATION TERMINEE")


if __name__ == "__main__":
    main()
