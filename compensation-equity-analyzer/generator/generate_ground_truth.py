"""
Ground Truth Dataset Generator
Produces separate ground_truth.csv and ground_truth.json files.
Contains explicitly labelled anomalies, expected system decisions, and review actions.
NEVER imported or consumed as a feature in runtime detection algorithms.
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any
from config import settings, DATA_DIR

def export_ground_truth(
    data_quality_issues: List[Dict[str, Any]],
    output_dir: Path = DATA_DIR
):
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "ground_truth.csv"
    json_path = output_dir / "ground_truth.json"

    ground_truth_records = []

    for issue in data_quality_issues:
        gt_label = issue.get("ground_truth_label", "UNKNOWN_ANOMALY")
        issue_type = issue.get("issue_type")
        entity_id = issue.get("entity_id")
        
        # Determine expected decisions based on business rules
        if issue_type == "EXPIRED_BAND":
            expected_decision = "EXCLUDE_FROM_COMPENSATION_DECISION"
            expected_action = "ASSIGN_ACTIVE_COMPENSATION_BAND"
            reason = "Band validity window expired prior to evaluation date; cannot use for benchmarking."
        elif issue_type == "FTE_IGNORED":
            expected_decision = "RECALCULATE_FTE_NORMALIZED"
            expected_action = "ADJUST_COMPARISON_TO_FTE_1_0"
            reason = "Raw nominal salary produces artificial compensation deficit for part-time schedule."
        elif issue_type == "MISSING_EXCHANGE_RATE":
            expected_decision = "HALT_COMPARISON_FLAG_EXCEPTION"
            expected_action = "CONFIGURE_FX_RATE_IN_TABLE"
            reason = "Foreign currency cannot be normalized to base currency without verified effective rate."
        elif issue_type == "UNAUTHORIZED_ADJUSTMENT":
            expected_decision = "TRIGGER_HIGH_PRIORITY_AUDIT"
            expected_action = "REVERT_OR_INITIATE_RETROACTIVE_APPROVAL"
            reason = "Salary increase applied without formal HR proposal approval and state transition."
        elif issue_type == "INCOMPARABLE_ROLE_GROUPING":
            expected_decision = "INVALIDATE_COMPARISON_GROUP"
            expected_action = "SEPARATE_INTO_DISCRETE_FAMILY_COHORTS"
            reason = "Disparate job families clustered without documented cross-functional rationale."
        else:
            expected_decision = "FLAG_FOR_REVIEW"
            expected_action = "INVESTIGATE"
            reason = issue.get("description", "")

        record = {
            "record_id": entity_id,
            "issue_id": issue.get("id"),
            "expected_anomaly_label": gt_label,
            "issue_type": issue_type,
            "severity": issue.get("severity", "HIGH"),
            "expected_system_decision": expected_decision,
            "reason": reason,
            "expected_review_action": expected_action
        }
        ground_truth_records.append(record)

    # 1. Export JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth_records, f, indent=2)

    # 2. Export CSV
    if ground_truth_records:
        keys = list(ground_truth_records[0].keys())
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(ground_truth_records)

    return csv_path, json_path, ground_truth_records
