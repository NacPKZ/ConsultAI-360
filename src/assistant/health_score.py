def health(d: dict) -> dict:
    """Score pédagogique : 60 % complétude, 40 % ponctualité."""
    comp = max(0.0, 100 - 5 * d["missing_pct"])
    punct = max(0.0, 100 - 2 * d["late_pct"])

    return {
        "score": round(0.6 * comp + 0.4 * punct, 1),
        "comp": comp,
        "punct": punct,
        "lost_missing": 0.6 * (100 - comp),
        "lost_late": 0.4 * (100 - punct),
    }
