from pathlib import Path

import numpy as np
import pandas as pd
import yaml


class FenwickTree:
    """Structure pour sélectionner efficacement des clients pondérés."""

    def __init__(self, size):
        self.size = size
        self.tree = np.zeros(size + 1, dtype=float)

    def add(self, index, value):
        index += 1

        while index <= self.size:
            self.tree[index] += value
            index += index & -index

    def find_by_weight(self, target):
        """Renvoie l'index correspondant à un tirage pondéré."""
        index = 0
        bit = 1 << (self.size.bit_length() - 1)

        while bit:
            next_index = index + bit

            if next_index <= self.size and self.tree[next_index] <= target:
                target -= self.tree[next_index]
                index = next_index

            bit >>= 1

        return index


def load_config():
    with Path("config/generation.yaml").open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def generate_orders(config):
    rng = np.random.default_rng(config["generation"]["seed"] + 4)

    data_dir = Path(config["output"]["directory"])

    customers = pd.read_csv(
        data_dir / "customers.csv", parse_dates=["registration_date"]
    )

    stores = pd.read_csv(data_dir / "stores.csv", parse_dates=["opening_date"])

    n_orders = config["volumes"]["orders"]

    start_date = pd.Timestamp(config["generation"]["start_date"])
    end_date = pd.Timestamp(config["generation"]["end_date"])

    if start_date > end_date:
        raise ValueError("Période de simulation invalide")

    dates = pd.date_range(start_date, end_date, freq="D")

    seasonality = config["orders"]["monthly_seasonality"]

    date_weights = np.array([float(seasonality[date.month]) for date in dates])
    date_weights /= date_weights.sum()

    sampled_dates = pd.to_datetime(
        rng.choice(dates.to_numpy(), size=n_orders, p=date_weights)
    )

    online_share = float(config["orders"]["online_share"])

    channels = rng.choice(
        ["online", "in_store"], size=n_orders, p=[online_share, 1 - online_share]
    )

    loyalty_weights = config["orders"]["loyalty_purchase_weights"]

    customers["purchase_weight"] = (
        customers["loyalty_tier"].map(loyalty_weights).astype(float)
    )

    if customers["purchase_weight"].isna().any():
        raise ValueError("Niveau de fidélité non reconnu")

    customers = customers.sort_values("registration_date").reset_index(drop=True)

    customer_dates = customers["registration_date"].to_numpy(dtype="datetime64[ns]")
    customer_ids = customers["customer_id"].to_numpy()
    customer_weights = customers["purchase_weight"].to_numpy()

    tree = FenwickTree(len(customers))
    active_weight = 0.0
    next_customer = 0

    order_indices = np.argsort(sampled_dates.to_numpy())

    # Préparation des magasins
    stores = stores.sort_values("opening_date").reset_index(drop=True)

    store_dates = stores["opening_date"].to_numpy(dtype="datetime64[ns]")
    store_ids = stores["store_id"].to_numpy()
    store_sizes = stores["store_size_m2"].to_numpy(dtype=float)

    records = [None] * n_orders

    for order_index in order_indices:
        order_date = sampled_dates[order_index]
        order_date_np = np.datetime64(order_date)

        # Ajouter les clients inscrits à cette date
        while (
            next_customer < len(customers)
            and customer_dates[next_customer] <= order_date_np
        ):
            weight = customer_weights[next_customer]

            if weight <= 0:
                raise ValueError("Poids client invalide")

            tree.add(next_customer, weight)
            active_weight += weight
            next_customer += 1

        if active_weight <= 0:
            raise ValueError(f"Aucun client éligible au {order_date}")

        target = rng.random() * active_weight
        customer_index = tree.find_by_weight(target)

        customer_id = customer_ids[customer_index]

        channel = channels[order_index]
        store_id = None

        if channel == "in_store":
            eligible_count = np.searchsorted(store_dates, order_date_np, side="right")

            if eligible_count == 0:
                raise ValueError("Aucun magasin ouvert à la date de commande")

            eligible_sizes = store_sizes[:eligible_count]
            probabilities = eligible_sizes / eligible_sizes.sum()

            selected_store = rng.choice(eligible_count, p=probabilities)

            store_id = store_ids[selected_store]

        if channel == "in_store":
            statuses = ["completed", "cancelled"]
            probabilities = [0.98, 0.02]
        else:
            statuses = ["delivered", "shipped", "processing", "cancelled"]
            probabilities = [0.88, 0.06, 0.04, 0.02]

        status = rng.choice(statuses, p=probabilities)

        records[order_index] = {
            "order_id": f"ORD{order_index + 1:06d}",
            "customer_id": customer_id,
            "store_id": store_id,
            "order_date": order_date,
            "sales_channel": channel,
            "order_status": status,
            "order_total": None,
        }

    orders = pd.DataFrame(records)

    if len(orders) != n_orders:
        raise ValueError("Nombre de commandes incorrect")

    if orders["order_id"].duplicated().any():
        raise ValueError("Identifiants commandes dupliqués")

    if orders["customer_id"].isna().any():
        raise ValueError("Commande sans client")

    return orders


def main():
    config = load_config()

    orders = generate_orders(config)

    output_dir = Path(config["output"]["directory"])
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "orders.csv"

    orders.to_csv(output_path, index=False, encoding=config["output"]["encoding"])

    print("\nCONSULTAI 360 — ORDERS GENERATION")
    print("-" * 45)

    print(f"Commandes générées : {len(orders):,}")

    print("\nRépartition des canaux :")
    print(
        orders["sales_channel"]
        .value_counts(normalize=True)
        .mul(100)
        .round(2)
        .to_string()
    )

    print("\nRépartition des statuts :")
    print(orders["order_status"].value_counts().to_string())

    print("\nPériode :")
    print(orders["order_date"].min())
    print(orders["order_date"].max())

    print(f"\nFichier créé : {output_path}")
    print("\nAPERÇU :")
    print(orders.head().to_string(index=False))


if __name__ == "__main__":
    main()
