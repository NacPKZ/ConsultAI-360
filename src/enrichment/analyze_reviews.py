from collections import Counter

from datasets import load_dataset

DATASET_NAME = "SetFit/amazon_reviews_multi_fr"

KEYWORDS = {
    "late_delivery": [
        "retard",
        "livraison tardive",
        "livré en retard",
        "colis arrivé en retard",
    ],
    "damaged_product": [
        "arrivé cassé",
        "arrivé abîmé",
        "endommagé",
        "colis abîmé",
    ],
    "wrong_product": [
        "mauvais produit",
        "mauvais article",
        "erreur de commande",
        "article différent",
    ],
    "refund_issue": [
        "remboursement",
        "remboursé",
        "pas remboursé",
        "attends mon remboursement",
    ],
    "customer_service": [
        "service client",
        "sav",
        "service après-vente",
        "vendeur ne répond",
    ],
    "product_quality": [
        "mauvaise qualité",
        "ne fonctionne plus",
        "défectueux",
        "qualité médiocre",
    ],
}


def main() -> None:

    dataset = load_dataset(
        DATASET_NAME,
        split="train",
        streaming=True,
    )

    counts: Counter[str] = Counter()
    examples: dict[str, list[str]] = {category: [] for category in KEYWORDS}

    total = 0

    for review in dataset:
        if total >= 10000:
            break

        total += 1

        text = str(review["text"]).strip()
        normalized = text.lower()

        if len(text) < 30:
            continue

        for category, keywords in KEYWORDS.items():
            if any(keyword in normalized for keyword in keywords):
                counts[category] += 1

                if len(examples[category]) < 2:
                    examples[category].append(text[:250])

    print("\nANALYSE DES AVIS CLIENTS")
    print("=" * 60)

    print(f"Avis examines : {total:,}")

    for category in KEYWORDS:
        count = counts[category]
        percentage = count / total * 100

        print(f"\n{category}")
        print(f"Correspondances : {count}")
        print(f"Pourcentage : {percentage:.2f} %")

        for example in examples[category]:
            print(f"Exemple : {example}")


if __name__ == "__main__":
    main()
