"""
Unit and Integration Tests for Database Schema and Relationships
"""

import pytest
from sqlalchemy import inspect
from database.db_connection import engine, SessionLocal
from models import (
    Employee, Role, Level, Location, CompensationBand, SalaryRecord,
    PerformanceEvidence, Tenure, Promotion, AdjustmentProposal,
    User, CurrencyExchangeRate, DataQualityIssue
)

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_database_tables_exist():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    required_tables = [
        "employees", "roles", "levels", "locations", "compensation_bands",
        "salary_records", "performance_evidences", "tenures", "promotions",
        "adjustment_proposals", "users", "currency_exchange_rates",
        "approval_history", "adjustment_events", "audit_logs",
        "comparison_groups", "comparison_group_members", "data_quality_issues"
    ]
    for req in required_tables:
        assert req in tables, f"Missing required table {req}"

def test_employee_relationships(db):
    emp = db.query(Employee).first()
    assert emp is not None
    assert emp.role is not None
    assert emp.level is not None
    assert emp.location is not None
    assert len(emp.salary_records) > 0
    assert emp.tenure_record is not None

def test_compensation_band_bounds(db):
    bands = db.query(CompensationBand).filter(CompensationBand.is_active == True).limit(20).all()
    for b in bands:
        assert b.min_salary < b.mid_salary < b.max_salary
        assert b.spread_percentage > 0
