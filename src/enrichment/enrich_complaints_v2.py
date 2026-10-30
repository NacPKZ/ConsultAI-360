"""ConsultAI 360 - enrichissement V2 des réclamations NexaRetail.

Avis réels réaffectés à des commandes SYNTHÉTIQUES : ils ne constituent pas
les réclamations authentiques de clients NexaRetail.
Ne pas publier les textes sans vérification des droits de redistribution.
"""

import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from datasets import load_dataset

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
BACKUP = ROOT / "data" / "backup"
REPORT = ROOT / "reports" / "enrichment"
SOURCE = "SetFit/amazon_reviews_multi_fr"
SEED = 20261030
MAX_REVIEWS = None  # parcourir toute la partition train
MIN_LENGTH, MAX_LENGTH = 45, 1500
MAX_RATE = 0.80  # garde-fou, pas un objectif
RNG = np.random.default_rng(SEED)


def norm(s):
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(c for c in s if not unicodedata.combining(c)).lower().strip()


def rx(pattern):
    return re.compile(pattern)


REASONS = {
    "late_delivery": [
        r"\b(?:livraison|livre\w*|colis|commande|recu\w*|arrive\w*).{0,55}\bretard\b",
        r"\bretard\b.{0,55}\b(?:livraison|colis|livre\w*|commande)\b",
        r"\bdelai\w* de livraison.{0,35}(?:depass\w*|non respecte\w*)",
    ],
    "damaged_product": [
        r"\b(?:recu\w*|arrive\w*|livre\w*|colis|article|produit).{0,40}(?:cass\w*|abim\w*|endommag\w*|fissur\w*)",
        r"\b(?:cass\w*|abim\w*|endommag\w*).{0,30}(?:a la reception|a l.arrivee|pendant le transport)",
    ],
    "wrong_product": [
        r"\bmauvais (?:article|produit) recu\b",
        r"\bpas le bon (?:article|produit)\b",
        r"\bpas (?:le|la) (?:produit|article|reference) command\w*",
        r"\b(?:article|produit) different de celui command\w*",
        r"\berreur de preparation.{0,25}commande",
        r"\bau lieu de (?:recevoir|la|le).{0,45}(?:recu|recois|recu\w*)",
    ],
    "refund_issue": [
        r"\b(?:pas|jamais|toujours pas|aucun|sans).{0,40}rembours\w*",
        r"\bremboursement.{0,45}(?:attend\w*|refus\w*|impossible|incomplet|inferieur|partiel|toujours pas)",
        r"\b(?:refus\w*|impossible|attend\w*).{0,40}remboursement",
        r"\b(?:ne|n.).{0,15}rembours\w*",
    ],
    "customer_service": [
        r"\b(?:aucune|pas de|jamais de|sans) reponse (?:du|de la|de mon|a mes|a mon).{0,30}(?:vendeur|service|sav|message|mail)",
        r"\b(?:service client|sav|service apres.vente).{0,55}(?:injoignable|inefficace|deplorable|inexistant|aucune reponse)",
        r"\b(?:vendeur|service client|sav).{0,40}(?:ne repond|ne repondent|injoignable)",
    ],
    "product_quality": [
        r"\b(?:mauvaise qualite|qualite mediocre|tres mauvaise qualite|produit defectueux)\b",
        r"\b(?:ne fonctionne plus|tombe en panne|ne marche plus)\b",
        r"\bcass\w* apres.{0,35}utilisation",
    ],
}
COMPILED = {k: [rx(p) for p in v] for k, v in REASONS.items()}

# Lexique volontairement conservateur. Les termes trop ambigus (table,
# sac, verre, produit, charge, etc.) ne sont pas utilisés isolément.
FAMILIES = {
    "Électronique": [
        "smartphone",
        "telephone",
        "macbook",
        "iphone",
        "ordinateur",
        "pc portable",
        "chargeur",
        "ecouteurs",
        "casque audio",
        "enceinte",
        "imprimante",
        "cartouche d.encre",
        "clavier",
        "souris informatique",
        "tablette tactile",
        "coque de telephone",
        "ecran",
        "disque dur",
        "cle usb",
        "adaptateur usb",
        "batterie externe",
        "cable usb",
        "camera",
    ],
    "Maison": [
        "canape",
        "chaise",
        "fauteuil",
        "armoire",
        "commode",
        "poubelle",
        "casserole",
        "poele a frire",
        "vaisselle",
        "rideau",
        "aspirateur",
        "lampe",
        "table a langer",
        "ventilateur",
        "meuble",
        "cuvette",
        "oreiller",
        "matelas",
        "ustensile",
        "tabouret",
    ],
    "Mode": [
        "chaussure",
        "basket de sport",
        "pantalon",
        "robe",
        "t-shirt",
        "veste",
        "manteau",
        "sac a main",
        "pull",
        "chemise",
        "bracelet",
        "montre",
        "ceinture",
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
        "vernis a ongles",
        "masque visage",
        "fond de teint",
        "biberon",
    ],
    "Sport": [
        "tapis de yoga",
        "haltere",
        "tapis de course",
        "velo elliptique",
        "raquette",
        "ballon de football",
        "sac de sport",
        "gant de boxe",
        "velo d.appartement",
        "trottinette",
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
        "figurine",
        "livre de coloriage",
        "jeu de cartes",
    ],
}
FAMILY_RX = {
    fam: [rx(r"(?<!\w)" + p.replace(" ", r"\s+") + r"(?!\w)") for p in terms]
    for fam, terms in FAMILIES.items()
}

# Un filtre conservateur : ne prétend pas couvrir toutes les marques.
EXTERNAL = rx(
    r"\b(?:amazon|amazon prime|prime video|aliexpress|cdiscount|fnac|temu|"
    r"xiaomi|wiko|mi home|samsung|apple|iphone|macbook|somfy|auchan|"
    r"ikea|ebay|wish|shein|darty|boulanger|carrefour|decathlon|"
    r"google|playstation|nintendo|huawei|sony|philips|saab)\b"
)
EMAIL = rx(r"\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b")
PHONE = rx(r"(?<!\d)(?:\+33|0)[1-9](?:[\s.\-]?\d{2}){4}(?!\d)")

# Un défaut physique / fonctionnel sans objet reconnu ne doit pas être
# rattaché arbitrairement à un produit. Ce filtre est heuristique.
OBJECT_SPECIFIC = rx(
    r"\b(?:casse\w*|fissur\w*|ray\w*|abim\w*|endommag\w*|defectu\w*|"
    r"ne fonctionne|ne marche|en panne|mauvaise qualite|qualite mediocre|"
    r"vis|bouton|moteur|plastique|taille|couleur|batterie|chargeur|"
    r"assemblage|montage|piece|notice|filtre|cartouche|ecran|"
    r"produit non conforme|article non conforme)\b"
)
REFUND_SUCCESS = rx(
    r"\b(?:remboursement|rembourse\w*).{0,35}"
    r"(?:rapide|sans probleme|sans difficulte|immediat|obtenu|effectue|accepte)"
)
REFUND_NEGATIVE = rx(
    r"\b(?:pas|jamais|toujours pas|aucun|sans|refus\w*|incomplet|"
    r"inferieur|partiel|impossible|attend\w*).{0,45}rembours\w*|"
    r"\bremboursement.{0,45}(?:refus\w*|incomplet|inferieur|"
    r"partiel|impossible|attend\w*|toujours pas)"
)


def classify_reason(t):
    hits = [k for k, pats in COMPILED.items() if any(p.search(t) for p in pats)]
    if len(hits) != 1:
        return None
    if hits[0] == "refund_issue" and (
        not REFUND_NEGATIVE.search(t)
        or (REFUND_SUCCESS.search(t) and not REFUND_NEGATIVE.search(t))
    ):
        return None
    return hits[0]


def identify_family(t):
    hits = {fam for fam, pats in FAMILY_RX.items() if any(p.search(t) for p in pats)}
    if len(hits) > 1:
        return "ambiguous"
    return next(iter(hits)) if hits else None


def load_base():
    source = BACKUP / "complaints_before_enrichment.csv"
    v1 = BACKUP / "complaints_enriched_v1.csv"
    if not source.is_file() or not v1.is_file():
        raise FileNotFoundError("Sauvegardes originale et V1 requises dans data/backup")
    base = pd.read_csv(source, dtype={"order_id": str, "complaint_id": str})
    if "complaint_text" in base.columns:
        raise ValueError("La sauvegarde originale contient déjà complaint_text")
    if base["complaint_id"].duplicated().any():
        raise ValueError("Doublons complaint_id dans la sauvegarde originale")
    items = pd.read_csv(
        RAW / "order_items.csv",
        usecols=["order_id", "product_id"],
        dtype={"order_id": str, "product_id": str},
    )
    products = pd.read_csv(
        RAW / "products.csv",
        usecols=["product_id", "category"],
        dtype={"product_id": str},
    )
    joined = items.merge(products, on="product_id", how="left", validate="many_to_one")
    if joined["category"].isna().any():
        raise ValueError("Catégories produit manquantes")
    categories = (
        joined.groupby("order_id")["category"].agg(lambda s: frozenset(s)).to_dict()
    )
    if not set(base["order_id"]).issubset(categories):
        raise ValueError("Certaines réclamations n’ont pas de commande avec articles")
    return base, categories


def collect():
    pools = defaultdict(list)
    excluded = Counter()
    seen = set()
    scanned = 0
    dataset = load_dataset(SOURCE, split="train", streaming=True)
    for row in dataset:
        if MAX_REVIEWS is not None and scanned >= MAX_REVIEWS:
            break
        scanned += 1
        text = str(row.get("text") or "").strip()
        if not MIN_LENGTH <= len(text) <= MAX_LENGTH:
            excluded["length"] += 1
            continue
        try:
            rating = int(row["label"]) + 1
        except (TypeError, ValueError, KeyError):
            excluded["invalid_rating"] += 1
            continue
        if rating not in (1, 2):
            excluded["rating"] += 1
            continue
        t = norm(text)
        if t in seen:
            excluded["duplicate"] += 1
            continue
        seen.add(t)
        if EXTERNAL.search(t):
            excluded["external_brand"] += 1
            continue
        if EMAIL.search(t) or PHONE.search(t):
            excluded["potential_pii"] += 1
            continue
        reason = classify_reason(t)
        if reason is None:
            excluded["ambiguous_or_no_reason"] += 1
            continue
        family = identify_family(t)
        if family == "ambiguous":
            excluded["ambiguous_family"] += 1
            continue
        if family is None and (
            reason in {"damaged_product", "product_quality"}
            or OBJECT_SPECIFIC.search(t)
        ):
            excluded["object_specific_without_family"] += 1
            continue
        # Les avis génériques de livraison, SAV et remboursement uniquement.
        if family is None and reason not in {
            "late_delivery",
            "refund_issue",
            "customer_service",
            "wrong_product",
        }:
            excluded["generic_disallowed"] += 1
            continue
        pools[(reason, family)].append({"text": text, "rating": rating})
        if scanned % 25000 == 0:
            print(f"Avis examinés : {scanned:,}", flush=True)
    print(f"Avis examinés : {scanned:,}")
    print(f"Avis retenus : {sum(map(len, pools.values())):,}")
    print("Exclusions :", dict(excluded))
    return pools, scanned, excluded


def enrich(base, categories, pools):
    out = base.copy()
    for c in [
        "complaint_text",
        "review_rating",
        "text_language",
        "text_source",
        "text_match_method",
        "text_match_confidence",
    ]:
        out[c] = pd.NA
    out["has_text"] = False
    available = {}
    for key, values in pools.items():
        available[key] = RNG.permutation(len(values)).tolist()
    total = 0
    max_count = int(len(out) * MAX_RATE)
    for i in RNG.permutation(len(out)):
        if total >= max_count:
            break
        i = int(i)
        reason = str(out.at[i, "complaint_reason"])
        cats = categories[str(out.at[i, "order_id"])]
        keys = [(reason, c) for c in sorted(cats) if available.get((reason, c))]
        if reason in {
            "late_delivery",
            "refund_issue",
            "customer_service",
            "wrong_product",
        }:
            if available.get((reason, None)):
                keys.append((reason, None))
        if not keys:
            continue
        # Préférence pour la correspondance explicite avec une famille.
        key = keys[int(RNG.integers(0, len(keys)))] if len(keys) > 1 else keys[0]
        review = pools[key][available[key].pop()]
        out.at[i, "complaint_text"] = review["text"]
        out.at[i, "review_rating"] = review["rating"]
        out.at[i, "text_language"] = "fr"
        out.at[i, "text_source"] = SOURCE
        out.at[i, "text_match_method"] = (
            "reason_and_category_v2" if key[1] else "generic_service_delivery_refund_v2"
        )
        out.at[i, "text_match_confidence"] = "medium" if key[1] else "low"
        out.at[i, "has_text"] = True
        total += 1
    return out


def validate(base, out, categories):
    if len(base) != len(out):
        raise ValueError("Nombre de lignes modifié")
    for c in base.columns:
        if not base[c].equals(out[c]):
            raise ValueError(f"Colonne d’origine modifiée : {c}")
    mask = out["has_text"]
    if not mask.equals(out["complaint_text"].notna()):
        raise ValueError("Incohérence has_text")
    if out.loc[mask, "complaint_text"].duplicated().any():
        raise ValueError("Textes réutilisés")
    for r in out.loc[mask].itertuples(index=False):
        t = norm(r.complaint_text)
        if classify_reason(t) != r.complaint_reason or EXTERNAL.search(t):
            raise ValueError(f"Texte ou motif invalide : {r.complaint_id}")
        fam = identify_family(t)
        if fam == "ambiguous" or (fam and fam not in categories[str(r.order_id)]):
            raise ValueError(f"Famille incompatible : {r.complaint_id}")
        if fam is None and (
            r.complaint_reason in {"damaged_product", "product_quality"}
            or OBJECT_SPECIFIC.search(t)
        ):
            raise ValueError(f"Texte objet spécifique sans famille : {r.complaint_id}")
    print(f"Validation V2 OK : {int(mask.sum()):,} textes uniques")


def save(base, out, scanned, excluded):
    REPORT.mkdir(parents=True, exist_ok=True)
    dest = RAW / "complaints.csv"
    tmp = RAW / "complaints_v2.tmp.csv"
    if not dest.is_file():
        raise FileNotFoundError("complaints.csv courant introuvable")
    old = pd.read_csv(dest, usecols=["complaint_id"], dtype={"complaint_id": str})
    if len(old) != len(base) or set(old["complaint_id"]) != set(base["complaint_id"]):
        raise ValueError(
            "Le CSV courant diffère des identifiants de la sauvegarde originale"
        )
    out.to_csv(tmp, index=False, encoding="utf-8")
    # Test du fichier temporaire avant remplacement.
    test = pd.read_csv(tmp, usecols=["complaint_id", "has_text"])
    if len(test) != len(base) or int(test["has_text"].sum()) != int(
        out["has_text"].sum()
    ):
        raise ValueError("Fichier temporaire invalide : aucune substitution")
    tmp.replace(dest)
    n = int(out["has_text"].sum())
    by_reason = {}
    for reason, group in out.groupby("complaint_reason"):
        by_reason[str(reason)] = {
            "total": len(group),
            "enriched": int(group["has_text"].sum()),
        }
    report = {
        "version": "v2",
        "dataset": SOURCE,
        "seed": SEED,
        "reviews_scanned": scanned,
        "total_complaints": len(out),
        "enriched_complaints": n,
        "unenriched_complaints": len(out) - n,
        "enrichment_rate_pct": round(100 * n / len(out), 2),
        "exclusions": dict(excluded),
        "by_reason": by_reason,
        "limitations": [
            "Avis authentiques du corpus Amazon, mais associés à des commandes NexaRetail fictives.",
            "Correspondance lexicale et catégorie heuristiques : contrôle humain nécessaire.",
            "Confidence est qualitative, non calibrée.",
            "Absence de texte structurelle ; ne pas assimiler à une anomalie injectée.",
            "Droits de redistribution du corpus à vérifier avant toute publication.",
        ],
    }
    (REPORT / "complaints_enrichment_report_v2.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("\nRÉSULTATS V2")
    print(f"Enrichies : {n:,}/{len(out):,} ({100 * n / len(out):.2f} %)")
    for k, v in by_reason.items():
        print(f"{k}: {v['enriched']}/{v['total']}")
    print("CSV :", dest)
    print("Rapport :", REPORT / "complaints_enrichment_report_v2.json")


def main():
    print("CONSULTAI 360 - ENRICHISSEMENT V2")
    base, categories = load_base()
    pools, scanned, excluded = collect()
    out = enrich(base, categories, pools)
    validate(base, out, categories)
    save(base, out, scanned, excluded)
    print("ENRICHISSEMENT V2 TERMINÉ")


if __name__ == "__main__":
    main()
