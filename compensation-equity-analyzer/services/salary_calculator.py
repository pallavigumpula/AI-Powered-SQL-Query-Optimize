"""
Salary Calculation and Band Validation Service
Implements compa-ratio, within-band position, and salary band lifecycle validation.
"""

from datetime import date
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from models.compensation_band import CompensationBand
from models.supporting import DataQualityIssue

class SalaryCalculator:
    def __init__(self, db: Optional[Session] = None):
        self.db = db

    @staticmethod
    def calculate_compa_ratio(normalized_salary: float, band_midpoint: float) -> Optional[float]:
        """
        Compa-Ratio = Normalized Salary / Compensation Band Midpoint * 100
        """
        if not band_midpoint or band_midpoint <= 0:
            return None
        return round((normalized_salary / band_midpoint) * 100.0, 2)

    @staticmethod
    def calculate_within_band_position(normalized_salary: float, band_minimum: float, band_maximum: float) -> Optional[float]:
        """
        Within-Band Position = (Normalized Salary - Band Minimum) / (Band Maximum - Band Minimum) * 100
        """
        spread = band_maximum - band_minimum
        if spread <= 0:
            return None
        return round(((normalized_salary - band_minimum) / spread) * 100.0, 2)

    def evaluate_band_status(
        self,
        normalized_salary: float,
        band: Optional[CompensationBand],
        as_of_date: Optional[date] = None,
        record_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validates salary against compensation band:
        - MISSING_BAND: No band configured
        - EXPIRED_BAND: Band effective_to < as_of_date or is_active is False (CASE 1)
        - BELOW_MINIMUM: Normalized salary < min_salary
        - WITHIN_BAND: min_salary <= Normalized salary <= max_salary
        - ABOVE_MAXIMUM: Normalized salary > max_salary
        """
        target_date = as_of_date or date.today()

        if band is None:
            return {
                "status": "MISSING_BAND",
                "compa_ratio": None,
                "within_band_position": None,
                "is_valid_band": False,
                "message": "No valid compensation band found for employee role, level, and location."
            }

        # Case 1: Salary compared with an expired compensation band
        if not band.is_active or band.effective_to < target_date or band.effective_from > target_date:
            message = (
                f"Compensation band {band.id} expired on {band.effective_to} "
                f"(evaluated on {target_date}). Excluded from valid compensation decisions."
            )
            
            if self.db and record_id:
                existing_issue = self.db.query(DataQualityIssue).filter(
                    DataQualityIssue.issue_type == "EXPIRED_BAND",
                    DataQualityIssue.entity_id == record_id,
                    DataQualityIssue.status == "OPEN"
                ).first()
                if not existing_issue:
                    issue = DataQualityIssue(
                        id=f"DQI-EXP-{record_id}",
                        issue_type="EXPIRED_BAND",
                        severity="HIGH",
                        entity_type="CompensationBand",
                        entity_id=record_id,
                        description=message,
                        status="OPEN",
                        ground_truth_label="CASE_1_EXPIRED_BAND"
                    )
                    self.db.add(issue)
                    self.db.commit()

            return {
                "status": "EXPIRED_BAND",
                "compa_ratio": None,
                "within_band_position": None,
                "is_valid_band": False,
                "message": message
            }

        # Active valid band calculations
        compa_ratio = self.calculate_compa_ratio(normalized_salary, band.mid_salary)
        within_band_pos = self.calculate_within_band_position(normalized_salary, band.min_salary, band.max_salary)

        if normalized_salary < band.min_salary:
            status = "BELOW_MINIMUM"
            message = f"Salary ${normalized_salary:,.2f} is below band minimum ${band.min_salary:,.2f} (Compa-Ratio: {compa_ratio}%)."
        elif normalized_salary > band.max_salary:
            status = "ABOVE_MAXIMUM"
            message = f"Salary ${normalized_salary:,.2f} exceeds band maximum ${band.max_salary:,.2f} (Compa-Ratio: {compa_ratio}%)."
        else:
            status = "WITHIN_BAND"
            message = f"Salary is within range [${band.min_salary:,.2f} - ${band.max_salary:,.2f}] (Compa-Ratio: {compa_ratio}%)."

        return {
            "status": status,
            "compa_ratio": compa_ratio,
            "within_band_position": within_band_pos,
            "is_valid_band": True,
            "message": message
        }
