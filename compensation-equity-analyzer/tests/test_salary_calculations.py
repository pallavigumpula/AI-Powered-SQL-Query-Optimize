"""
Unit Tests for Compensation Business Logic and Calculations
"""

import pytest
from datetime import date
from database.db_connection import SessionLocal
from services.salary_calculator import SalaryCalculator
from services.fte_service import FTEService
from services.currency_service import CurrencyService

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_fte_normalization():
    # 0.5 FTE earning 60,000 actual salary has 120,000 full-time normalized salary
    norm = FTEService.normalize_salary(actual_salary=60000.0, fte=0.5)
    assert norm == 120000.0

    # 0.8 FTE earning 100,000 actual salary has 125,000 normalized salary
    norm_80 = FTEService.normalize_salary(actual_salary=100000.0, fte=0.8)
    assert norm_80 == 125000.0

    with pytest.raises(ValueError):
        FTEService.normalize_salary(actual_salary=100000.0, fte=0.0)

def test_compa_ratio_calculation():
    # Salary = Midpoint -> 100%
    cr = SalaryCalculator.calculate_compa_ratio(normalized_salary=150000.0, band_midpoint=150000.0)
    assert cr == 100.0

    # Salary = 120k, Midpoint = 150k -> 80%
    cr_low = SalaryCalculator.calculate_compa_ratio(normalized_salary=120000.0, band_midpoint=150000.0)
    assert cr_low == 80.0

def test_within_band_position():
    # Exactly minimum -> 0%
    pos_min = SalaryCalculator.calculate_within_band_position(100000.0, 100000.0, 200000.0)
    assert pos_min == 0.0

    # Exactly midpoint -> 50%
    pos_mid = SalaryCalculator.calculate_within_band_position(150000.0, 100000.0, 200000.0)
    assert pos_mid == 50.0

    # Exactly maximum -> 100%
    pos_max = SalaryCalculator.calculate_within_band_position(200000.0, 100000.0, 200000.0)
    assert pos_max == 100.0

def test_currency_conversion(db):
    fx = CurrencyService(db)
    # EUR to USD with rate 1.085
    converted, err = fx.convert_to_base(10000.0, "EUR", date(2026, 1, 1))
    assert err is None
    assert converted == 10850.0

    # Missing currency (CHF)
    converted_missing, err_missing = fx.convert_to_base(10000.0, "CHF", date(2026, 1, 1))
    assert converted_missing is None
    assert err_missing == "MISSING_EXCHANGE_RATE"
