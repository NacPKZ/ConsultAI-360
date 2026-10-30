from pathlib import Path

import numpy as np
import pandas as pd
import yaml

# ============================================================
# 1. CONFIGURATION
# ============================================================


def load_config():
    config_path = Path("config/generation.yaml")

    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


# ============================================================
# 2. GENERATION DES PAIEMENTS
# ============================================================


def generate_payments(config):

    seed = int(config["generation"]["seed"]) + 6
    rng = np.random.default_rng(seed)

    data_dir = Path(config["output"]["directory"])

    orders = pd.read_csv(data_dir / "orders.csv", parse_dates=["order_date"])

    # Verification des colonnes obligatoires
    required_columns = {"order_id", "order_date", "order_status", "order_total"}

    missing_columns = required_columns - set(orders.columns)

    if missing_columns:
        raise ValueError(f"Colonnes manquantes : {missing_columns}")

    if orders["order_id"].duplicated().any():
        raise ValueError("Commandes dupliquees")

    if orders["order_total"].isna().any():
        raise ValueError("Montants manquants")

    if (orders["order_total"] <= 0).any():
        raise ValueError("Montants invalides")

    if orders["order_date"].isna().any():
        raise ValueError("Dates manquantes")

    # Moyens de paiement
    methods = ["credit_card", "debit_card", "paypal", "bank_transfer", "installments"]

    method_weights = [0.45, 0.25, 0.15, 0.10, 0.05]

    records = []
    payment_counter = 1

    # --------------------------------------------------------
    # Fonction d'ajout d'une transaction
    # --------------------------------------------------------

    def add_payment(
        order_id: str,
        method: str,
        status: str,
        amount: float,
        payment_date: pd.Timestamp,
    ):

        nonlocal payment_counter

        records.append(
            {
                "payment_id": f"PAY{payment_counter:07d}",
                "order_id": order_id,
                "payment_method": method,
                "payment_status": status,
                "payment_amount": round(amount, 2),
                "payment_date": payment_date,
            }
        )

        payment_counter += 1

    # --------------------------------------------------------
    # Parcours des commandes
    # --------------------------------------------------------

    for order in orders.to_dict("records"):
        order_id = str(order["order_id"])
        order_status = str(order["order_status"])

        amount = float(str(order["order_total"]))

        order_date = pd.Timestamp(str(order["order_date"]))

        method = str(rng.choice(methods, p=method_weights))

        payment_date = order_date

        # ----------------------------------------------------
        # CAS 1 : COMMANDE ANNULEE
        # ----------------------------------------------------

        if order_status == "cancelled":
            # 65 % : annulation avant encaissement
            if rng.random() < 0.65:
                add_payment(
                    order_id=order_id,
                    method=method,
                    status="cancelled",
                    amount=0.0,
                    payment_date=payment_date,
                )

            # 35 % : paiement puis remboursement
            else:
                add_payment(
                    order_id=order_id,
                    method=method,
                    status="paid",
                    amount=amount,
                    payment_date=payment_date,
                )

                refund_days = int(rng.integers(1, 8))

                refund_date = pd.Timestamp(str(payment_date)) + pd.Timedelta(
                    days=refund_days
                )

                add_payment(
                    order_id=order_id,
                    method=method,
                    status="refunded",
                    amount=-amount,
                    payment_date=refund_date,
                )

        # ----------------------------------------------------
        # CAS 2 : COMMANDE NON ANNULEE
        # ----------------------------------------------------

        else:
            # 4 % : premier paiement refuse
            if rng.random() < 0.04:
                add_payment(
                    order_id=order_id,
                    method=method,
                    status="failed",
                    amount=0.0,
                    payment_date=payment_date,
                )

            # Paiement finalement accepte
            add_payment(
                order_id=order_id,
                method=method,
                status="paid",
                amount=amount,
                payment_date=payment_date,
            )

    payments = pd.DataFrame(records)

    return orders, payments


# ============================================================
# 3. CONTROLES DE QUALITE
# ============================================================


def validate_payments(orders, payments):

    # Controle 1 : identifiants uniques
    duplicated_payments = int(payments["payment_id"].duplicated().sum())

    # Controle 2 : commandes existantes
    invalid_orders = int((~payments["order_id"].isin(orders["order_id"])).sum())

    # Controle 3 : dates de paiement
    payment_dates = pd.to_datetime(payments["payment_date"])

    order_dates = orders.set_index("order_id")["order_date"]

    reference_dates = pd.to_datetime(payments["order_id"].map(order_dates))

    invalid_dates = int((payment_dates < reference_dates).sum())

    # Controle 4 : encaissements nets
    net_payments = payments.groupby("order_id")["payment_amount"].sum().round(2)

    control = orders[["order_id", "order_status", "order_total"]].copy()

    control["net_paid"] = control["order_id"].map(net_payments).fillna(0).round(2)

    # Controle 5 : commandes annulees
    cancelled = control["order_status"] == "cancelled"

    cancelled_errors = int((control.loc[cancelled, "net_paid"].abs() > 0.001).sum())

    # Controle 6 : commandes actives
    active = ~cancelled

    differences = (
        control.loc[active, "net_paid"] - control.loc[active, "order_total"]
    ).abs()

    financial_errors = int((differences > 0.001).sum())

    # Controle 7 : remboursements
    refunded = payments["payment_status"] == "refunded"

    invalid_refunds = int((payments.loc[refunded, "payment_amount"] >= 0).sum())

    # --------------------------------------------------------
    # Affichage des controles
    # --------------------------------------------------------

    print("\nCONTROLES FINANCIERS")
    print("=" * 50)

    print("Paiements dupliques :", duplicated_payments)
    print("Commandes inexistantes :", invalid_orders)
    print("Dates invalides :", invalid_dates)
    print("Annulations avec encaissement :", cancelled_errors)
    print("Ecarts financiers :", financial_errors)
    print("Remboursements invalides :", invalid_refunds)

    print("\nEncaissement net total :", f"{control['net_paid'].sum():,.2f} EUR")

    # Bloquer la sauvegarde si anomalie
    errors = [
        duplicated_payments,
        invalid_orders,
        invalid_dates,
        cancelled_errors,
        financial_errors,
        invalid_refunds,
    ]

    if any(error > 0 for error in errors):
        raise ValueError("Echec des controles financiers")


# ============================================================
# 4. EXECUTION PRINCIPALE
# ============================================================


def main():

    config = load_config()

    orders, payments = generate_payments(config)

    # Validation avant sauvegarde
    validate_payments(orders, payments)

    output_dir = Path(config["output"]["directory"])

    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "payments.csv"

    payments.to_csv(output_path, index=False, encoding=config["output"]["encoding"])

    # --------------------------------------------------------
    # Rapport final
    # --------------------------------------------------------

    print("\nCONSULTAI 360 - PAYMENTS GENERATION")
    print("=" * 50)

    print(f"Commandes : {len(orders):,}")
    print(f"Transactions : {len(payments):,}")

    print("\nREPARTITION DES STATUTS")
    print(payments["payment_status"].value_counts().to_string())

    print("\nREPARTITION DES MOYENS DE PAIEMENT")
    print(payments["payment_method"].value_counts().to_string())

    print("\nAPERCU DES TRANSACTIONS")
    print(payments.head(10).to_string(index=False))

    print("\nFICHIER CREE")
    print(output_path)

    print("\nGENERATION TERMINEE")


# ============================================================
# 5. LANCEMENT
# ============================================================

if __name__ == "__main__":
    main()
