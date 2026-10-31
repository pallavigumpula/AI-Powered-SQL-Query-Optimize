"""
Synthetic Salary History, Performance, and Promotion Generator
Simulates 36 months (2024-01 through 2026-12) of career progression, performance reviews, and promotions.
Ensures mathematical consistency between band, FTE, and exchange rates.
"""

import random
from datetime import date, timedelta
from typing import List, Dict, Any, Tuple
from config import settings

def generate_history_for_employees(
    employees: List[Dict[str, Any]],
    bands: List[Dict[str, Any]],
    exchange_rates: List[Dict[str, Any]],
    levels: List[Dict[str, Any]],
    seed: int = settings.RANDOM_SEED
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    random.seed(seed)

    # Index bands by (role_id, level_id, location_id, is_active)
    active_bands_map = {}
    for b in bands:
        if b["is_active"]:
            key = (b["role_id"], b["level_id"], b["location_id"])
            active_bands_map[key] = b

    # Index rates by from_currency
    rate_map = {r["from_currency"]: r["rate"] for r in exchange_rates if r["to_currency"] == "USD"}

    all_salary_records = []
    all_performance_records = []
    all_promotions = []

    # Historical monthly dates from 2024-01 to 2026-10 (34 to 36 months)
    months = []
    for year in [2024, 2025, 2026]:
        end_m = 10 if year == 2026 else 12
        for m in range(1, end_m + 1):
            months.append(date(year, m, 1))

    # Performance cycles
    perf_cycles = [
        ("2024-H1", date(2024, 6, 30)),
        ("2024-H2", date(2024, 12, 31)),
        ("2025-H1", date(2025, 6, 30)),
        ("2025-H2", date(2025, 12, 31)),
        ("2026-H1", date(2026, 6, 30)),
    ]

    promotion_counter = 1

    for emp in employees:
        emp_id = emp["id"]
        hire_date = emp["hire_date"]
        fte = emp["fte"]
        currency = emp["currency"]
        rate = rate_map.get(currency, 1.0)

        # Baseline performance ratings across cycles (skewed towards 3 and 4)
        # Ratings: 1 (2%), 2 (8%), 3 (50%), 4 (30%), 5 (10%)
        perf_ratings = random.choices([1, 2, 3, 4, 5], weights=[0.02, 0.08, 0.50, 0.30, 0.10], k=len(perf_cycles))

        for idx, (cycle_name, cycle_date) in enumerate(perf_cycles):
            if cycle_date >= hire_date:
                r_val = perf_ratings[idx]
                all_performance_records.append({
                    "id": f"PERF-{emp_id}-{cycle_name}",
                    "employee_id": emp_id,
                    "review_cycle": cycle_name,
                    "rating": r_val,
                    "goal_completion_percentage": round(80.0 + (r_val * 5.0) + random.uniform(-3, 3), 1),
                    "evidence_summary": f"Performance review for {cycle_name}. Delivered on key deliverables, cross-functional collaboration rating: {r_val}/5.",
                    "reviewer_id": emp["manager_id"],
                    "review_date": cycle_date
                })

        # Possible promotion in 2025 if high performer and joined before 2024
        current_level_id = emp["level_id"]
        promoted = False
        promo_date = None
        if hire_date < date(2024, 1, 1) and sum(perf_ratings) >= 17:
            # Check if there is an upper level
            lvl_obj = next(l for l in levels if l["id"] == current_level_id)
            if lvl_obj["hierarchy_order"] < 6 and random.random() < 0.25:
                promoted = True
                next_lvl = next(l for l in levels if l["hierarchy_order"] == lvl_obj["hierarchy_order"] + 1)
                promo_date = date(2025, 7, 1)
                all_promotions.append({
                    "id": f"PROM-2025-{promotion_counter:06d}",
                    "employee_id": emp_id,
                    "from_level_id": current_level_id,
                    "to_level_id": next_lvl["id"],
                    "effective_date": promo_date,
                    "justification": f"Consistently demonstrated leadership and high technical output in {lvl_obj['name']}. Recommended for advancement.",
                    "salary_increase_pct": 14.5,
                    "approved_by": emp["manager_id"] or "HRBP"
                })
                promotion_counter += 1

        # Generate monthly salary records
        # Determine starting salary based on active band
        band_key = (emp["role_id"], current_level_id, emp["location_id"])
        band = active_bands_map.get(band_key)
        
        if not band:
            # Fallback mock band if combination missing
            band = bands[0]

        # Starting normalized full-time salary in USD: centered around band midpoint
        spread = band["max_salary"] - band["min_salary"]
        # Position roughly between 20% and 80% of band based on tenure
        tenure_fraction = min(1.0, emp["tenure"]["total_months_experience"] / 120.0)
        norm_usd_base = band["min_salary"] + (spread * (0.2 + 0.6 * tenure_fraction))
        # Add slight natural Gaussian variance
        norm_usd_base = round(norm_usd_base + random.gauss(0, spread * 0.04), 2)
        norm_usd_base = max(band["min_salary"] * 0.95, min(band["max_salary"] * 1.05, norm_usd_base))

        current_norm_usd = norm_usd_base

        emp_salary_records = []
        for m_date in months:
            if m_date < hire_date:
                continue

            # Check if promotion occurs on this month
            if promoted and promo_date and m_date == promo_date:
                # Upgraded to next level
                lvl_obj = next(l for l in levels if l["id"] == current_level_id)
                next_lvl = next(l for l in levels if l["hierarchy_order"] == lvl_obj["hierarchy_order"] + 1)
                current_level_id = next_lvl["id"]
                band_key = (emp["role_id"], current_level_id, emp["location_id"])
                band = active_bands_map.get(band_key, band)
                current_norm_usd = round(current_norm_usd * 1.145, 2)

            # Annual merit increase in April (2024-04, 2025-04, 2026-04)
            if m_date.month == 4 and m_date > hire_date:
                merit_pct = random.uniform(0.025, 0.055)
                current_norm_usd = round(current_norm_usd * (1.0 + merit_pct), 2)

            # Calculate actual nominal local currency salary:
            # actual_salary = (normalized_USD * FTE) / rate
            actual_local_salary = round((current_norm_usd * fte) / rate, 2)

            # Compa-ratio and position
            compa_ratio = round((current_norm_usd / band["mid_salary"]) * 100.0, 2) if band["mid_salary"] > 0 else 100.0
            spread_band = band["max_salary"] - band["min_salary"]
            within_band = round(((current_norm_usd - band["min_salary"]) / spread_band) * 100.0, 2) if spread_band > 0 else 50.0

            sal_status = "WITHIN_BAND"
            if current_norm_usd < band["min_salary"]:
                sal_status = "BELOW_MINIMUM"
            elif current_norm_usd > band["max_salary"]:
                sal_status = "ABOVE_MAXIMUM"

            record_id = f"SAL-{emp_id}-{m_date.strftime('%Y-%m')}"
            rec = {
                "id": record_id,
                "employee_id": emp_id,
                "band_id": band["id"],
                "amount": actual_local_salary,
                "currency": currency,
                "effective_date": m_date,
                "fte": fte,
                "normalized_salary": current_norm_usd,
                "compa_ratio": compa_ratio,
                "within_band_position": within_band,
                "band_status": sal_status,
                "is_current": False # will set latest to True
            }
            emp_salary_records.append(rec)

        if emp_salary_records:
            # Set latest salary record is_current = True
            emp_salary_records[-1]["is_current"] = True
            all_salary_records.extend(emp_salary_records)

    return all_salary_records, all_performance_records, all_promotions
