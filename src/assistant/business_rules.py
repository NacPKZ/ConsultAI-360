def build_business_facts(commercial: dict, logistique: dict) -> str:
    """Construit des constats métier à partir de KPI vérifiés."""

    commandes = commercial["commandes"]
    manquants = commercial["montants_manquants"]
    completude = commercial["taux_completude_pct"]
    panier = commercial["panier_moyen"]

    livraisons = logistique["livraisons_evaluables"]
    retards = logistique["retards"]
    taux_retard = logistique["taux_retard_pct"]

    if commandes == 0:
        return "Aucune commande disponible pour ce scénario."

    if completude is None:
        return "Impossible de calculer la complétude."

    facts = [
        f"Le scénario contient {commandes} commandes.",
        (
            f"{manquants} commandes présentent un montant manquant, "
            f"soit {100 - completude:.2f} % des commandes."
        ),
        (
            f"Le panier moyen est de {panier} € sur les commandes "
            "dont le montant est renseigné."
            if panier is not None
            else "Le panier moyen ne peut pas être calculé."
        ),
        (
            f"Sur {livraisons} livraisons évaluables, "
            f"{retards} sont en retard, soit {taux_retard} %."
            if livraisons > 0 and taux_retard is not None
            else "Le taux de retard ne peut pas être calculé."
        ),
    ]

    return "\n".join(facts)
