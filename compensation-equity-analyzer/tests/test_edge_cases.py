"""
Integration Tests for All Five Mandatory Edge Cases
"""

import pytest
from datetime import date
from database.db_connection import SessionLocal
from models import DataQualityIssue, SalaryRecord, CompensationBand, ComparisonGroup
from services.salary_calculator import SalaryCalculator
from services.currency_service import CurrencyService
from services.fte_service import FTEService
from services.comparison_service import ComparisonService
from services.approval_service import ApprovalService

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_case_1_expired_compensation_band(db):
    """CASE 1: Salary compared with an expired compensation band."""
    expired_band = db.query(CompensationBand).filter(CompensationBand.is_active == False).first()
    assert expired_band is not None

    calculator = SalaryCalculator(db)
    eval_result = calculator.evaluate_band_status(
        normalized_salary=120000.0,
        band=expired_band,
        as_of_date=date(2026, 10, 22),
        record_id="TEST-SAL-EXP"
    )

    assert eval_result["status"] == "EXPIRED_BAND"
    assert eval_result["is_valid_band"] is False
    assert "expired" in eval_result["message"].lower()

def test_case_2_fte_ignored(db):
    """CASE 2: FTE ignored on part-time compensation."""
    fte_service = FTEService(db)
    is_part_time, normalized_salary, warning = fte_service.validate_fte_comparison(
        employee_id="EMP-TEST",
        actual_salary=60000.0,
        fte=0.5,
        compared_against_salary=120000.0,
        record_id="TEST-SAL-FTE"
    )

    assert is_part_time is True
    assert normalized_salary == 120000.0
    assert "artificial disparity" in warning.lower()

def test_case_3_missing_currency_conversion(db):
    """CASE 3: Missing currency conversion data."""
    currency_service = CurrencyService(db)
    converted, err = currency_service.convert_to_base(
        amount=150000.0,
        from_currency="CHF",
        as_of_date=date(2026, 10, 22),
        record_id="TEST-SAL-CHF"
    )

    assert converted is None
    assert err == "MISSING_EXCHANGE_RATE"

def test_case_4_salary_adjustment_without_approval(db):
    """CASE 4: Salary adjustment applied without approval."""
    approval_service = ApprovalService(db)
    flagged = approval_service.detect_unauthorized_adjustments()
    assert flagged >= 0

    unauthorized_issue = db.query(DataQualityIssue).filter(
        DataQualityIssue.issue_type == "UNAUTHORIZED_ADJUSTMENT"
    ).first()
    assert unauthorized_issue is not None
    assert unauthorized_issue.severity == "CRITICAL"

def test_case_5_incomparable_roles_grouped_without_rationale(db):
    """CASE 5: Incomparable roles grouped without rationale."""
    group = db.query(ComparisonGroup).filter(ComparisonGroup.is_valid == False).first()
    assert group is not None

    comparison_service = ComparisonService(db)
    res = comparison_service.validate_group_compatibility(group)
    assert res["is_valid"] is False
    assert "incompatible" in res["reason"].lower()
