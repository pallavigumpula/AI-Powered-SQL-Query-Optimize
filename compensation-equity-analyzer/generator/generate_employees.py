"""
Synthetic Employee Generator
Generates realistic employees, reporting hierarchies, and tenure profiles.
Fixed seed 20261022 for deterministic output.
"""

import random
from datetime import date, timedelta
from typing import List, Dict, Any
from faker import Faker
from config import settings

def generate_employees(
    count: int = 5000,
    roles: List[Dict[str, Any]] = None,
    levels: List[Dict[str, Any]] = None,
    locations: List[Dict[str, Any]] = None,
    seed: int = settings.RANDOM_SEED
) -> List[Dict[str, Any]]:
    random.seed(seed)
    fake = Faker()
    fake.seed_instance(seed)

    # Weights for levels: L1 (15%), L2 (30%), L3 (30%), L4 (15%), L5 (7%), L6 (3%)
    level_weights = [0.15, 0.30, 0.30, 0.15, 0.07, 0.03]
    level_ids = [lvl["id"] for lvl in levels]

    # Weights for roles: Engineering & AI heavy
    role_weights = [
        0.14, 0.06, 0.08, 0.08, # SWE, QA, DEVOPS, DATAENG
        0.08, 0.06, 0.08, 0.06, # MLE, AIRES, FDAIE, DATASCI
        0.08, 0.05, 0.04,       # PM, PRODDES, UXRES
        0.05, 0.04, 0.04, 0.04, 0.02 # HRBP, TA, FIN, AE, CSM
    ]
    role_ids = [r["id"] for r in roles]

    # Location distribution
    location_weights = [0.25, 0.20, 0.15, 0.12, 0.10, 0.10, 0.05, 0.03]
    location_ids = [loc["id"] for loc in locations]

    # FTE weights: 88% full-time, 7% 0.8 FTE, 5% 0.5 FTE
    fte_choices = [1.0, 0.8, 0.5]
    fte_weights = [0.88, 0.07, 0.05]

    employees = []
    manager_pool_by_level = {lvl["id"]: [] for lvl in levels}

    # First pass: Create leadership (L5, L6) to establish manager tree
    reference_date = date(2026, 10, 22)

    for i in range(1, count + 1):
        emp_id = f"EMP-{i:06d}"
        
        # Pick level, role, location deterministically
        level_id = random.choices(level_ids, weights=level_weights)[0]
        role_id = random.choices(role_ids, weights=role_weights)[0]
        loc_id = random.choices(location_ids, weights=location_weights)[0]

        role_obj = next(r for r in roles if r["id"] == role_id)
        loc_obj = next(l for l in locations if l["id"] == loc_id)
        lvl_obj = next(l for l in levels if l["id"] == level_id)

        # First and last names
        gender = random.choice(["M", "F"])
        first_name = fake.first_name_male() if gender == "M" else fake.first_name_female()
        last_name = fake.last_name()
        clean_first = "".join(c for c in first_name.lower() if c.isalnum())
        clean_last = "".join(c for c in last_name.lower() if c.isalnum())
        email = f"{clean_first}.{clean_last}.{i}@yottaflex.ai"

        # Hire date (between 2018-01-01 and 2026-06-01)
        # Higher levels generally joined earlier or had more prior experience
        min_exp_years = lvl_obj["min_experience_years"]
        days_at_company = random.randint(120, 2800)
        hire_date = reference_date - timedelta(days=days_at_company)
        if hire_date < date(2018, 1, 1):
            hire_date = date(2018, 1, 1) + timedelta(days=random.randint(0, 365))

        company_tenure_months = max(1, int((reference_date - hire_date).days / 30.4))
        prior_experience_months = random.randint(min_exp_years * 12, (min_exp_years + 6) * 12)
        total_experience_months = company_tenure_months + prior_experience_months

        # FTE
        fte = random.choices(fte_choices, weights=fte_weights)[0]

        # Currency
        currency = loc_obj["default_currency"]

        # Manager assignment
        manager_id = None
        if lvl_obj["hierarchy_order"] < 6:
            # Report to a manager with hierarchy_order + 1 or + 2
            higher_levels = [l["id"] for l in levels if l["hierarchy_order"] > lvl_obj["hierarchy_order"]]
            candidate_mgrs = []
            for h_lvl in higher_levels:
                candidate_mgrs.extend(manager_pool_by_level[h_lvl])
            if candidate_mgrs:
                manager_id = random.choice(candidate_mgrs)

        # Store in manager pool if senior
        if lvl_obj["hierarchy_order"] >= 4:
            manager_pool_by_level[level_id].append(emp_id)

        employees.append({
            "id": emp_id,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "department": role_obj["department"],
            "role_id": role_id,
            "level_id": level_id,
            "location_id": loc_id,
            "manager_id": manager_id,
            "hire_date": hire_date,
            "status": "Active",
            "fte": fte,
            "currency": currency,
            "tenure": {
                "id": f"TEN-{emp_id}",
                "employee_id": emp_id,
                "total_months_experience": total_experience_months,
                "company_tenure_months": company_tenure_months,
                "role_tenure_months": min(company_tenure_months, random.randint(6, 36)),
                "prior_experience_months": prior_experience_months,
                "last_calculated_date": reference_date
            }
        })

    return employees
