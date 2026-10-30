from pathlib import Path

import numpy as np
import pandas as pd
import yaml


def load_config():
    with Path("config/generation.yaml").open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def generate_order_items(config):
    seed = config["generation"]["seed"]
    rng = np.random.default_rng(seed + 5)

    data_dir = Path(config["output"]["directory"])

    orders = pd.read_csv(data_dir / "orders.csv")
    products = pd.read_csv(data_dir / "products.csv")

    required_product_columns = {"product_id", "base_price", "unit_cost"}

    if not required_product_columns.issubset(products.columns):
        raise ValueError("Colonnes manquantes dans products.csv")

    product_ids = products["product_id"].to_numpy()
    product_prices = products["base_price"].to_numpy(dtype=float)

    if len(products) < 8:
        raise ValueError("Nombre de produits insuffisant")

    if (product_prices <= 0).any():
        raise ValueError("Prix produits invalides")

    basket_config = config["orders"]["basket"]

    min_items = int(basket_config["min_items"])
    max_items = int(basket_config["max_items"])

    if not (1 <= min_items <= max_items <= len(products)):
        raise ValueError("Configuration panier invalide")

    # Les petits paniers sont plus fréquents.
    possible_sizes = np.arange(min_items, max_items + 1)

    size_weights = 1 / possible_sizes.astype(float) ** 1.5
    size_weights /= size_weights.sum()

    records = []
    item_counter = 1

    for order in orders.itertuples(index=False):
        basket_size = int(rng.choice(possible_sizes, p=size_weights))

        selected_indices = rng.choice(len(products), size=basket_size, replace=False)

        for product_index in selected_indices:
            product_id = product_ids[product_index]
            base_price = product_prices[product_index]

            # Quantités : principalement 1 article.
            quantity = int(rng.choice([1, 2, 3, 4], p=[0.75, 0.17, 0.06, 0.02]))

            # Prix transactionnel légèrement variable.
            price_factor = rng.uniform(0.95, 1.05)

            unit_price = round(float(base_price * price_factor), 2)

            # 65 % des lignes sans remise.
            discount_rate = float(
                rng.choice(
                    [0.00, 0.05, 0.10, 0.15, 0.20, 0.30],
                    p=[0.65, 0.10, 0.10, 0.07, 0.05, 0.03],
                )
            )

            gross_amount = round(unit_price * quantity, 2)

            discount_amount = round(gross_amount * discount_rate, 2)

            line_total = round(gross_amount - discount_amount, 2)

            records.append(
                {
                    "order_item_id": f"ITM{item_counter:07d}",
                    "order_id": order.order_id,
                    "product_id": product_id,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount_amount": discount_amount,
                    "line_total": line_total,
                }
            )

            item_counter += 1

    order_items = pd.DataFrame(records)

    # Contrôles automatiques
    if order_items["order_item_id"].duplicated().any():
        raise ValueError("Identifiants de lignes dupliqués")

    if (order_items["quantity"] <= 0).any():
        raise ValueError("Quantités invalides")

    if (order_items["line_total"] < 0).any():
        raise ValueError("Montants négatifs")

    if order_items.duplicated(subset=["order_id", "product_id"]).any():
        raise ValueError("Produit répété dans une même commande")

    return orders, order_items


def main():
    config = load_config()

    orders, order_items = generate_order_items(config)

    output_dir = Path(config["output"]["directory"])

    # Calcul du montant total par commande
    totals = order_items.groupby("order_id")["line_total"].sum().round(2)

    orders["order_total"] = orders["order_id"].map(totals).round(2)

    if orders["order_total"].isna().any():
        raise ValueError("Certaines commandes n'ont pas de montant")

    # Sauvegarde
    order_items.to_csv(
        output_dir / "order_items.csv",
        index=False,
        encoding=config["output"]["encoding"],
    )

    orders.to_csv(
        output_dir / "orders.csv", index=False, encoding=config["output"]["encoding"]
    )

    print("\nCONSULTAI 360 — ORDER ITEMS")
    print("-" * 45)

    print(f"Commandes : {len(orders):,}")
    print(f"Lignes générées : {len(order_items):,}")

    print("Articles vendus :", f"{order_items['quantity'].sum():,}")

    print("Panier moyen HT :", f"{orders['order_total'].mean():,.2f} €")

    # CA réalisé : exclusion des commandes annulées
    valid_orders = orders[orders["order_status"] != "cancelled"]

    print(
        "CA commercial hors annulations :",
        f"{valid_orders['order_total'].sum():,.2f} €",
    )

    print("\nFichiers mis à jour :")
    print(output_dir / "order_items.csv")
    print(output_dir / "orders.csv")

    print("\nAPERÇU :")
    print(order_items.head().to_string(index=False))


if __name__ == "__main__":
    main()
