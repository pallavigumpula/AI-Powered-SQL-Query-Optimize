"""
Synthetic Master Data Generator
Generates Roles, Levels, Locations, Compensation Bands, Exchange Rates, and System Users.
Uses fixed random seed 20261022 for 100% deterministic reproducibility.
"""

import random
from datetime import date, datetime
from typing import List, Dict, Any
from faker import Faker
from config import settings

def get_master_data(seed: int = settings.RANDOM_SEED) -> Dict[str, Any]:
    random.seed(seed)
    fake = Faker()
    fake.seed_instance(seed)

    # 1. Career Levels (L1 to L6)
    levels = [
        {"id": "LVL-L1", "code": "L1", "name": "Associate / Entry", "hierarchy_order": 1, "min_experience_years": 0, "base_min": 75000, "base_max": 95000},
        {"id": "LVL-L2", "code": "L2", "name": "Mid-Level Professional", "hierarchy_order": 2, "min_experience_years": 2, "base_min": 95000, "base_max": 130000},
        {"id": "LVL-L3", "code": "L3", "name": "Senior Professional", "hierarchy_order": 3, "min_experience_years": 5, "base_min": 130000, "base_max": 180000},
        {"id": "LVL-L4", "code": "L4", "name": "Staff / Lead", "hierarchy_order": 4, "min_experience_years": 8, "base_min": 175000, "base_max": 240000},
        {"id": "LVL-L5", "code": "L5", "name": "Principal / Director", "hierarchy_order": 5, "min_experience_years": 12, "base_min": 230000, "base_max": 320000},
        {"id": "LVL-L6", "code": "L6", "name": "Executive / VP", "hierarchy_order": 6, "min_experience_years": 16, "base_min": 310000, "base_max": 460000},
    ]

    # 2. Locations with Cost of Living Index (relative to USD 1.0)
    locations = [
        {"id": "LOC-US-NYC", "code": "US-NYC", "city": "New York", "country": "United States", "region": "Americas", "cost_of_living_index": 1.25, "default_currency": "USD"},
        {"id": "LOC-US-SF", "code": "US-SF", "city": "San Francisco", "country": "United States", "region": "Americas", "cost_of_living_index": 1.30, "default_currency": "USD"},
        {"id": "LOC-US-AUS", "code": "US-AUS", "city": "Austin", "country": "United States", "region": "Americas", "cost_of_living_index": 1.00, "default_currency": "USD"},
        {"id": "LOC-UK-LON", "code": "UK-LON", "city": "London", "country": "United Kingdom", "region": "EMEA", "cost_of_living_index": 1.15, "default_currency": "GBP"},
        {"id": "LOC-DE-BER", "code": "DE-BER", "city": "Berlin", "country": "Germany", "region": "EMEA", "cost_of_living_index": 1.05, "default_currency": "EUR"},
        {"id": "LOC-IN-BLR", "code": "IN-BLR", "city": "Bengaluru", "country": "India", "region": "APAC", "cost_of_living_index": 0.40, "default_currency": "INR"},
        {"id": "LOC-JP-TYO", "code": "JP-TYO", "city": "Tokyo", "country": "Japan", "region": "APAC", "cost_of_living_index": 0.95, "default_currency": "JPY"},
        {"id": "LOC-SG-SIN", "code": "SG-SIN", "city": "Singapore", "country": "Singapore", "region": "APAC", "cost_of_living_index": 1.12, "default_currency": "SGD"},
    ]

    # 3. Roles across Functional Job Families
    roles = [
        # Engineering
        {"id": "ROLE-SWE", "code": "SWE", "name": "Software Engineer", "department": "Engineering", "job_family": "Engineering", "multiplier": 1.0},
        {"id": "ROLE-QA", "code": "QA", "name": "Quality Assurance Engineer", "department": "Engineering", "job_family": "Engineering", "multiplier": 0.90},
        {"id": "ROLE-DEVOPS", "code": "DEVOPS", "name": "DevOps & Cloud Engineer", "department": "Engineering", "job_family": "Engineering", "multiplier": 1.05},
        {"id": "ROLE-DATAENG", "code": "DATAENG", "name": "Data Engineer", "department": "Engineering", "job_family": "Engineering", "multiplier": 1.05},
        # AI & Data
        {"id": "ROLE-MLE", "code": "MLE", "name": "Machine Learning Engineer", "department": "AI Research", "job_family": "AI & Data", "multiplier": 1.18},
        {"id": "ROLE-AIRES", "code": "AIRES", "name": "AI Research Scientist", "department": "AI Research", "job_family": "AI & Data", "multiplier": 1.25},
        {"id": "ROLE-FDAIE", "code": "FDAIE", "name": "Forward Deployed AI Engineer", "department": "AI Research", "job_family": "AI & Data", "multiplier": 1.20},
        {"id": "ROLE-DATASCI", "code": "DATASCI", "name": "Data Scientist", "department": "AI Research", "job_family": "AI & Data", "multiplier": 1.10},
        # Product & Design
        {"id": "ROLE-PM", "code": "PM", "name": "Product Manager", "department": "Product", "job_family": "Product", "multiplier": 1.05},
        {"id": "ROLE-PRODDES", "code": "PRODDES", "name": "Product Designer", "department": "Product", "job_family": "Product", "multiplier": 0.95},
        {"id": "ROLE-UXRES", "code": "UXRES", "name": "UX Researcher", "department": "Product", "job_family": "Product", "multiplier": 0.92},
        # Operations & Business
        {"id": "ROLE-HRBP", "code": "HRBP", "name": "HR Business Partner", "department": "People & HR", "job_family": "Operations", "multiplier": 0.88},
        {"id": "ROLE-TA", "code": "TA", "name": "Talent Acquisition Specialist", "department": "People & HR", "job_family": "Operations", "multiplier": 0.82},
        {"id": "ROLE-FIN", "code": "FIN", "name": "Financial Analyst", "department": "Finance", "job_family": "Operations", "multiplier": 0.92},
        {"id": "ROLE-AE", "code": "AE", "name": "Account Executive", "department": "Sales", "job_family": "Operations", "multiplier": 0.90},
        {"id": "ROLE-CSM", "code": "CSM", "name": "Customer Success Manager", "department": "Sales", "job_family": "Operations", "multiplier": 0.85},
    ]

    # 4. Currency Exchange Rates (to USD)
    exchange_rates = [
        {"id": "FX-USD-USD-2024", "from_currency": "USD", "to_currency": "USD", "rate": 1.0, "effective_from": date(2024, 1, 1), "effective_to": date(2026, 12, 31)},
        {"id": "FX-EUR-USD-2024", "from_currency": "EUR", "to_currency": "USD", "rate": 1.085, "effective_from": date(2024, 1, 1), "effective_to": date(2026, 12, 31)},
        {"id": "FX-GBP-USD-2024", "from_currency": "GBP", "to_currency": "USD", "rate": 1.272, "effective_from": date(2024, 1, 1), "effective_to": date(2026, 12, 31)},
        {"id": "FX-INR-USD-2024", "from_currency": "INR", "to_currency": "USD", "rate": 0.0121, "effective_from": date(2024, 1, 1), "effective_to": date(2026, 12, 31)},
        {"id": "FX-JPY-USD-2024", "from_currency": "JPY", "to_currency": "USD", "rate": 0.0066, "effective_from": date(2024, 1, 1), "effective_to": date(2026, 12, 31)},
        {"id": "FX-SGD-USD-2024", "from_currency": "SGD", "to_currency": "USD", "rate": 0.748, "effective_from": date(2024, 1, 1), "effective_to": date(2026, 12, 31)},
    ]

    # 5. Compensation Bands (Active and Expired for Case 1)
    # Generate for role x level x location combinations
    bands = []
    for r in roles:
        for lvl in levels:
            for loc in locations:
                col = loc["cost_of_living_index"]
                role_mult = r["multiplier"]
                
                # Active Band (2024 to 2026)
                min_s = round(lvl["base_min"] * role_mult * col, 2)
                max_s = round(lvl["base_max"] * role_mult * col, 2)
                mid_s = round((min_s + max_s) / 2.0, 2)
                
                band_id = f"BAND-{r['code']}-{lvl['code']}-{loc['code']}-2026"
                bands.append({
                    "id": band_id,
                    "role_id": r["id"],
                    "level_id": lvl["id"],
                    "location_id": loc["id"],
                    "currency": "USD",
                    "min_salary": min_s,
                    "mid_salary": mid_s,
                    "max_salary": max_s,
                    "effective_from": date(2024, 1, 1),
                    "effective_to": date(2026, 12, 31),
                    "is_active": True
                })

    # Add Expired Bands explicitly to test CASE 1
    # For example, expired in 2023
    for r in roles[:3]:
        for lvl in levels[:3]:
            for loc in locations[:2]:
                exp_band_id = f"BAND-EXPIRED-{r['code']}-{lvl['code']}-{loc['code']}-2023"
                bands.append({
                    "id": exp_band_id,
                    "role_id": r["id"],
                    "level_id": lvl["id"],
                    "location_id": loc["id"],
                    "currency": "USD",
                    "min_salary": round(lvl["base_min"] * 0.85, 2),
                    "mid_salary": round(lvl["base_min"] * 0.95, 2),
                    "max_salary": round(lvl["base_max"] * 0.85, 2),
                    "effective_from": date(2022, 1, 1),
                    "effective_to": date(2023, 12, 31),
                    "is_active": False
                })

    # 6. Default Role-Based Users
    # 5 standard roles
    users = [
        {
            "id": "USR-001",
            "username": "employee",
            "email": "employee@yottaflex.ai",
            "full_name": "Elena Rostova (Staff AI Engineer)",
            "role": settings.ROLE_EMPLOYEE,
            "employee_id": "EMP-000001",
            "password_hash": "pbkdf2:sha256:demo123"
        },
        {
            "id": "USR-002",
            "username": "manager",
            "email": "manager@yottaflex.ai",
            "full_name": "Marcus Vance (Engineering Manager)",
            "role": settings.ROLE_MANAGER,
            "employee_id": "EMP-000010",
            "password_hash": "pbkdf2:sha256:demo123"
        },
        {
            "id": "USR-003",
            "username": "hr_partner",
            "email": "hr@yottaflex.ai",
            "full_name": "Sarah Jenkins (Senior HR Business Partner)",
            "role": settings.ROLE_HR_PARTNER,
            "employee_id": "EMP-000020",
            "password_hash": "pbkdf2:sha256:demo123"
        },
        {
            "id": "USR-004",
            "username": "it_ops",
            "email": "it_ops@yottaflex.ai",
            "full_name": "David Chen (IT & Data Integrity Ops)",
            "role": settings.ROLE_IT_OPS,
            "employee_id": "EMP-000030",
            "password_hash": "pbkdf2:sha256:demo123"
        },
        {
            "id": "USR-005",
            "username": "admin",
            "email": "admin@yottaflex.ai",
            "full_name": "System Administrator",
            "role": settings.ROLE_ADMIN,
            "employee_id": None,
            "password_hash": "pbkdf2:sha256:admin123"
        }
    ]

    return {
        "levels": levels,
        "locations": locations,
        "roles": roles,
        "exchange_rates": exchange_rates,
        "bands": bands,
        "users": users
    }
