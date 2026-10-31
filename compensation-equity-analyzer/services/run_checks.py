"""
CLI Verification Runner
Executes validator, ground truth evaluator, and reproducibility check.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.db_connection import SessionLocal
from services.validator import DataValidator
from services.evaluator import GroundTruthEvaluator
from services.reproducibility import run_reproducibility_check

def main():
    db = SessionLocal()

    print("=" * 60)
    print("1. RUNNING DATA VALIDATOR")
    print("=" * 60)
    validator = DataValidator(db)
    val_res = validator.run_all_validations()
    print("Validation Overall Status:", val_res["overall_status"])
    for k, v in val_res["checks"].items():
        print(f"  - {k}: {v.get('passed')}")

    print("\n" + "=" * 60)
    print("2. RUNNING GROUND TRUTH EVALUATION")
    print("=" * 60)
    evaluator = GroundTruthEvaluator(db)
    eval_res = evaluator.evaluate()
    print("Precision:", eval_res["metrics"]["precision_percentage"], "%")
    print("Recall:", eval_res["metrics"]["recall_percentage"], "%")
    print("F1-Score:", eval_res["metrics"]["f1_score"])
    print("Coverage:", eval_res["metrics"]["exception_detection_coverage_pct"], "%")
    print("Confusion Matrix:", eval_res["confusion_matrix"])

    print("\n" + "=" * 60)
    print("3. RUNNING REPRODUCIBILITY CHECK (Seed 20261022)")
    print("=" * 60)
    rep_res = run_reproducibility_check(sample_size=100)
    print("Reproducibility Status:", rep_res["reproducibility_status"])
    print("Deterministic IDs Match:", rep_res["run_comparison"]["deterministic_ids_match"])
    print("Employee SHA-256 Match:", rep_res["run_comparison"]["employee_sha256_match"])
    print("Salary SHA-256 Match:", rep_res["run_comparison"]["salary_sha256_match"])
    print("Performance SHA-256 Match:", rep_res["run_comparison"]["performance_sha256_match"])

    db.close()
    print("\nAll checks completed successfully!")

if __name__ == "__main__":
    main()
