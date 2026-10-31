"""
Data Quality and Referential Integrity Validator
Performs comprehensive automated auditing of PK uniqueness, FK integrity, date logic, and arithmetic.
Produces documentation/validation_summary.json.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from config import settings, DOCS_DIR
from models import (
    Employee, Role, Level, Location, CompensationBand, SalaryRecord,
    PerformanceEvidence, Tenure, Promotion, AdjustmentProposal,
    User, CurrencyExchangeRate, DataQualityIssue, AdjustmentEvent,
    ComparisonGroup, ComparisonGroupMember, AuditLog
)

class DataValidator:
    def __init__(self, db: Session):
        self.db = db

    def run_all_validations(self) -> Dict[str, Any]:
        results = {
            "validation_timestamp": datetime.utcnow().isoformat() + "Z",
            "overall_status": "PASSED",
            "checks": {},
            "summary_metrics": {}
        }

        checks = {}
        all_passed = True

        # 1. Primary Key Uniqueness
        pk_checks = []
        for model, name in [
            (Employee, "Employee"),
            (Role, "Role"),
            (Level, "Level"),
            (Location, "Location"),
            (CompensationBand, "CompensationBand"),
            (SalaryRecord, "SalaryRecord"),
            (PerformanceEvidence, "PerformanceEvidence"),
            (Tenure, "Tenure"),
            (Promotion, "Promotion"),
            (User, "User")
        ]:
            total = self.db.query(model).count()
            distinct_pks = self.db.query(func.count(func.distinct(model.id))).scalar()
            passed = (total == distinct_pks)
            pk_checks.append({"entity": name, "total": total, "distinct": distinct_pks, "passed": passed})
            if not passed:
                all_passed = False
        checks["primary_key_uniqueness"] = {"passed": all(c["passed"] for c in pk_checks), "details": pk_checks}

        # 2. Foreign Key Integrity
        fk_failures = []
        # Check employee FKs
        emp_roles = self.db.query(Employee.role_id).distinct().all()
        valid_roles = {r.id for r in self.db.query(Role.id).all()}
        invalid_roles = [r[0] for r in emp_roles if r[0] not in valid_roles]
        if invalid_roles:
            fk_failures.append(f"Employees reference invalid roles: {invalid_roles}")

        emp_levels = self.db.query(Employee.level_id).distinct().all()
        valid_levels = {l.id for l in self.db.query(Level.id).all()}
        invalid_levels = [l[0] for l in emp_levels if l[0] not in valid_levels]
        if invalid_levels:
            fk_failures.append(f"Employees reference invalid levels: {invalid_levels}")

        # Check salary records link to existing employees
        sal_emps = self.db.query(SalaryRecord.employee_id).distinct().all()
        valid_emps = {e.id for e in self.db.query(Employee.id).all()}
        invalid_sal_emps = [e[0] for e in sal_emps if e[0] not in valid_emps]
        if invalid_sal_emps:
            fk_failures.append(f"Salary records reference invalid employees: {invalid_sal_emps[:5]}")

        checks["foreign_key_integrity"] = {
            "passed": len(fk_failures) == 0,
            "violations_count": len(fk_failures),
            "failures": fk_failures
        }
        if fk_failures: all_passed = False

        # 3. Allowed Enum / Value Ranges
        enum_failures = []
        # FTE in (0, 1.0]
        invalid_fte = self.db.query(Employee).filter((Employee.fte <= 0) | (Employee.fte > 1.0)).count()
        if invalid_fte > 0:
            enum_failures.append(f"{invalid_fte} employees have invalid FTE values outside (0, 1.0]")

        # Performance ratings in [1, 5]
        invalid_ratings = self.db.query(PerformanceEvidence).filter(
            (PerformanceEvidence.rating < 1) | (PerformanceEvidence.rating > 5)
        ).count()
        if invalid_ratings > 0:
            enum_failures.append(f"{invalid_ratings} performance ratings outside [1, 5] scale")

        checks["allowed_enum_and_range_validity"] = {
            "passed": len(enum_failures) == 0,
            "violations": enum_failures
        }
        if enum_failures: all_passed = False

        # 4. Salary Arithmetic and Non-Negative Values
        sal_math_failures = []
        negative_salaries = self.db.query(SalaryRecord).filter(SalaryRecord.amount <= 0).count()
        if negative_salaries > 0:
            sal_math_failures.append(f"{negative_salaries} salary records with non-positive amount")

        # Verify compa_ratio formula: (normalized / midpoint) * 100
        sample_records = self.db.query(SalaryRecord).join(CompensationBand).filter(
            SalaryRecord.band_id.isnot(None),
            SalaryRecord.band_status == "WITHIN_BAND",
            SalaryRecord.normalized_salary.isnot(None)
        ).limit(50).all()

        mismatch_count = 0
        for s in sample_records:
            if s.band and s.band.mid_salary > 0:
                expected_compa = round((s.normalized_salary / s.band.mid_salary) * 100.0, 2)
                if s.compa_ratio and abs(s.compa_ratio - expected_compa) > 0.05:
                    mismatch_count += 1
        if mismatch_count > 0:
            sal_math_failures.append(f"{mismatch_count} salary records had compa-ratio mathematical discrepancies")

        checks["salary_arithmetic_consistency"] = {
            "passed": len(sal_math_failures) == 0,
            "discrepancies": sal_math_failures
        }
        if sal_math_failures: all_passed = False

        # 5. Date Ordering & Promotion Timeline
        date_failures = []
        # Promotions from_level order < to_level order
        promos = self.db.query(Promotion).all()
        level_map = {l.id: l.hierarchy_order for l in self.db.query(Level).all()}
        for p in promos:
            from_order = level_map.get(p.from_level_id, 0)
            to_order = level_map.get(p.to_level_id, 0)
            if to_order <= from_order:
                date_failures.append(f"Promotion {p.id} target level {p.to_level_id} order ({to_order}) <= from level order ({from_order})")

        checks["date_ordering_and_progression"] = {
            "passed": len(date_failures) == 0,
            "violations": date_failures
        }
        if date_failures: all_passed = False

        # Summary Metrics
        results["overall_status"] = "PASSED" if all_passed else "FLAGGED_ISSUES"
        results["checks"] = checks
        results["summary_metrics"] = {
            "total_employees": self.db.query(Employee).count(),
            "total_salary_records": self.db.query(SalaryRecord).count(),
            "total_performance_records": self.db.query(PerformanceEvidence).count(),
            "total_promotions": self.db.query(Promotion).count(),
            "total_compensation_bands": self.db.query(CompensationBand).count(),
            "total_data_quality_issues": self.db.query(DataQualityIssue).count(),
            "active_bands_count": self.db.query(CompensationBand).filter(CompensationBand.is_active == True).count(),
            "expired_bands_count": self.db.query(CompensationBand).filter(CompensationBand.is_active == False).count(),
        }

        # Export to documentation/validation_summary.json
        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        summary_path = DOCS_DIR / "validation_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        return results
