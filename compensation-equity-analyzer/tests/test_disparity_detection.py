"""
Unit Tests for Disparity Detection and Ethical Explainability
"""

import pytest
from database.db_connection import SessionLocal
from models import Employee
from services.disparity_detector import DisparityDetector

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_disparity_detector_output_structure(db):
    emp = db.query(Employee).filter(Employee.status == "Active").first()
    assert emp is not None

    detector = DisparityDetector(db)
    result = detector.analyze_employee(emp)

    required_keys = [
        "employee_id", "employee_name", "role", "level", "location",
        "actual_salary", "normalized_salary", "group_median_salary",
        "salary_difference", "percentage_difference", "z_score",
        "compa_ratio", "within_band_position", "performance_rating",
        "tenure_years", "possible_explanation", "review_recommendation",
        "confidence_score"
    ]
    for key in required_keys:
        assert key in result, f"Key '{key}' missing from disparity analysis"

def test_no_automated_discrimination_declaration(db):
    detector = DisparityDetector(db)
    disparities = detector.detect_all_disparities(limit=50)

    for d in disparities:
        # Ethical compliance: Never declare an employee discriminated against automatically
        recommendation = d["review_recommendation"].lower()
        explanation = d["possible_explanation"].lower()
        assert "discriminated" not in recommendation
        assert "illegal discrimination" not in explanation
        # Must recommend human review or legitimate business justification
        assert any(term in recommendation for term in ["review", "monitor", "coaching", "aligned", "re-evaluate", "competitive", "freeze"])
