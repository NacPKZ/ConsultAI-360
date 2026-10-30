"""ConsultAI 360 — V2.1 conservative post-filter of the backed-up V2.

Does not download reviews. Rejects suspect assignments; never invents texts.
Run from project root: python src/enrichment/refine_complaints_v21.py
"""

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BACKUP = ROOT / "data" / "backup"
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "reports" / "enrichment"


def norm(x):
    x = unicodedata.normalize("NFKD", str(x))
    return "".join(c for c in x if not unicodedata.combining(c)).lower()


def pattern(words):
    return re.compile(r"(?<!\w)(?:" + "|".join(words) + r")(?!\w)")


# Terms describe *ordered product*, not incidental words such as "livraison".
# Each explicit object is mapped to acceptable catalogue subcategories.
OBJECTS = {
    "Livres": [
        r"livre\w*",
        r"roman\w*",
        r"ouvrage\w*",
        r"bd",
        r"bande\s+dessinee",
        r"pages?",
        r"couverture\s+du\s+livre",
    ],
    "Jeux": [
        r"jouet\w*",
        r"playmobil",
        r"puzzle\w*",
        r"jeu\s+de\s+societe",
        r"des\s+de\s+couleur",
        r"figurine\w*",
    ],
    "Audio": [
        r"enceinte\w*",
        r"ecouteur\w*",
        r"casque\s+audio",
        r"haut[ -]?parleur\w*",
    ],
    "Téléphonie": [
        r"telephone\w*",
        r"smartphone\w*",
        r"iphone\w*",
        r"coque\w*\s+(?:de\s+)?telephone",
    ],
    "Informatique": [
        r"ordinateur\w*",
        r"pc\s+portable",
        r"clavier\w*",
        r"imprimante\w*",
        r"cartouche\w*\s+d.imprimante",
    ],
    "Mobilier": [
        r"meuble\w*",
        r"chaise\w*",
        r"fauteuil\w*",
        r"canape\w*",
        r"table\s+a\s+langer",
        r"armoire\w*",
        r"commode\w*",
        r"tonnelle\w*",
    ],
    "Cuisine": [
        r"casserole\w*",
        r"bouilloire\w*",
        r"poele\s+a\s+frire",
        r"ustensile\w*",
    ],
    "Rangement": [r"poubelle\w*", r"boite\s+de\s+rangement"],
    "Vêtements": [
        r"robe\w*",
        r"pantalon\w*",
        r"vetement\w*",
        r"chemise\w*",
        r"manteau\w*",
        r"pull\w*",
        r"couette\w*",
    ],
    "Chaussures": [r"chaussure\w*", r"basket\w*\s+(?:de\s+)?sport"],
    "Sacs": [r"sac\s+a\s+main", r"sacoche\w*"],
    "Parfums": [r"parfum\w*", r"eau\s+de\s+toilette"],
    "Maquillage": [r"mascara\w*", r"vernis\s+a\s+ongles", r"rouge\s+a\s+levres"],
    "Fitness": [
        r"velo\s+d.appartement",
        r"velo\s+elliptique",
        r"tapis\s+de\s+course",
        r"haltere\w*",
    ],
    "Équipement": [r"trottinette\w*", r"raquette\w*"],
}
OBJ_RX = {k: pattern(v) for k, v in OBJECTS.items()}
EXTERNAL = pattern(
    [
        r"amazon\w*",
        r"prime",
        r"chronopost",
        r"chrono\s*post",
        r"tnt",
        r"gls",
        r"playmobil",
        r"coolpix",
        r"asus",
        r"bestek",
        r"iphone",
        r"ipad",
        r"fnac",
        r"cdiscount",
        r"aliexpress",
        r"xiaomi",
        r"samsung",
        r"apple",
        r"ikea",
        r"colissimo",
        r"dhl",
        r"ups",
        r"mondial\s+relay",
    ]
)
REFUND_SUCCESS = re.compile(
    r"\b(?:remboursement\s+(?:a\s+ete|est|fut)\s+(?:effectue|realise|verse|obtenu)|"
    r"(?:j.ai|je\s+suis|nous\s+avons)\s+(?:ete\s+)?rembourse\w*|"
    r"rembourse\w*\s+(?:sans\s+probleme|rapidement))\b"
)
REFUND_PENDING = re.compile(
    r"\b(?:toujours\s+pas|jamais|aucun|pas\s+encore|refus\w*|impossible|"
    r"non\s+rembourse\w*|sans\s+remboursement|attend\w*\s+le\s+remboursement)\b"
)
# Potentially explicit objects missed by the taxonomy: reject instead of calling generic.
UNKNOWN_OBJECT = pattern(
    [
        r"bouillotte\w*",
        r"collier\w*",
        r"porte[ -]?serviette\w*",
        r"miroir\w*",
        r"chaine",
        r"plateau\w*",
        r"plafonnier\w*",
        r"vitre\w*",
        r"verres?",
        r"capteur\w*",
        r"pedalier\w*",
        r"guidon\w*",
        r"ceinture\w*",
        r"rideau\w*",
        r"matelas\w*",
        r"housse\w*",
        r"lampe\w*",
        r"bijou\w*",
        r"insecticide\w*",
        r"reveil\w*",
        r"manette\w*",
    ]
)


def main():
    source = BACKUP / "complaints_enriched_v2.csv"
    original = BACKUP / "complaints_before_enrichment.csv"
    current = RAW / "complaints.csv"
    for f in (source, original, current):
        if not f.is_file():
            raise FileNotFoundError(f"Missing required file: {f}")
    v2 = pd.read_csv(source, dtype={"complaint_id": str, "order_id": str})
    base = pd.read_csv(original, dtype={"complaint_id": str, "order_id": str})
    if len(v2) != len(base) or not v2["complaint_id"].equals(base["complaint_id"]):
        raise ValueError("V2 and original complaint IDs do not align")
    for col in base.columns:
        if not v2[col].equals(base[col]):
            raise ValueError(f"Original field changed: {col}")
    now = pd.read_csv(current, usecols=["complaint_id"], dtype=str)
    if not now["complaint_id"].equals(v2["complaint_id"]):
        raise ValueError("Current CSV IDs do not match backed-up V2")
    if "has_text" not in v2 or not v2["has_text"].astype(bool).equals(
        v2["complaint_text"].notna()
    ):
        raise ValueError("Invalid V2 has_text column")
    items = pd.read_csv(
        RAW / "order_items.csv", usecols=["order_id", "product_id"], dtype=str
    )
    products = pd.read_csv(
        RAW / "products.csv",
        usecols=["product_id", "category", "subcategory"],
        dtype=str,
    )
    join = items.merge(products, on="product_id", how="left", validate="many_to_one")
    if join["subcategory"].isna().any():
        raise ValueError("Missing product subcategory")
    order_subcats = (
        join.groupby("order_id")["subcategory"].agg(lambda s: set(s)).to_dict()
    )
    out = v2.copy()
    reasons = Counter()
    exclusions = []
    text_fields = [
        "complaint_text",
        "review_rating",
        "text_language",
        "text_source",
        "text_match_method",
        "text_match_confidence",
    ]
    for idx in out.index[out["complaint_text"].notna()]:
        row = out.loc[idx]
        t = norm(row["complaint_text"])
        subs = order_subcats.get(row["order_id"], set())
        matched = {name for name, regex in OBJ_RX.items() if regex.search(t)}
        issue = None
        if EXTERNAL.search(t):
            issue = "external_reference"
        elif (
            row["complaint_reason"] == "refund_issue"
            and REFUND_SUCCESS.search(t)
            and not REFUND_PENDING.search(t)
        ):
            issue = "refund_already_completed"
        elif matched and not matched.issubset(subs):
            issue = "product_subcategory_mismatch"
        elif not matched and UNKNOWN_OBJECT.search(t):
            issue = "unmapped_specific_object"
        # A review may mention another item incidentally; this conservative
        # filter intentionally prioritizes precision over coverage.
        if issue:
            reasons[issue] += 1
            exclusions.append(
                {
                    "complaint_id": row["complaint_id"],
                    "complaint_reason": row["complaint_reason"],
                    "exclusion_reason": issue,
                    "matched_subcategories": "|".join(sorted(matched)),
                    "order_subcategories": "|".join(sorted(subs)),
                }
            )
            out.loc[idx, text_fields] = pd.NA
            out.at[idx, "has_text"] = False
    if not out["has_text"].astype(bool).equals(out["complaint_text"].notna()):
        raise ValueError("Inconsistent has_text after filtering")
    if out.loc[out["has_text"], "complaint_text"].duplicated().any():
        raise ValueError("Duplicated texts")
    for col in base.columns:
        if not out[col].equals(base[col]):
            raise ValueError(f"Original field modified: {col}")
    REPORTS.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        exclusions,
        columns=[
            "complaint_id",
            "complaint_reason",
            "exclusion_reason",
            "matched_subcategories",
            "order_subcategories",
        ],
    ).to_csv(
        REPORTS / "complaints_v21_exclusions.csv", index=False, encoding="utf-8-sig"
    )
    n0 = int(v2["has_text"].sum())
    n1 = int(out["has_text"].sum())
    report = {
        "version": "v2.1",
        "source": "complaints_enriched_v2.csv",
        "initial_enriched": n0,
        "removed": n0 - n1,
        "final_enriched": n1,
        "final_coverage_pct": round(100 * n1 / len(out), 2),
        "removed_by_rule": dict(reasons),
        "by_reason": {
            str(k): int(g["has_text"].sum()) for k, g in out.groupby("complaint_reason")
        },
        "limitations": [
            "Conservative heuristic filtering; not a semantic guarantee.",
            "Subcategory labels may not exactly represent the item.",
            "Some external brands or objects may remain undetected.",
            "Text absence is structural, not injected missingness.",
            "Real Amazon reviews reassigned to synthetic orders; redistribution rights to check.",
        ],
    }
    (REPORTS / "complaints_enrichment_report_v21.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temp = RAW / "complaints_v21.tmp.csv"
    out.to_csv(temp, index=False, encoding="utf-8")
    check = pd.read_csv(temp, usecols=["complaint_id", "has_text"])
    if len(check) != len(out) or int(check["has_text"].sum()) != n1:
        raise ValueError("Temporary CSV verification failed")
    temp.replace(current)
    print("CONSULTAI 360 — V2.1 TERMINEE")
    print(
        f"V2: {n0:,} | Retires: {n0 - n1:,} | V2.1: {n1:,}/{len(out):,} ({100 * n1 / len(out):.2f}%)"
    )
    print("Exclusions:", dict(reasons))
    print("Par motif:", report["by_reason"])
    print("Rapport:", REPORTS / "complaints_enrichment_report_v21.json")


if __name__ == "__main__":
    main()
