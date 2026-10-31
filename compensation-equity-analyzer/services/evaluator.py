"""
Ground Truth Evaluation Engine
Evaluates disparity detector and data quality monitors against isolated ground truth datasets.
Calculates Precision, Recall, F1-Score, Confusion Matrix, and Exception Coverage.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from config import settings, DATA_DIR, DOCS_DIR
from models import (
    Employee, SalaryRecord, DataQualityIssue, AdjustmentProposal,
    ComparisonGroup, AdjustmentEvent
)
from services.disparity_detector import DisparityDetector
from services.comparison_service import ComparisonService

class GroundTruthEvaluator:
    def __init__(self, db: Session, ground_truth_file: Path = DATA_DIR / "ground_truth.json"):
        self.db = db
        self.gt_file = ground_truth_file
        self.detector = DisparityDetector(db)
        self.comparison_service = ComparisonService(db)

    def evaluate(self) -> Dict[str, Any]:
        """
        Executes benchmark evaluation against the ground truth labels.
        """
        if not self.gt_file.exists():
            return {"error": f"Ground truth file not found at {self.gt_file}"}

        with open(self.gt_file, "r", encoding="utf-8") as f:
            gt_records = json.load(f)

        gt_anomaly_ids = {item["record_id"]: item for item in gt_records}
        total_ground_truth_anomalies = len(gt_records)

        # 1. Evaluate Data Quality Exceptions Detection
        detected_issues = self.db.query(DataQualityIssue).all()
        detected_entity_ids = {issue.entity_id: issue for issue in detected_issues}

        tp_ids = set()
        fn_ids = set()

        for rec_id, gt_item in gt_anomaly_ids.items():
            if rec_id in detected_entity_ids:
                tp_ids.add(rec_id)
            else:
                fn_ids.add(rec_id)

        # False positives: detected issues that were not in ground truth
        fp_ids = set(detected_entity_ids.keys()) - set(gt_anomaly_ids.keys())

        # Total population size
        total_salary_records = self.db.query(SalaryRecord).count()
        total_groups = self.db.query(ComparisonGroup).count()
        total_events = self.db.query(AdjustmentEvent).count()
        total_evaluated_entities = total_salary_records + total_groups + total_events

        # True Negatives: entities that are neither ground truth anomalies nor falsely flagged
        tn_count = max(0, total_evaluated_entities - (len(tp_ids) + len(fp_ids) + len(fn_ids)))

        tp = len(tp_ids)
        fp = len(fp_ids)
        fn = len(fn_ids)
        tn = tn_count

        precision = round((tp / (tp + fp)) * 100.0, 2) if (tp + fp) > 0 else 0.0
        recall = round((tp / (tp + fn)) * 100.0, 2) if (tp + fn) > 0 else 0.0
        f1_score = round(2 * (precision * recall) / (precision + recall), 2) if (precision + recall) > 0 else 0.0
        fpr = round((fp / (fp + tn)) * 100.0, 4) if (fp + tn) > 0 else 0.0
        fnr = round((fn / (fn + tp)) * 100.0, 2) if (fn + tp) > 0 else 0.0
        coverage = round((tp / total_ground_truth_anomalies) * 100.0, 2) if total_ground_truth_anomalies > 0 else 100.0

        # Detailed breakdown per Edge Case
        case_breakdown = {}
        for item in gt_records:
            case_label = item["expected_anomaly_label"]
            rec_id = item["record_id"]
            detected = rec_id in detected_entity_ids
            case_breakdown[case_label] = {
                "record_id": rec_id,
                "issue_type": item["issue_type"],
                "detected": detected,
                "expected_decision": item["expected_system_decision"],
                "status": "PASS" if detected else "FAIL"
            }

        # Operational metrics
        total_records = self.db.query(SalaryRecord).count()
        invalid_records = self.db.query(DataQualityIssue).filter(DataQualityIssue.status == "OPEN").count()
        valid_records = max(0, total_records - invalid_records)
        proposals_count = self.db.query(AdjustmentProposal).count()
        reconciled_count = self.db.query(DataQualityIssue).filter(DataQualityIssue.status == "RESOLVED").count()

        evaluation_results = {
            "evaluation_timestamp": settings.HISTORY_END_DATE,
            "metrics": {
                "precision_percentage": precision,
                "recall_percentage": recall,
                "f1_score": f1_score,
                "false_positive_rate": fpr,
                "false_negative_rate": fnr,
                "exception_detection_coverage_pct": coverage
            },
            "confusion_matrix": {
                "true_positives": tp,
                "false_positives": fp,
                "true_negatives": tn,
                "false_negatives": fn
            },
            "edge_case_verification": case_breakdown,
            "operational_report": {
                "total_records_generated": total_records,
                "valid_records": valid_records,
                "invalid_records": invalid_records,
                "number_of_anomalies": len(gt_records),
                "number_of_proposals_generated": proposals_count,
                "number_of_records_reconciled": reconciled_count
            }
        }

        # Export evaluation results
        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        eval_path = DOCS_DIR / "evaluation_report.json"
        with open(eval_path, "w", encoding="utf-8") as f:
            json.dump(evaluation_results, f, indent=2)

        return evaluation_results
