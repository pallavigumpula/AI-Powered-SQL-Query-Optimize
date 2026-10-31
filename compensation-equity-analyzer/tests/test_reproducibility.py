"""
Automated Tests for 100% Deterministic Reproducibility
"""

import pytest
from services.reproducibility import run_reproducibility_check
from config import settings

def test_deterministic_reproducibility():
    res = run_reproducibility_check(sample_size=50, seed=settings.RANDOM_SEED)
    assert res["reproducibility_status"] == "VERIFIED_DETERMINISTIC"
    assert res["run_comparison"]["deterministic_ids_match"] is True
    assert res["run_comparison"]["employee_sha256_match"] is True
    assert res["run_comparison"]["salary_sha256_match"] is True
    assert res["run_comparison"]["performance_sha256_match"] is True
