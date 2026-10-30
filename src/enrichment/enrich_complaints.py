import json
import re
import shutil
import unicodedata
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from datasets import load_dataset

# ============================================================
# 1. CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
BACKUP = ROOT / "data" / "backup"
REPORTS = ROOT / "reports" / "enrichment"

DATASET_NAME = "SetFit/amazon_reviews_multi_fr"

SEED = 20261030
MAX_REVIEWS = 150000
MIN_TEXT_LENGTH = 45
MAX_TEXT_LENGTH = 1500

# Ne pas forcer l'enrichissement de toutes les reclamations.
MAX_ENRICHMENT_RATE = 0.80

rng = np.random.default_rng(SEED)


# ============================================================
# 2. REGLES DE CLASSIFICATION
# ============================================================

# Expressions volontairement restrictives.
# Une correspondance n'est pas une preuve parfaite.

REASON_PATTERNS = {
    "late_delivery": [
        r"\blivraison.{0,35}retard\b",
        r"\blivr[ée].{0,25}retard\b",
        r"\bcolis.{0,30}retard\b",
        r"\brecu.{0,30}retard\b",
        r"\bdelai de livraison.{0,25}depass",
    ],
    "damaged_product": [
        r"\barriv[ée].{0,25}cass",
        r"\brecu.{0,25}cass",
        r"\barriv[ée].{0,25}abim",
        r"\brecu.{0,25}endommag",
        r"\bcolis.{0,25}abim",
        r"\bproduit.{0,25}endommag",
    ],
    "wrong_product": [
        r"\bmauvais article recu\b",
        r"\bmauvais produit recu\b",
        r"\bpas le bon article\b",
        r"\bpas le produit command",
        r"\barticle different de celui command",
        r"\berreur de preparation.{0,20}commande",
    ],
    "refund_issue": [
        r"\bpas.{0,25}rembours",
        r"\baucun remboursement\b",
        r"\bremboursement.{0,35}attend",
        r"\bremboursement.{0,35}refus",
        r"\bremboursement.{0,35}impossible",
        r"\bremboursement.{0,35}probleme",
    ],
    "customer_service": [
        r"\bservice client.{0,50}(injoignable|inefficace|deplorable)",
        r"\bsav.{0,35}(injoignable|inefficace|deplorable)",
        r"\baucune reponse du (vendeur|service client|sav)",
        r"\bservice apres.vente.{0,40}(injoignable|inefficace)",
    ],
    "product_quality": [
        r"\bmauvaise qualite\b",
        r"\bqualite mediocre\b",
        r"\bne fonctionne plus\b",
        r"\bproduit defectueux\b",
        r"\btombe en panne\b",
        r"\bcasse apres.{0,25}utilisation",
    ],
}

# Termes indiquant explicitement une famille de produits.
# On ne rejette pas un texte simplement parce qu'il ne
# mentionne aucun produit precis.

PRODUCT_FAMILIES = {
    "Électronique": [
        "telephone",
        "smartphone",
        "ordinateur",
        "pc portable",
        "ecouteur",
        "casque audio",
        "enceinte bluetooth",
        "batterie",
        "chargeur",
        "ecran",
        "clavier",
        "souris",
        "tablette",
        "imprimante",
    ],
    "Beauté": [
        "parfum",
        "shampoing",
        "creme visage",
        "maquillage",
        "rouge a levres",
        "mascara",
        "gel douche",
        "deodorant",
        "serum visage",
    ],
    "Maison": [
        "canape",
        "chaise",
        "table basse",
        "meuble",
        "armoire",
        "casserole",
        "poele",
        "vaisselle",
        "rideau",
        "aspirateur",
        "lampe",
    ],
    "Mode": [
        "chaussure",
        "basket",
        "pantalon",
        "robe",
        "t-shirt",
        "veste",
        "manteau",
        "sac a main",
        "pull",
        "chemise",
    ],
    "Sport": [
        "tapis de yoga",
        "halter",
        "tapis de course",
        "velo elliptique",
        "equipement sportif",
        "ballon de football",
        "raquette",
        "sac de sport",
    ],
    "Loisirs": [
        "livre",
        "roman",
        "bande dessinee",
        "puzzle",
        "jeu de societe",
        "jeu video",
        "instrument de musique",
        "guitare",
        "jouet",
    ],
}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return text.lower().strip()


COMPILED_PATTERNS = {
    reason: [re.compile(pattern) for pattern in patterns]
    for reason, patterns in REASON_PATTERNS.items()
}


def classify_reason(text: str) -> str | None:
    normalized = normalize(text)

    matches = [
        reason
        for reason, patterns in COMPILED_PATTERNS.items()
        if any(pattern.search(normalized) for pattern in patterns)
    ]

    # Plusieurs motifs detectes : texte ambigu.
    if len(matches) != 1:
        return None

    return matches[0]


def identify_product_family(text: str) -> str | None:
    normalized = normalize(text)

    detected = set()

    for family, keywords in PRODUCT_FAMILIES.items():
        for keyword in keywords:
            pattern = r"(?<!\w)" + re.escape(normalize(keyword)) + r"(?!\w)"
            if re.search(pattern, normalized):
                detected.add(family)
                break

    # Plusieurs familles : ambiguite.
    if len(detected) != 1:
        return None

    return next(iter(detected))


# ============================================================
# 3. CHARGEMENT DES DONNEES NEXARETAIL
# ============================================================


def load_nexaretail():
    complaints = pd.read_csv(RAW / "complaints.csv")
    items = pd.read_csv(RAW / "order_items.csv")
    products = pd.read_csv(RAW / "products.csv")

    required_complaints = {"complaint_id", "order_id", "complaint_reason"}
    required_items = {"order_id", "product_id"}
    required_products = {"product_id", "category"}

    for name, df, required in [
        ("complaints", complaints, required_complaints),
        ("order_items", items, required_items),
        ("products", products, required_products),
    ]:
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"{name}: colonnes manquantes : {sorted(missing)}")

    if complaints["complaint_id"].duplicated().any():
        raise ValueError("Identifiants de reclamation dupliques")

    # Categories de tous les produits de chaque commande.
    joined = items[["order_id", "product_id"]].merge(
        products[["product_id", "category"]],
        on="product_id",
        how="left",
        validate="many_to_one",
    )

    if joined["category"].isna().any():
        raise ValueError("Certains articles n'ont pas de categorie produit")

    order_categories = (
        joined.groupby("order_id")["category"]
        .agg(lambda values: set(values.astype(str)))
        .to_dict()
    )

    return complaints, order_categories


# ============================================================
# 4. COLLECTE DES AVIS REELS
# ============================================================


def collect_reviews():
    print("\nCOLLECTE DES AVIS FRANCAIS")
    print("=" * 55)

    dataset = load_dataset(
        DATASET_NAME,
        split="train",
        streaming=True,
    )

    pools = defaultdict(list)
    seen_texts = set()

    scanned = 0
    retained = 0

    for review in dataset:
        if scanned >= MAX_REVIEWS:
            break

        scanned += 1

        text = str(review.get("text") or "").strip()

        if not MIN_TEXT_LENGTH <= len(text) <= MAX_TEXT_LENGTH:
            continue

        # Ce dataset utilise des labels de 0 a 4.
        # Nous retenons les notes 1 et 2 etoiles.
        label = int(review["label"])
        rating = label + 1

        if rating not in (1, 2):
            continue

        reason = classify_reason(text)

        if reason is None:
            continue

        normalized = normalize(text)

        if normalized in seen_texts:
            continue

        seen_texts.add(normalized)

        family = identify_product_family(text)

        pools[reason].append(
            {
                "text": text,
                "rating": rating,
                "family": family,
            }
        )

        retained += 1

        if scanned % 25000 == 0:
            print(f"Avis examines : {scanned:,}")

    print(f"\nAvis examines : {scanned:,}")
    print(f"Avis retenus : {retained:,}")

    for reason in REASON_PATTERNS:
        print(f"{reason}: {len(pools[reason]):,}")

    return pools, scanned


# ============================================================
# 5. ENRICHISSEMENT
# ============================================================


def enrich_complaints(complaints, order_categories, pools):
    enriched = complaints.copy()

    new_columns = {
        "complaint_text": pd.NA,
        "review_rating": pd.NA,
        "text_language": pd.NA,
        "text_source": pd.NA,
        "text_match_method": pd.NA,
        "text_match_confidence": pd.NA,
    }

    for column, value in new_columns.items():
        if column in enriched.columns:
            raise ValueError(
                f"Colonne deja presente : {column}. Arret pour eviter un ecrasement."
            )
        enriched[column] = value

    # Chaque avis ne sera utilise qu'une seule fois.
    available = {}

    for reason, reviews in pools.items():
        indices = rng.permutation(len(reviews)).tolist()
        available[reason] = indices

    enriched_count = 0
    target = int(len(enriched) * MAX_ENRICHMENT_RATE)

    row_indices = rng.permutation(len(enriched))

    for row_index in row_indices:
        if enriched_count >= target:
            break

        reason = str(enriched.at[int(row_index), "complaint_reason"])
        order_id = str(enriched.at[int(row_index), "order_id"])

        if reason not in pools:
            continue

        categories = order_categories.get(order_id, set())

        if not categories:
            continue

        candidates = available[reason]
        chosen_position = None

        # On examine au maximum 100 candidats disponibles.
        # Cela limite le temps de recherche.
        for position in range(max(0, len(candidates) - 100), len(candidates)):
            review_index = candidates[position]
            review = pools[reason][review_index]
            family = review["family"]

            if family is None or family in categories:
                chosen_position = position
                break

        if chosen_position is None:
            continue

        review_index = candidates.pop(chosen_position)
        review = pools[reason][review_index]

        method = (
            "reason_and_category"
            if review["family"] is not None
            else "reason_only_no_explicit_product"
        )

        idx = int(row_index)

        enriched.at[idx, "complaint_text"] = review["text"]
        enriched.at[idx, "review_rating"] = review["rating"]
        enriched.at[idx, "text_language"] = "fr"
        enriched.at[idx, "text_source"] = DATASET_NAME
        enriched.at[idx, "text_match_method"] = method

        # Etiquette qualitative, pas une probabilite calibree.
        enriched.at[idx, "text_match_confidence"] = (
            "medium" if review["family"] is not None else "low"
        )

        enriched_count += 1

    return enriched


# ============================================================
# 6. VALIDATION
# ============================================================


def validate(original, enriched, order_categories):
    if len(original) != len(enriched):
        raise ValueError("Le nombre de reclamations a change")

    for column in original.columns:
        if not original[column].equals(enriched[column]):
            raise ValueError(f"Colonne originale modifiee : {column}")

    with_text = enriched["complaint_text"].notna()

    texts = enriched.loc[with_text, "complaint_text"]

    if texts.duplicated().any():
        raise ValueError("Commentaires reels reutilises")

    invalid_reasons = 0
    invalid_families = 0

    for row in enriched.loc[with_text].to_dict("records"):
        text = str(row["complaint_text"])
        reason = str(row["complaint_reason"])
        order_id = str(row["order_id"])

        if classify_reason(text) != reason:
            invalid_reasons += 1

        family = identify_product_family(text)

        if family is not None and family not in order_categories.get(order_id, set()):
            invalid_families += 1

    print("\nCONTROLES D'ENRICHISSEMENT")
    print("=" * 55)
    print(f"Nombre de lignes modifie : {len(enriched) - len(original)}")
    print(f"Textes dupliques : {int(texts.duplicated().sum())}")
    print(f"Motifs incompatibles : {invalid_reasons}")
    print(f"Familles incompatibles : {invalid_families}")

    if invalid_reasons or invalid_families:
        raise ValueError("Incoherences detectees dans les textes")


# ============================================================
# 7. SAUVEGARDE ET RAPPORT
# ============================================================


def save_results(original, enriched, scanned):
    BACKUP.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    source_path = RAW / "complaints.csv"
    backup_path = BACKUP / "complaints_before_enrichment.csv"

    if not backup_path.exists():
        shutil.copy2(source_path, backup_path)
        print(f"\nSauvegarde creee : {backup_path}")

    # Ecriture temporaire, puis remplacement du CSV.
    temp_path = RAW / "complaints_enriched.tmp.csv"

    enriched.to_csv(
        temp_path,
        index=False,
        encoding="utf-8",
    )

    temp_path.replace(source_path)

    enriched_count = int(enriched["complaint_text"].notna().sum())

    report = {
        "dataset": DATASET_NAME,
        "language": "fr",
        "seed": SEED,
        "reviews_scanned": scanned,
        "total_complaints": len(enriched),
        "enriched_complaints": enriched_count,
        "unenriched_complaints": len(enriched) - enriched_count,
        "enrichment_rate_pct": round(enriched_count / len(enriched) * 100, 2),
        "matching_policy": (
            "Unique negative reviews, one unambiguous reason, "
            "compatible explicit product family when detected."
        ),
        "limitation": (
            "Review texts originate from a public corpus and are "
            "associated with synthetic NexaRetail complaints. "
            "They are not authentic NexaRetail complaints. "
            "Keyword matching is heuristic and may contain errors."
        ),
        "by_reason": {},
    }

    for reason, group in enriched.groupby("complaint_reason"):
        report["by_reason"][str(reason)] = {
            "total": len(group),
            "enriched": int(group["complaint_text"].notna().sum()),
        }

    report_path = REPORTS / "complaints_enrichment_report.json"

    report_path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\nRESULTATS")
    print("=" * 55)
    print(f"Reclamations totales : {len(enriched):,}")
    print(f"Reclamations enrichies : {enriched_count:,}")
    print(f"Taux d'enrichissement : {report['enrichment_rate_pct']:.2f} %")

    print("\nENRICHISSEMENT PAR MOTIF")

    for reason, stats in report["by_reason"].items():
        print(f"{reason}: {stats['enriched']:,}/{stats['total']:,}")

    print("\nFichiers :")
    print(source_path)
    print(backup_path)
    print(report_path)


# ============================================================
# 8. EXECUTION
# ============================================================


def main():
    print("CONSULTAI 360 - ENRICHISSEMENT DES RECLAMATIONS")
    print("=" * 55)

    complaints, order_categories = load_nexaretail()

    pools, scanned = collect_reviews()

    enriched = enrich_complaints(
        complaints,
        order_categories,
        pools,
    )

    validate(
        complaints,
        enriched,
        order_categories,
    )

    save_results(
        complaints,
        enriched,
        scanned,
    )

    print("\nENRICHISSEMENT TERMINE")


if __name__ == "__main__":
    main()
