"""
Synthetic Edge Cases Injector
Injects and clearly labels the 5 mandatory edge cases into the dataset.
Generates corresponding DataQualityIssues and tracking metadata.
"""

from datetime import date, datetime
from typing import List, Dict, Any, Tuple

def inject_edge_cases(
    employees: List[Dict[str, Any]],
    salary_records: List[Dict[str, Any]],
    bands: List[Dict[str, Any]],
    groups: List[Dict[str, Any]],
    group_members: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Injects the 5 mandatory edge cases into the generated baseline.
    Returns:
        (modified_salary_records, adjustment_events, data_quality_issues)
    """
    data_quality_issues = []
    adjustment_events = []

    # CASE 1: Salary compared with an expired compensation band
    # Find expired band
    expired_band = next((b for b in bands if not b["is_active"]), None)
    if expired_band and len(employees) > 1:
        emp_case1 = employees[1] # EMP-000002
        # Modify their latest salary record
        latest_sal = next(
            (s for s in reversed(salary_records) if s["employee_id"] == emp_case1["id"] and s["is_current"]),
            None
        )
        if latest_sal:
            latest_sal["band_id"] = expired_band["id"]
            latest_sal["band_status"] = "EXPIRED_BAND"
            latest_sal["compa_ratio"] = None
            latest_sal["within_band_position"] = None
            
            data_quality_issues.append({
                "id": f"DQI-EXP-{latest_sal['id']}",
                "issue_type": "EXPIRED_BAND",
                "severity": "HIGH",
                "entity_type": "SalaryRecord",
                "entity_id": latest_sal["id"],
                "description": f"Salary for employee {emp_case1['id']} is tied to expired band {expired_band['id']} (expired on {expired_band['effective_to']}). Excluded from valid compensation decisions.",
                "status": "OPEN",
                "ground_truth_label": "CASE_1_EXPIRED_BAND",
                "created_at": datetime.utcnow()
            })

    # CASE 2: FTE ignored (Part-time employee compared raw instead of FTE-normalized)
    part_time_emp = next((e for e in employees if e["fte"] == 0.5), None)
    if part_time_emp:
        latest_sal = next(
            (s for s in reversed(salary_records) if s["employee_id"] == part_time_emp["id"] and s["is_current"]),
            None
        )
        if latest_sal:
            data_quality_issues.append({
                "id": f"DQI-FTE-{latest_sal['id']}",
                "issue_type": "FTE_IGNORED",
                "severity": "HIGH",
                "entity_type": "SalaryRecord",
                "entity_id": latest_sal["id"],
                "description": f"Part-time employee {part_time_emp['id']} (FTE=0.5, nominal salary ${latest_sal['amount']:,.2f}) was flagged in raw salary comparison. System must normalize to full-time equivalent (${latest_sal['normalized_salary']:,.2f}).",
                "status": "OPEN",
                "ground_truth_label": "CASE_2_FTE_IGNORED",
                "created_at": datetime.utcnow()
            })

    # CASE 3: Missing currency conversion
    if len(employees) > 3:
        emp_case3 = employees[3] # EMP-000004
        emp_case3["currency"] = "CHF" # Swiss Franc without exchange rate record
        latest_sal = next(
            (s for s in reversed(salary_records) if s["employee_id"] == emp_case3["id"] and s["is_current"]),
            None
        )
        if latest_sal:
            latest_sal["currency"] = "CHF"
            latest_sal["normalized_salary"] = None
            latest_sal["compa_ratio"] = None
            latest_sal["within_band_position"] = None
            
            data_quality_issues.append({
                "id": f"DQI-FX-{latest_sal['id']}",
                "issue_type": "MISSING_EXCHANGE_RATE",
                "severity": "CRITICAL",
                "entity_type": "SalaryRecord",
                "entity_id": latest_sal["id"],
                "description": f"Missing FX exchange rate for currency 'CHF' to 'USD' for employee {emp_case3['id']}. Cannot compute reliable peer comparison.",
                "status": "OPEN",
                "ground_truth_label": "CASE_3_MISSING_CURRENCY_CONVERSION",
                "created_at": datetime.utcnow()
            })

    # CASE 4: Salary adjustment applied without approval
    if len(employees) > 5:
        emp_case4 = employees[5] # EMP-000006
        unauth_event_id = "EVT-UNAUTH-2026-0001"
        unauth_event = {
            "id": unauth_event_id,
            "proposal_id": None, # Missing approved proposal
            "employee_id": emp_case4["id"],
            "old_salary": 125000.0,
            "new_salary": 165000.0,
            "effective_date": date(2026, 8, 1),
            "is_authorized": False,
            "applied_by": "unknown_actor@direct_db_insert",
            "notes": "Emergency salary hike direct database update without HR proposal approval",
            "created_at": datetime.utcnow()
        }
        adjustment_events.append(unauth_event)

        data_quality_issues.append({
            "id": f"DQI-UNAUTH-{unauth_event_id}",
            "issue_type": "UNAUTHORIZED_ADJUSTMENT",
            "severity": "CRITICAL",
            "entity_type": "AdjustmentEvent",
            "entity_id": unauth_event_id,
            "description": f"Unauthorized salary modification detected for employee {emp_case4['id']} (+$40,000.00). No approved AdjustmentProposal found in audit ledger.",
            "status": "OPEN",
            "ground_truth_label": "CASE_4_UNAUTHORIZED_ADJUSTMENT",
            "created_at": datetime.utcnow()
        })

    # CASE 5: Incomparable roles grouped without rationale
    incomparable_group_id = "GRP-INCOMPATIBLE-001"
    groups.append({
        "id": incomparable_group_id,
        "name": "Cross-Department Mismatched Cohort",
        "role_id": None,
        "level_id": "LVL-L3",
        "location_id": "LOC-US-NYC",
        "rationale": "Arbitrary grouping created during ad-hoc department restructuring without job architecture justification.",
        "is_valid": False,
        "created_at": datetime.utcnow()
    })

    if len(employees) >= 8:
        # Group together a Senior AI Engineer with a Junior Talent Acquisition Specialist
        emp_ai = next((e for e in employees if e["role_id"] in ["ROLE-MLE", "ROLE-FDAIE"]), employees[0])
        emp_ta = next((e for e in employees if e["role_id"] in ["ROLE-TA", "ROLE-HRBP"]), employees[7])
        
        group_members.append({"comparison_group_id": incomparable_group_id, "employee_id": emp_ai["id"], "joined_date": date(2026, 1, 15)})
        group_members.append({"comparison_group_id": incomparable_group_id, "employee_id": emp_ta["id"], "joined_date": date(2026, 1, 15)})

        data_quality_issues.append({
            "id": f"DQI-GRP-{incomparable_group_id}",
            "issue_type": "INCOMPARABLE_ROLE_GROUPING",
            "severity": "HIGH",
            "entity_type": "ComparisonGroup",
            "entity_id": incomparable_group_id,
            "description": f"Comparison group '{incomparable_group_id}' clusters incompatible roles ({emp_ai['role_id']} vs {emp_ta['role_id']}) across different job families without job architecture rationale.",
            "status": "OPEN",
            "ground_truth_label": "CASE_5_INCOMPARABLE_ROLES_GROUPED",
            "created_at": datetime.utcnow()
        })

    return salary_records, adjustment_events, data_quality_issues
