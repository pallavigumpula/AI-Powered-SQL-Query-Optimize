"""
End-to-End Synthetic Data Generator Pipeline
Orchestrates master data, employee population, 3-year salary history, edge cases, ground truth, and database seeding.
"""

import sys
import os
import argparse
import csv
import json
from pathlib import Path
from datetime import datetime, date

# Ensure root directory is on PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings, DATA_DIR, DATABASE_DIR
from database.db_connection import init_db, SessionLocal, engine
from models import (
    Role, Level, Location, CompensationBand, Employee, SalaryRecord,
    PerformanceEvidence, Tenure, Promotion, User, CurrencyExchangeRate,
    ComparisonGroup, ComparisonGroupMember, DataQualityIssue, AdjustmentEvent
)
from generator.generate_master_data import get_master_data
from generator.generate_employees import generate_employees
from generator.generate_salary_history import generate_history_for_employees
from generator.generate_edge_cases import inject_edge_cases
from generator.generate_ground_truth import export_ground_truth

def export_to_csv(data: list, filepath: Path, fieldnames: list = None):
    if not data:
        return
    keys = fieldnames or list(data[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)
    print(f"Exported {len(data)} records to {filepath.name}")

def export_seed_sql(
    master_data: dict,
    employees: list,
    salary_records: list,
    perf_records: list,
    promotions: list,
    tenures: list,
    groups: list,
    group_members: list,
    issues: list,
    events: list,
    filepath: Path
):
    """
    Exports MySQL-compatible insert statements for full offline database seeding.
    """
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("-- =============================================================================\n")
        f.write("-- YottaFlex.ai Compensation Equity Analyzer - SQL Seed Data\n")
        f.write(f"-- Generated: {datetime.utcnow().isoformat()}Z | Deterministic Seed: {settings.RANDOM_SEED}\n")
        f.write("-- =============================================================================\n\n")
        f.write("USE `compensation_equity`;\n")
        f.write("SET FOREIGN_KEY_CHECKS = 0;\n\n")

        # Helper to format SQL value
        def sql_val(v):
            if v is None:
                return "NULL"
            if isinstance(v, (int, float)):
                return str(v)
            if isinstance(v, bool):
                return "1" if v else "0"
            if isinstance(v, (date, datetime)):
                return f"'{v.isoformat()}'"
            clean_str = str(v).replace("'", "''").replace("\\", "\\\\")
            return f"'{clean_str}'"

        # 1. Roles
        for r in master_data["roles"]:
            f.write(f"INSERT INTO `roles` (`id`, `code`, `name`, `department`, `job_family`, `description`) VALUES ({sql_val(r['id'])}, {sql_val(r['code'])}, {sql_val(r['name'])}, {sql_val(r['department'])}, {sql_val(r['job_family'])}, {sql_val(r.get('name'))});\n")

        # 2. Levels
        for l in master_data["levels"]:
            f.write(f"INSERT INTO `levels` (`id`, `code`, `name`, `hierarchy_order`, `min_experience_years`) VALUES ({sql_val(l['id'])}, {sql_val(l['code'])}, {sql_val(l['name'])}, {l['hierarchy_order']}, {l['min_experience_years']});\n")

        # 3. Locations
        for loc in master_data["locations"]:
            f.write(f"INSERT INTO `locations` (`id`, `code`, `city`, `country`, `region`, `cost_of_living_index`, `default_currency`) VALUES ({sql_val(loc['id'])}, {sql_val(loc['code'])}, {sql_val(loc['city'])}, {sql_val(loc['country'])}, {sql_val(loc['region'])}, {loc['cost_of_living_index']}, {sql_val(loc['default_currency'])});\n")

        # 4. Exchange Rates
        for fx in master_data["exchange_rates"]:
            f.write(f"INSERT INTO `currency_exchange_rates` (`id`, `from_currency`, `to_currency`, `rate`, `effective_from`, `effective_to`) VALUES ({sql_val(fx['id'])}, {sql_val(fx['from_currency'])}, {sql_val(fx['to_currency'])}, {fx['rate']}, {sql_val(fx['effective_from'])}, {sql_val(fx['effective_to'])});\n")

        # 5. Compensation Bands
        for b in master_data["bands"]:
            f.write(f"INSERT INTO `compensation_bands` (`id`, `role_id`, `level_id`, `location_id`, `currency`, `min_salary`, `mid_salary`, `max_salary`, `effective_from`, `effective_to`, `is_active`) VALUES ({sql_val(b['id'])}, {sql_val(b['role_id'])}, {sql_val(b['level_id'])}, {sql_val(b['location_id'])}, {sql_val(b['currency'])}, {b['min_salary']}, {b['mid_salary']}, {b['max_salary']}, {sql_val(b['effective_from'])}, {sql_val(b['effective_to'])}, {1 if b['is_active'] else 0});\n")

        # 6. Users
        for u in master_data["users"]:
            f.write(f"INSERT INTO `users` (`id`, `username`, `email`, `full_name`, `role`, `employee_id`, `password_hash`, `is_active`) VALUES ({sql_val(u['id'])}, {sql_val(u['username'])}, {sql_val(u['email'])}, {sql_val(u['full_name'])}, {sql_val(u['role'])}, {sql_val(u['employee_id'])}, {sql_val(u['password_hash'])}, 1);\n")

        f.write("\nSET FOREIGN_KEY_CHECKS = 1;\n")
    print(f"Exported MySQL seed SQL file to {filepath.name}")

def run_pipeline(employee_count: int = 250, seed: int = settings.RANDOM_SEED):
    print("=" * 70)
    print(f"YottaFlex.ai Compensation Equity Analyzer - Data Pipeline")
    print(f"Configured Size: {employee_count} employees | Seed: {seed}")
    print("=" * 70)

    # 1. Initialize DB tables
    init_db()
    db = SessionLocal()

    # Clear existing data to allow fresh deterministic re-run
    db.query(DataQualityIssue).delete()
    db.query(AdjustmentEvent).delete()
    db.query(ComparisonGroupMember).delete()
    db.query(ComparisonGroup).delete()
    db.query(SalaryRecord).delete()
    db.query(PerformanceEvidence).delete()
    db.query(Promotion).delete()
    db.query(Tenure).delete()
    db.query(User).delete()
    db.query(Employee).delete()
    db.query(CompensationBand).delete()
    db.query(CurrencyExchangeRate).delete()
    db.query(Role).delete()
    db.query(Level).delete()
    db.query(Location).delete()
    db.commit()

    # 2. Master Data
    master = get_master_data(seed=seed)
    for r in master["roles"]:
        db.add(Role(id=r["id"], code=r["code"], name=r["name"], department=r["department"], job_family=r["job_family"], description=r.get("name")))
    for l in master["levels"]:
        db.add(Level(id=l["id"], code=l["code"], name=l["name"], hierarchy_order=l["hierarchy_order"], min_experience_years=l["min_experience_years"]))
    for loc in master["locations"]:
        db.add(Location(id=loc["id"], code=loc["code"], city=loc["city"], country=loc["country"], region=loc["region"], cost_of_living_index=loc["cost_of_living_index"], default_currency=loc["default_currency"]))
    for fx in master["exchange_rates"]:
        db.add(CurrencyExchangeRate(id=fx["id"], from_currency=fx["from_currency"], to_currency=fx["to_currency"], rate=fx["rate"], effective_from=fx["effective_from"], effective_to=fx["effective_to"]))
    for b in master["bands"]:
        db.add(CompensationBand(id=b["id"], role_id=b["role_id"], level_id=b["level_id"], location_id=b["location_id"], currency=b["currency"], min_salary=b["min_salary"], mid_salary=b["mid_salary"], max_salary=b["max_salary"], effective_from=b["effective_from"], effective_to=b["effective_to"], is_active=b["is_active"]))
    db.commit()
    print("Master data committed successfully.")

    # 3. Employees & Tenure
    employees = generate_employees(
        count=employee_count,
        roles=master["roles"],
        levels=master["levels"],
        locations=master["locations"],
        seed=seed
    )

    tenures_to_insert = []
    for emp in employees:
        db.add(Employee(
            id=emp["id"],
            first_name=emp["first_name"],
            last_name=emp["last_name"],
            email=emp["email"],
            department=emp["department"],
            role_id=emp["role_id"],
            level_id=emp["level_id"],
            location_id=emp["location_id"],
            manager_id=emp["manager_id"],
            hire_date=emp["hire_date"],
            status=emp["status"],
            fte=emp["fte"],
            currency=emp["currency"]
        ))
        t = emp["tenure"]
        tenures_to_insert.append(t)
        db.add(Tenure(
            id=t["id"],
            employee_id=t["employee_id"],
            total_months_experience=t["total_months_experience"],
            company_tenure_months=t["company_tenure_months"],
            role_tenure_months=t["role_tenure_months"],
            prior_experience_months=t["prior_experience_months"],
            last_calculated_date=t["last_calculated_date"]
        ))
    db.commit()
    print(f"{len(employees)} Employees and Tenures committed.")

    # Insert Users after Employees exist
    for u in master["users"]:
        db.add(User(id=u["id"], username=u["username"], email=u["email"], full_name=u["full_name"], role=u["role"], employee_id=u["employee_id"], password_hash=u["password_hash"], is_active=True))
    db.commit()
    print("System users committed successfully.")

    # 4. Salary History, Performance, Promotions
    salary_records, perf_records, promotions = generate_history_for_employees(
        employees=employees,
        bands=master["bands"],
        exchange_rates=master["exchange_rates"],
        levels=master["levels"],
        seed=seed
    )

    # Comparison Groups setup
    groups = [
        {
            "id": "GRP-SWE-L3-US",
            "name": "Senior Software Engineers - US",
            "role_id": "ROLE-SWE",
            "level_id": "LVL-L3",
            "location_id": "LOC-US-NYC",
            "rationale": "Standard comparable peer group for L3 Software Engineers in US metro markets.",
            "is_valid": True,
            "created_at": datetime.utcnow()
        },
        {
            "id": "GRP-AI-L4-METRO",
            "name": "Staff AI & ML Engineers",
            "role_id": "ROLE-MLE",
            "level_id": "LVL-L4",
            "location_id": "LOC-US-SF",
            "rationale": "High-complexity research and modeling engineers with equivalent technical scope.",
            "is_valid": True,
            "created_at": datetime.utcnow()
        }
    ]
    group_members = []
    # Add members to groups
    for emp in employees:
        if emp["role_id"] == "ROLE-SWE" and emp["level_id"] == "LVL-L3":
            group_members.append({"comparison_group_id": "GRP-SWE-L3-US", "employee_id": emp["id"], "joined_date": date(2024, 1, 1)})
        elif emp["role_id"] in ["ROLE-MLE", "ROLE-FDAIE"] and emp["level_id"] == "LVL-L4":
            group_members.append({"comparison_group_id": "GRP-AI-L4-METRO", "employee_id": emp["id"], "joined_date": date(2024, 1, 1)})

    # 5. Inject 5 Mandatory Edge Cases
    salary_records, adjustment_events, data_quality_issues = inject_edge_cases(
        employees=employees,
        salary_records=salary_records,
        bands=master["bands"],
        groups=groups,
        group_members=group_members
    )

    # Insert Groups & Members
    for g in groups:
        db.add(ComparisonGroup(id=g["id"], name=g["name"], role_id=g["role_id"], level_id=g["level_id"], location_id=g["location_id"], rationale=g["rationale"], is_valid=g["is_valid"]))
    for gm in group_members:
        db.add(ComparisonGroupMember(comparison_group_id=gm["comparison_group_id"], employee_id=gm["employee_id"], joined_date=gm["joined_date"]))
    
    # Bulk insert performance, promotions, salary records in batches
    for p in perf_records:
        db.add(PerformanceEvidence(id=p["id"], employee_id=p["employee_id"], review_cycle=p["review_cycle"], rating=p["rating"], goal_completion_percentage=p["goal_completion_percentage"], evidence_summary=p["evidence_summary"], reviewer_id=p["reviewer_id"], review_date=p["review_date"]))
    for pr in promotions:
        db.add(Promotion(id=pr["id"], employee_id=pr["employee_id"], from_level_id=pr["from_level_id"], to_level_id=pr["to_level_id"], effective_date=pr["effective_date"], justification=pr["justification"], salary_increase_pct=pr["salary_increase_pct"], approved_by=pr["approved_by"]))
    for evt in adjustment_events:
        db.add(AdjustmentEvent(id=evt["id"], proposal_id=evt["proposal_id"], employee_id=evt["employee_id"], old_salary=evt["old_salary"], new_salary=evt["new_salary"], effective_date=evt["effective_date"], is_authorized=evt["is_authorized"], applied_by=evt["applied_by"], notes=evt["notes"]))
    for dqi in data_quality_issues:
        db.add(DataQualityIssue(id=dqi["id"], issue_type=dqi["issue_type"], severity=dqi["severity"], entity_type=dqi["entity_type"], entity_id=dqi["entity_id"], description=dqi["description"], status=dqi["status"], ground_truth_label=dqi["ground_truth_label"]))

    # Insert salary records
    batch_size = 1000
    for i in range(0, len(salary_records), batch_size):
        batch = salary_records[i:i + batch_size]
        for s in batch:
            db.add(SalaryRecord(
                id=s["id"],
                employee_id=s["employee_id"],
                band_id=s["band_id"],
                amount=s["amount"],
                currency=s["currency"],
                effective_date=s["effective_date"],
                fte=s["fte"],
                normalized_salary=s["normalized_salary"],
                compa_ratio=s["compa_ratio"],
                within_band_position=s["within_band_position"],
                band_status=s["band_status"],
                is_current=s["is_current"]
            ))
        db.commit()
    db.commit()
    print(f"Committed {len(salary_records)} Salary Records, {len(perf_records)} Performance Reviews, and {len(promotions)} Promotions.")

    # 6. Export Ground Truth
    export_ground_truth(data_quality_issues, output_dir=DATA_DIR)
    print("Exported Ground Truth datasets (CSV & JSON).")

    # 7. Export CSV files
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    export_to_csv(employees, DATA_DIR / "employees.csv", ["id", "first_name", "last_name", "email", "department", "role_id", "level_id", "location_id", "manager_id", "hire_date", "status", "fte", "currency"])
    export_to_csv(master["roles"], DATA_DIR / "roles.csv", ["id", "code", "name", "department", "job_family"])
    export_to_csv(master["levels"], DATA_DIR / "levels.csv", ["id", "code", "name", "hierarchy_order", "min_experience_years"])
    export_to_csv(master["locations"], DATA_DIR / "locations.csv", ["id", "code", "city", "country", "region", "cost_of_living_index", "default_currency"])
    export_to_csv(master["bands"], DATA_DIR / "compensation_bands.csv", ["id", "role_id", "level_id", "location_id", "currency", "min_salary", "mid_salary", "max_salary", "effective_from", "effective_to", "is_active"])
    export_to_csv(salary_records, DATA_DIR / "salary_records.csv", ["id", "employee_id", "band_id", "amount", "currency", "effective_date", "fte", "normalized_salary", "compa_ratio", "within_band_position", "band_status", "is_current"])
    export_to_csv(perf_records, DATA_DIR / "performance_evidence.csv", ["id", "employee_id", "review_cycle", "rating", "goal_completion_percentage", "evidence_summary", "reviewer_id", "review_date"])
    export_to_csv(promotions, DATA_DIR / "promotions.csv", ["id", "employee_id", "from_level_id", "to_level_id", "effective_date", "justification", "salary_increase_pct", "approved_by"])

    # 8. Export Seed SQL
    export_seed_sql(
        master_data=master,
        employees=employees,
        salary_records=salary_records,
        perf_records=perf_records,
        promotions=promotions,
        tenures=tenures_to_insert,
        groups=groups,
        group_members=group_members,
        issues=data_quality_issues,
        events=adjustment_events,
        filepath=DATABASE_DIR / "seed.sql"
    )

    db.close()
    print("=" * 70)
    print(f"Pipeline completed successfully!")
    print(f"Total Employees: {len(employees)}")
    print(f"Total Salary Records: {len(salary_records)}")
    print(f"Total Edge Case Issues: {len(data_quality_issues)}")
    print("=" * 70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synthetic Data Generation Pipeline")
    parser.add_argument("--size", type=int, default=250, help="Number of employees to generate (e.g. 250 for starter, 5000 for full)")
    parser.add_argument("--seed", type=int, default=settings.RANDOM_SEED, help="Deterministic random seed")
    args = parser.parse_args()

    run_pipeline(employee_count=args.size, seed=args.seed)
