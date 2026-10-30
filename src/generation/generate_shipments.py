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
# 2. GENERATION DES LIVRAISONS
# ============================================================


def generate_shipments(config):

    rng = np.random.default_rng(int(config["generation"]["seed"]) + 7)

    data_dir = Path(config["output"]["directory"])

    orders = pd.read_csv(data_dir / "orders.csv", parse_dates=["order_date"])

    required = {"order_id", "order_date", "sales_channel", "order_status"}

    missing = required - set(orders.columns)

    if missing:
        raise ValueError(f"Colonnes manquantes : {missing}")

    if orders["order_id"].duplicated().any():
        raise ValueError("Commandes dupliquees")

    simulation_end = pd.Timestamp(str(config["generation"]["end_date"]))

    carriers = ["NexaLog", "RapidParcel", "EuroShip", "UrbanExpress"]

    carrier_weights = [0.35, 0.30, 0.20, 0.15]

    records = []
    shipment_counter = 1

    # --------------------------------------------------------
    # Parcours des commandes
    # --------------------------------------------------------

    for order in orders.to_dict("records"):
        order_id = str(order["order_id"])
        channel = str(order["sales_channel"])
        status = str(order["order_status"])

        order_date = pd.Timestamp(str(order["order_date"]))

        # Pas de livraison pour les achats en magasin
        if channel != "online":
            continue

        # Pas d'expedition pour les commandes annulees
        if status == "cancelled":
            continue

        carrier = str(rng.choice(carriers, p=carrier_weights))

        shipping_method = str(rng.choice(["standard", "express"], p=[0.80, 0.20]))

        # Delai de preparation : 0 a 2 jours
        preparation_days = int(rng.integers(0, 3))

        shipping_date = order_date + pd.Timedelta(days=preparation_days)

        # Livraison prevue
        if shipping_method == "express":
            planned_days = int(rng.integers(1, 4))
        else:
            planned_days = int(rng.integers(3, 8))

        estimated_date = shipping_date + pd.Timedelta(days=planned_days)

        # Simulation des retards
        is_delayed = bool(rng.random() < 0.15)

        if is_delayed:
            extra_days = int(rng.integers(1, 6))
        else:
            extra_days = 0

        actual_date = estimated_date + pd.Timedelta(days=extra_days)

        # ----------------------------------------------------
        # Statut selon la date de fin de simulation
        # ----------------------------------------------------

        if shipping_date > simulation_end:
            # Commande encore en preparation
            shipment_status = "processing"
            shipping_date_output = pd.NaT
            actual_date_output = pd.NaT

        elif actual_date > simulation_end:
            # Colis expedie mais pas encore livre
            shipment_status = "in_transit"
            shipping_date_output = shipping_date
            actual_date_output = pd.NaT

        else:
            shipment_status = "delivered"
            shipping_date_output = shipping_date
            actual_date_output = actual_date

        # ----------------------------------------------------
        # Retard uniquement pour les livraisons terminees
        # ----------------------------------------------------

        if shipment_status == "delivered":
            delay_days = max(
                0,
                (
                    pd.Timestamp(str(actual_date_output))
                    - pd.Timestamp(str(estimated_date))
                ).days,
            )
            late_flag = int(delay_days is not None and delay_days > 0)

        else:
            delay_days = None
            late_flag = None

        records.append(
            {
                "shipment_id": f"SHP{shipment_counter:07d}",
                "order_id": order_id,
                "carrier": carrier,
                "shipping_method": shipping_method,
                "shipping_date": shipping_date_output,
                "estimated_delivery_date": estimated_date,
                "actual_delivery_date": actual_date_output,
                "shipment_status": shipment_status,
                "delivery_delay_days": delay_days,
                "is_late": late_flag,
            }
        )

        shipment_counter += 1

    shipments = pd.DataFrame(records)

    return orders, shipments


# ============================================================
# 3. HARMONISATION DES STATUTS DES COMMANDES
# ============================================================


def update_order_statuses(orders, shipments):

    status_mapping = {
        "delivered": "delivered",
        "in_transit": "shipped",
        "processing": "processing",
    }

    shipment_status = shipments.set_index("order_id")["shipment_status"].map(
        status_mapping
    )

    online_active = (orders["sales_channel"] == "online") & (
        orders["order_status"] != "cancelled"
    )

    orders.loc[online_active, "order_status"] = orders.loc[
        online_active, "order_id"
    ].map(shipment_status)

    if orders["order_status"].isna().any():
        raise ValueError("Statuts de commandes manquants apres mise a jour")

    return orders


# ============================================================
# 4. CONTROLES QUALITE
# ============================================================


def validate_shipments(orders, shipments, config):

    simulation_end = pd.Timestamp(str(config["generation"]["end_date"]))

    duplicate_ids = int(shipments["shipment_id"].duplicated().sum())

    duplicate_orders = int(shipments["order_id"].duplicated().sum())

    unknown_orders = int((~shipments["order_id"].isin(orders["order_id"])).sum())

    order_reference = orders.set_index("order_id")

    shipment_channels = shipments["order_id"].map(order_reference["sales_channel"])

    store_shipments = int((shipment_channels != "online").sum())

    shipment_order_dates = shipments["order_id"].map(order_reference["order_date"])

    shipped = shipments["shipping_date"].notna()

    early_shipping = int(
        (
            shipments.loc[shipped, "shipping_date"] < shipment_order_dates.loc[shipped]
        ).sum()
    )

    delivered = shipments["shipment_status"] == "delivered"

    missing_delivery_dates = int(
        shipments.loc[delivered, "actual_delivery_date"].isna().sum()
    )

    future_deliveries = int(
        (shipments.loc[delivered, "actual_delivery_date"] > simulation_end).sum()
    )

    negative_delays = int((shipments["delivery_delay_days"].dropna() < 0).sum())

    print("\nCONTROLES LOGISTIQUES")
    print("=" * 50)

    checks = {
        "Identifiants dupliques": duplicate_ids,
        "Commandes expediees plusieurs fois": duplicate_orders,
        "Commandes inexistantes": unknown_orders,
        "Livraisons de ventes en magasin": store_shipments,
        "Expeditions avant commande": early_shipping,
        "Livraisons sans date": missing_delivery_dates,
        "Livraisons apres fin simulation": future_deliveries,
        "Retards negatifs": negative_delays,
    }

    for name, value in checks.items():
        print(f"{name} : {value}")

    if any(value != 0 for value in checks.values()):
        raise ValueError("Echec des controles logistiques")


# ============================================================
# 5. EXECUTION PRINCIPALE
# ============================================================


def main():

    config = load_config()

    orders, shipments = generate_shipments(config)

    orders = update_order_statuses(orders, shipments)

    validate_shipments(orders, shipments, config)

    output_dir = Path(config["output"]["directory"])

    output_dir.mkdir(parents=True, exist_ok=True)

    # Sauvegarde des livraisons
    shipments_path = output_dir / "shipments.csv"

    shipments.to_csv(shipments_path, index=False, encoding=config["output"]["encoding"])

    # Mise a jour des commandes
    orders_path = output_dir / "orders.csv"

    orders.to_csv(orders_path, index=False, encoding=config["output"]["encoding"])

    # Rapport
    print("\nCONSULTAI 360 - SHIPMENTS GENERATION")
    print("=" * 50)

    print(f"Commandes : {len(orders):,}")
    print(f"Livraisons : {len(shipments):,}")

    print("\nSTATUTS LOGISTIQUES")
    print(shipments["shipment_status"].value_counts().to_string())

    delivered = shipments[shipments["shipment_status"] == "delivered"]

    if not delivered.empty:
        late_rate = delivered["is_late"].mean() * 100

        print(f"\nTaux de retard : {late_rate:.2f} %")

    print("\nFICHIERS CREES / MIS A JOUR")
    print(shipments_path)
    print(orders_path)

    print("\nGENERATION TERMINEE")


if __name__ == "__main__":
    main()
