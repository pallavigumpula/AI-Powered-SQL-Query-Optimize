"""
Reproducibility Verification Service
Executes deterministic verification across multiple generation runs with fixed seed 20261022.
Computes SHA-256 checksums, validates row counts, and generates reproducibility_report.json.
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, Any, List

from config import settings, DATA_DIR, DOCS_DIR
from generator.generate_master_data import get_master_data
from generator.generate_employees import generate_employees
from generator.generate_salary_history import generate_history_for_employees

def calculate_sha256(data_bytes: bytes) -> str:
    return hashlib.sha256(data_bytes).hexdigest()

def calculate_file_sha256(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def run_reproducibility_check(sample_size: int = 100, seed: int = settings.RANDOM_SEED) -> Dict[str, Any]:
    """
    Executes two independent generation runs from scratch using fixed seed.
    Compares record counts, ID sequences, serialized payloads, and cryptographic hashes.
    """
    # Run 1
    master_1 = get_master_data(seed=seed)
    emps_1 = generate_employees(count=sample_size, roles=master_1["roles"], levels=master_1["levels"], locations=master_1["locations"], seed=seed)
    salaries_1, perf_1, promo_1 = generate_history_for_employees(emps_1, master_1["bands"], master_1["exchange_rates"], master_1["levels"], seed=seed)

    # Run 2
    master_2 = get_master_data(seed=seed)
    emps_2 = generate_employees(count=sample_size, roles=master_2["roles"], levels=master_2["levels"], locations=master_2["locations"], seed=seed)
    salaries_2, perf_2, promo_2 = generate_history_for_employees(emps_2, master_2["bands"], master_2["exchange_rates"], master_2["levels"], seed=seed)

    # Hash payloads
    hash_emp_1 = calculate_sha256(json.dumps(emps_1, default=str, sort_keys=True).encode("utf-8"))
    hash_emp_2 = calculate_sha256(json.dumps(emps_2, default=str, sort_keys=True).encode("utf-8"))

    hash_sal_1 = calculate_sha256(json.dumps(salaries_1, default=str, sort_keys=True).encode("utf-8"))
    hash_sal_2 = calculate_sha256(json.dumps(salaries_2, default=str, sort_keys=True).encode("utf-8"))

    hash_perf_1 = calculate_sha256(json.dumps(perf_1, default=str, sort_keys=True).encode("utf-8"))
    hash_perf_2 = calculate_sha256(json.dumps(perf_2, default=str, sort_keys=True).encode("utf-8"))

    # File checksums on current data directory
    csv_checksums = {}
    csv_files = ["employees.csv", "roles.csv", "levels.csv", "locations.csv", "compensation_bands.csv", "salary_records.csv", "ground_truth.csv"]
    for fname in csv_files:
        fpath = DATA_DIR / fname
        if fpath.exists():
            csv_checksums[fname] = calculate_file_sha256(fpath)

    # Verify ID match
    ids_emp_1 = [e["id"] for e in emps_1]
    ids_emp_2 = [e["id"] for e in emps_2]
    ids_identical = (ids_emp_1 == ids_emp_2)

    emp_match = (hash_emp_1 == hash_emp_2)
    sal_match = (hash_sal_1 == hash_sal_2)
    perf_match = (hash_perf_1 == hash_perf_2)
    counts_match = (len(emps_1) == len(emps_2)) and (len(salaries_1) == len(salaries_2))

    all_identical = emp_match and sal_match and perf_match and ids_identical and counts_match

    report = {
        "reproducibility_status": "VERIFIED_DETERMINISTIC" if all_identical else "FAILED",
        "fixed_seed": seed,
        "sample_size": sample_size,
        "run_comparison": {
            "employees_row_count_run1": len(emps_1),
            "employees_row_count_run2": len(emps_2),
            "salary_records_count_run1": len(salaries_1),
            "salary_records_count_run2": len(salaries_2),
            "performance_records_count_run1": len(perf_1),
            "performance_records_count_run2": len(perf_2),
            "deterministic_ids_match": ids_identical,
            "employee_sha256_match": emp_match,
            "salary_sha256_match": sal_match,
            "performance_sha256_match": perf_match,
            "run1_employee_sha256": hash_emp_1,
            "run2_employee_sha256": hash_emp_2,
            "run1_salary_sha256": hash_sal_1,
            "run2_salary_sha256": hash_sal_2
        },
        "file_sha256_checksums": csv_checksums
    }

    # Export report to documentation/reproducibility_report.json
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DOCS_DIR / "reproducibility_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report
