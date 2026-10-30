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
# 2. GENERATION DES STOCKS
# ============================================================


def generate_inventory(config):

    seed = int(config["generation"]["seed"]) + 9
    rng = np.random.default_rng(seed)

    data_dir = Path(config["output"]["directory"])

    stores = pd.read_csv(data_dir / "stores.csv")

    products = pd.read_csv(data_dir / "products.csv")

    simulation_end = pd.Timestamp(str(config["generation"]["end_date"]))

    # --------------------------------------------------------
    # Verification des sources
    # --------------------------------------------------------

    required_stores = {"store_id", "store_size_m2"}

    required_products = {"product_id", "unit_cost"}

    if not required_stores.issubset(stores.columns):
        raise ValueError("Colonnes manquantes dans stores.csv")

    if not required_products.issubset(products.columns):
        raise ValueError("Colonnes manquantes dans products.csv")

    if stores["store_id"].duplicated().any():
        raise ValueError("Magasins dupliques")

    if products["product_id"].duplicated().any():
        raise ValueError("Produits dupliques")

    if (stores["store_size_m2"] <= 0).any():
        raise ValueError("Surfaces de magasins invalides")

    if (products["unit_cost"] <= 0).any():
        raise ValueError("Couts unitaires invalides")

    # --------------------------------------------------------
    # Preparation des donnees
    # --------------------------------------------------------

    store_ids = stores["store_id"].astype(str).to_numpy()

    store_sizes = stores["store_size_m2"].to_numpy(dtype=float)

    product_ids = products["product_id"].astype(str).to_numpy()

    n_stores = len(stores)
    n_products = len(products)

    n_rows = n_stores * n_products

    # --------------------------------------------------------
    # Construction des couples magasin-produit
    # --------------------------------------------------------

    inventory_store_ids = np.repeat(store_ids, n_products)

    inventory_product_ids = np.tile(product_ids, n_stores)

    inventory_store_sizes = np.repeat(store_sizes, n_products)

    # --------------------------------------------------------
    # Capacite relative des magasins
    # --------------------------------------------------------

    median_store_size = float(np.median(store_sizes))

    capacity_factor = np.clip(inventory_store_sizes / median_store_size, 0.5, 2.0)

    # --------------------------------------------------------
    # Seuils de reapprovisionnement
    # --------------------------------------------------------

    reorder_point = rng.integers(5, 26, size=n_rows)

    reorder_point = np.maximum(1, np.rint(reorder_point * capacity_factor).astype(int))

    reorder_quantity = np.maximum(
        1, np.rint(reorder_point * rng.uniform(1.5, 3.0, size=n_rows)).astype(int)
    )

    # --------------------------------------------------------
    # Generation des quantites disponibles
    # --------------------------------------------------------

    stock_quantity = rng.poisson(lam=reorder_point * 1.8).astype(int)

    # Introduction de situations commerciales
    scenario = rng.choice(
        ["normal", "stockout", "low", "overstock"],
        size=n_rows,
        p=[0.78, 0.05, 0.12, 0.05],
    )

    stockout_mask = scenario == "stockout"
    low_mask = scenario == "low"
    overstock_mask = scenario == "overstock"

    # Ruptures
    stock_quantity[stockout_mask] = 0

    # Stocks faibles
    stock_quantity[low_mask] = rng.integers(1, 5, size=int(low_mask.sum()))

    # Surstocks
    stock_quantity[overstock_mask] = reorder_point[overstock_mask] * rng.integers(
        5, 9, size=int(overstock_mask.sum())
    )

    # --------------------------------------------------------
    # Classification des stocks
    # --------------------------------------------------------

    stock_status = np.full(n_rows, "normal", dtype=object)

    stock_status[stock_quantity == 0] = "out_of_stock"

    stock_status[(stock_quantity > 0) & (stock_quantity <= reorder_point)] = "low_stock"

    stock_status[stock_quantity > reorder_point * 4] = "overstock"

    # --------------------------------------------------------
    # Dates de reapprovisionnement
    # --------------------------------------------------------

    days_since_restock = rng.integers(0, 91, size=n_rows)

    last_restock_dates = simulation_end - pd.to_timedelta(days_since_restock, unit="D")

    # --------------------------------------------------------
    # Construction du DataFrame
    # --------------------------------------------------------

    inventory = pd.DataFrame(
        {
            "inventory_id": [f"INV{i:07d}" for i in range(1, n_rows + 1)],
            "store_id": inventory_store_ids,
            "product_id": inventory_product_ids,
            "stock_quantity": stock_quantity,
            "reorder_point": reorder_point,
            "reorder_quantity": reorder_quantity,
            "stock_status": stock_status,
            "last_restock_date": last_restock_dates,
        }
    )

    return stores, products, inventory


# ============================================================
# 3. CONTROLES QUALITE
# ============================================================


def validate_inventory(stores, products, inventory, config):

    simulation_end = pd.Timestamp(str(config["generation"]["end_date"]))

    expected_rows = len(stores) * len(products)

    duplicate_ids = int(inventory["inventory_id"].duplicated().sum())

    duplicate_pairs = int(inventory.duplicated(["store_id", "product_id"]).sum())

    unknown_stores = int((~inventory["store_id"].isin(stores["store_id"])).sum())

    unknown_products = int(
        (~inventory["product_id"].isin(products["product_id"])).sum()
    )

    negative_stock = int((inventory["stock_quantity"] < 0).sum())

    invalid_reorder_points = int((inventory["reorder_point"] <= 0).sum())

    invalid_reorder_quantities = int((inventory["reorder_quantity"] <= 0).sum())

    future_restocks = int((inventory["last_restock_date"] > simulation_end).sum())

    # --------------------------------------------------------
    # Verification des statuts
    # --------------------------------------------------------

    quantity = inventory["stock_quantity"]
    threshold = inventory["reorder_point"]
    status = inventory["stock_status"]

    expected_status = np.select(
        [quantity == 0, quantity > threshold * 4, quantity <= threshold],
        ["out_of_stock", "overstock", "low_stock"],
        default="normal",
    )

    invalid_statuses = int((status.to_numpy() != expected_status).sum())

    # --------------------------------------------------------
    # Rapport des controles
    # --------------------------------------------------------

    checks = {
        "Nombre de lignes incorrect": abs(len(inventory) - expected_rows),
        "Identifiants dupliques": duplicate_ids,
        "Couples magasin-produit dupliques": duplicate_pairs,
        "Magasins inexistants": unknown_stores,
        "Produits inexistants": unknown_products,
        "Stocks negatifs": negative_stock,
        "Seuils invalides": invalid_reorder_points,
        "Quantites de commande invalides": invalid_reorder_quantities,
        "Reapprovisionnements futurs": future_restocks,
        "Statuts incoherents": invalid_statuses,
    }

    print("\nCONTROLES DES STOCKS")
    print("=" * 55)

    for name, value in checks.items():
        print(f"{name} : {value}")

    if any(value != 0 for value in checks.values()):
        raise ValueError("Echec des controles de stocks")


# ============================================================
# 4. EXECUTION PRINCIPALE
# ============================================================


def main():

    config = load_config()

    stores, products, inventory = generate_inventory(config)

    validate_inventory(stores, products, inventory, config)

    output_dir = Path(config["output"]["directory"])

    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "inventory.csv"

    inventory.to_csv(output_path, index=False, encoding=config["output"]["encoding"])

    print("\nCONSULTAI 360 - INVENTORY GENERATION")
    print("=" * 55)

    print(f"Magasins : {len(stores):,}")
    print(f"Produits : {len(products):,}")
    print(f"Lignes de stock : {len(inventory):,}")

    print("\nREPARTITION DES STATUTS")

    print(inventory["stock_status"].value_counts().to_string())

    print("\nINDICATEURS")

    stockout_rate = inventory["stock_status"].eq("out_of_stock").mean() * 100

    overstock_rate = inventory["stock_status"].eq("overstock").mean() * 100

    print(f"Taux de rupture : {stockout_rate:.2f} %")
    print(f"Taux de surstock : {overstock_rate:.2f} %")

    print("\nFICHIER CREE")
    print(output_path)

    print("\nGENERATION TERMINEE")


if __name__ == "__main__":
    main()
