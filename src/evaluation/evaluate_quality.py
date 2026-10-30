"""ConsultAI 360 — evaluation des injections, detections et nettoyages.

Execution (depuis la racine du projet):
    .\\.venv\\Scripts\\python.exe src/evaluation/evaluate_quality.py --scenario all

Les journaux d'injection ne sont utilises ICI que pour l'evaluation,
jamais pour detecter ou nettoyer les donnees.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

SCENARIOS = ("low", "medium", "critical")
TYPES = (
    "missing_values",
    "negative_amounts",
    "invalid_status",
    "invalid_dates",
    "broken_references",
    "invalid_formats",
    "inconsistent_totals",
    "duplicates",
)
ISSUE_TO_TYPE = {
    "invalid_status": "invalid_status",
    "negative_amount": "negative_amounts",
    "invalid_date": "invalid_dates",
    "invalid_format": "invalid_formats",
    "inconsistent_or_missing_total": "inconsistent_totals",
    "unverifiable_total": "inconsistent_totals",
}


def read_csv(path: Path, columns: tuple[str, ...]) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Fichier manquant : {path}")
    df = pd.read_csv(path, dtype="string", low_memory=False)
    missing = set(columns) - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes dans {path}: {sorted(missing)}")
    return df


def normalize(df: pd.DataFrame, position: str, kind: str) -> pd.DataFrame:
    result = df.copy()
    result["table"] = result["table"].astype("string").str.strip()
    result["row_position"] = pd.to_numeric(result[position], errors="raise").astype(
        "int64"
    )
    result["anomaly_type"] = result[kind].astype("string").str.strip()
    result["column"] = result["column"].fillna("<ROW>").astype("string").str.strip()
    result.loc[result["anomaly_type"].eq("duplicates"), "column"] = "<ROW>"
    return result


def score(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def evaluate(scenario: str, output_root: Path) -> dict:
    injection = read_csv(
        Path(f"reports/data_quality/injections/{scenario}/injection_log.csv"),
        ("table", "row_position", "column", "anomaly_type"),
    )
    audit = read_csv(
        Path(f"reports/data_quality/audits/{scenario}/detected_anomalies.csv"),
        ("table", "row_position", "column", "anomaly_type"),
    )
    events = read_csv(
        Path(f"reports/data_quality/cleaning_v2/{scenario}/quality_events.csv"),
        ("table", "source_row_position", "column", "issue", "action"),
    )
    summary_path = Path(
        f"reports/data_quality/cleaning_v2/{scenario}/cleaning_summary.json"
    )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    truth = normalize(injection, "row_position", "anomaly_type")
    found = normalize(audit, "row_position", "anomaly_type")
    keys = ["table", "row_position", "column", "anomaly_type"]
    if truth.duplicated(keys).any():
        raise ValueError(
            "Journal d'injection : cles evenement non uniques. Evaluation ambiguë."
        )
    if found.duplicated(keys).any():
        raise ValueError("Audit : cles evenement non uniques. Evaluation ambiguë.")
    truth_keys = pd.MultiIndex.from_frame(truth[keys])
    found_keys = pd.MultiIndex.from_frame(found[keys])
    truth["detected"] = truth_keys.isin(found_keys)
    found["injected"] = found_keys.isin(truth_keys)

    per_type = {}
    for kind in TYPES:
        t = truth.loc[truth.anomaly_type.eq(kind)]
        d = found.loc[found.anomaly_type.eq(kind)]
        tp = int(t.detected.sum())
        per_type[kind] = {
            "injected_events": len(t),
            "detected_alerts": len(d),
            **score(tp, len(d) - tp, len(t) - tp),
        }
    tp_all = int(truth.detected.sum())
    detection = {
        "overall": score(tp_all, len(found) - tp_all, len(truth) - tp_all),
        "by_type": per_type,
    }

    # Matching des actions sur les positions ORIGINALES du scenario corrompu.
    # Ne jamais utiliser les positions du CSV nettoye (elles ont change apres deduplication).
    actions = events.copy()
    actions["row_position"] = pd.to_numeric(
        actions["source_row_position"], errors="raise"
    ).astype("int64")
    actions["column"] = actions["column"].fillna("<ROW>").astype("string").str.strip()
    actions["anomaly_type"] = actions["issue"].map(ISSUE_TO_TYPE).astype("string")
    broken = actions["issue"].fillna("").str.startswith("broken_reference_to_")
    actions.loc[broken, "anomaly_type"] = "broken_references"
    # Les doublons sont comptabilises par la quarantaine, sans log evenementiel dans quality_events.
    actions = actions.loc[actions.anomaly_type.notna()].copy()
    action_keys = ["table", "row_position", "column", "anomaly_type"]
    matched_actions = actions[action_keys + ["action"]].drop_duplicates()
    merged = truth.merge(matched_actions, on=action_keys, how="left")
    action_counts = (
        events["action"].fillna("unknown").value_counts().astype(int).to_dict()
    )
    injected_action_counts = (
        merged.loc[merged.action.notna(), "action"].value_counts().astype(int).to_dict()
    )

    before = sum(int(x) for x in summary["rows_before"].values())
    after = sum(int(x) for x in summary["rows_after"].values())
    quarantined = sum(int(x) for x in summary["quarantined_rows"].values())
    residual = {k: int(v) for k, v in summary["remaining_alerts_by_type"].items()}
    report = {
        "scenario": scenario,
        "evaluated_at_utc": datetime.now(UTC).isoformat(),
        "method": "Exact match (table, source row position, column, anomaly type) before cleaning",
        "detection": detection,
        "cleaning": {
            "rows_before": before,
            "rows_after": after,
            "quarantined_rows": quarantined,
            "retention_rate": after / before if before else None,
            "quarantine_rate": quarantined / before if before else None,
            "quality_event_actions": {str(k): int(v) for k, v in action_counts.items()},
            "injected_events_with_logged_action": int(merged.action.notna().sum()),
            "injected_events_actions": {
                str(k): int(v) for k, v in injected_action_counts.items()
            },
            "remaining_alerts": int(summary["remaining_audit_alerts"]),
            "remaining_alerts_by_type": residual,
            "alert_reduction_rate": 1
            - int(summary["remaining_audit_alerts"]) / len(found)
            if len(found)
            else None,
        },
        "limitations": [
            "Precision/rappel/F1 evaluent les injections connues, pas toutes les erreurs reelles preexistantes.",
            "Une alerte non associee a une injection est un FP relatif au journal, pas necessairement une fausse anomalie metier.",
            "Les actions 'nullified' neutralisent une valeur et ne restaurent pas la valeur originale.",
            "Les FK 'flagged_not_deleted' sont conservees et non reparees.",
            "Les doublons sont evalues par correspondance exacte dans l'audit; leur suppression est mesuree par quarantaine.",
            "Les alertes residuelles sont comparees en volumes seulement : les positions de lignes ont change apres deduplication.",
            "Le rapprochement des actions de nettoyage ne constitue pas une preuve de correction exacte.",
        ],
    }
    folder = output_root / scenario
    if folder.exists():
        raise FileExistsError(f"Rapport deja existant : {folder}")
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "evaluation_summary.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    pd.DataFrame(
        [{"anomaly_type": kind, **values} for kind, values in per_type.items()]
    ).to_csv(folder / "detection_by_type.csv", index=False, encoding="utf-8-sig")
    print(
        f"\n{scenario.upper()} | TP={tp_all:,} | FP={len(found) - tp_all:,} | FN={len(truth) - tp_all:,}"
    )
    print(
        f"Precision={detection['overall']['precision']:.2%} | Rappel={detection['overall']['recall']:.2%} | F1={detection['overall']['f1']:.2%}"
    )
    print(
        f"Lignes conservees={after:,}/{before:,} | Alertes restantes={report['cleaning']['remaining_alerts']:,}"
    )
    print(f"Rapports : {folder}")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=(*SCENARIOS, "all"), default="medium")
    args = parser.parse_args()
    selected = SCENARIOS if args.scenario == "all" else (args.scenario,)
    for scenario in selected:
        evaluate(scenario, Path("reports/data_quality/evaluation"))


if __name__ == "__main__":
    main()
