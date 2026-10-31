"""
FTE Normalization Service
Normalizes actual salary to Full-Time Equivalent (FTE 1.0) baseline.
Detects when unnormalized part-time compensation is incorrectly compared against full-time peers.
"""

from typing import Tuple, Optional
from sqlalchemy.orm import Session
from models.supporting import DataQualityIssue

class FTEService:
    def __init__(self, db: Optional[Session] = None):
        self.db = db

    @staticmethod
    def normalize_salary(actual_salary: float, fte: float) -> float:
        """
        Calculates FTE-adjusted full-time equivalent salary:
        FTE Adjusted Salary = Actual Salary / FTE
        """
        if not fte or fte <= 0:
            raise ValueError(f"FTE must be strictly positive, received {fte}")
        return round(actual_salary / fte, 2)

    def validate_fte_comparison(
        self,
        employee_id: str,
        actual_salary: float,
        fte: float,
        compared_against_salary: float,
        record_id: Optional[str] = None
    ) -> Tuple[bool, float, Optional[str]]:
        """
        Checks whether salary is being compared on a raw basis without FTE normalization.
        If fte < 1.0 and comparison was raw, flags the edge case and recalculates normalized salary.
        """
        normalized_salary = self.normalize_salary(actual_salary, fte)
        
        # Edge Case 2: FTE Ignored check
        # If someone compared raw actual_salary directly while FTE < 0.95
        if fte < 0.95:
            disparity_raw = round(abs(actual_salary - compared_against_salary), 2)
            disparity_norm = round(abs(normalized_salary - compared_against_salary), 2)
            
            warning_msg = (
                f"Employee {employee_id} is part-time (FTE={fte}). "
                f"Raw salary ${actual_salary:,.2f} produces an artificial disparity of ${disparity_raw:,.2f}. "
                f"Recalculated full-time equivalent is ${normalized_salary:,.2f} (disparity ${disparity_norm:,.2f})."
            )

            if self.db and record_id:
                existing_issue = self.db.query(DataQualityIssue).filter(
                    DataQualityIssue.issue_type == "FTE_IGNORED",
                    DataQualityIssue.entity_id == record_id,
                    DataQualityIssue.status == "OPEN"
                ).first()
                if not existing_issue:
                    issue = DataQualityIssue(
                        id=f"DQI-FTE-{record_id}",
                        issue_type="FTE_IGNORED",
                        severity="HIGH",
                        entity_type="SalaryRecord",
                        entity_id=record_id,
                        description=warning_msg,
                        status="OPEN",
                        ground_truth_label="CASE_2_FTE_IGNORED"
                    )
                    self.db.add(issue)
                    self.db.commit()

            return True, normalized_salary, warning_msg

        return False, normalized_salary, None
