"""Règles métier de publication des KPI."""

DEFAULT_TH = {
    "m_warn": 3.0,
    "m_fail": 8.0,
    "l_warn": 10.0,
    "l_fail": 20.0,
}


def safe_th(th: dict) -> dict:
    """Revient aux seuils par défaut si leur ordre est incohérent."""
    ok = th["m_warn"] <= th["m_fail"] and th["l_warn"] <= th["l_fail"]
    return th if ok else dict(DEFAULT_TH)


def _fmt(v: float, digits: int = 0) -> str:
    """Format français identique à celui de Streamlit."""
    return f"{v:,.{digits}f}".replace(",", "\u202f").replace(".", ",")


def gate(d: dict, th: dict) -> dict:
    """Classe les indicateurs en go, warn ou stop."""
    m, l = d["missing_pct"], d["late_pct"]

    checks = [
        (
            "Montants renseignés",
            f"{_fmt(m, 2)} % absents",
            "go" if m <= th["m_warn"] else "warn" if m <= th["m_fail"] else "stop",
            f"Seuils : réserves au-delà de {_fmt(th['m_warn'], 1)} %, blocage au-delà de {_fmt(th['m_fail'], 1)} %",
        ),
        (
            "Ponctualité des livraisons",
            f"{_fmt(l, 2)} % en retard",
            "go" if l <= th["l_warn"] else "warn" if l <= th["l_fail"] else "stop",
            f"Seuils : réserves au-delà de {_fmt(th['l_warn'], 1)} %, blocage au-delà de {_fmt(th['l_fail'], 1)} %",
        ),
    ]

    order = {"go": 0, "warn": 1, "stop": 2}

    return {
        "checks": checks,
        "overall": max(
            (c[2] for c in checks),
            key=lambda s: order[s],
        ),
    }
