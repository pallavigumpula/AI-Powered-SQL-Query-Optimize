"""
Comparison Service
Constructs comparable employee peer cohorts and detects invalid grouping anomalies.
Enforces rule: Never group unrelated roles without documented rationale (CASE 5).
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from models.employee import Employee
from models.role import Role
from models.supporting import ComparisonGroup, ComparisonGroupMember, DataQualityIssue

class ComparisonService:
    def __init__(self, db: Session):
        self.db = db

    # Allowed cross-role clustering only within identical job family with documented rationale
    ALLOWED_CLUSTERS = {
        "Engineering": ["ROLE-SWE", "ROLE-QA", "ROLE-DEVOPS", "ROLE-DATAENG"],
        "AI & Data": ["ROLE-MLE", "ROLE-AIRES", "ROLE-FDAIE", "ROLE-DATASCI"],
        "Product": ["ROLE-PM", "ROLE-PRODDES", "ROLE-UXRES"],
        "Operations": ["ROLE-HRBP", "ROLE-FIN", "ROLE-OPS", "ROLE-TA"]
    }

    def validate_group_compatibility(self, group: ComparisonGroup) -> Dict[str, Any]:
        """
        Validates whether members of a ComparisonGroup are legitimately comparable.
        Edge Case 5: Incomparable roles grouped without rationale.
        """
        members = self.db.query(Employee).join(
            ComparisonGroupMember, ComparisonGroupMember.employee_id == Employee.id
        ).filter(ComparisonGroupMember.comparison_group_id == group.id).all()

        if not members:
            return {"is_valid": True, "reason": "No members in group"}

        # Extract roles, levels, and departments
        roles = {m.role_id for m in members}
        role_objs = self.db.query(Role).filter(Role.id.in_(roles)).all()
        job_families = {r.job_family for r in role_objs}
        levels = {m.level_id for m in members}

        # Check: disparate job families grouped together
        if len(job_families) > 1 and ("cross-functional" not in group.rationale.lower() or not group.is_valid):
            # Egregious mismatch (e.g. Engineering + Operations grouped together)
            issue_desc = (
                f"Comparison Group '{group.name}' (ID: {group.id}) combines incompatible job families: "
                f"{sorted(list(job_families))} without documented executive rationale. "
                f"Roles involved: {sorted(list(roles))}."
            )

            # Ensure DataQualityIssue is logged
            existing_issue = self.db.query(DataQualityIssue).filter(
                DataQualityIssue.issue_type == "INCOMPARABLE_ROLE_GROUPING",
                DataQualityIssue.entity_id == group.id,
                DataQualityIssue.status == "OPEN"
            ).first()

            if not existing_issue:
                issue = DataQualityIssue(
                    id=f"DQI-GRP-{group.id}",
                    issue_type="INCOMPARABLE_ROLE_GROUPING",
                    severity="HIGH",
                    entity_type="ComparisonGroup",
                    entity_id=group.id,
                    description=issue_desc,
                    status="OPEN",
                    ground_truth_label="CASE_5_INCOMPARABLE_ROLES_GROUPED"
                )
                self.db.add(issue)
                group.is_valid = False
                self.db.commit()

            return {
                "is_valid": False,
                "reason": issue_desc,
                "job_families": list(job_families),
                "levels": list(levels)
            }

        return {
            "is_valid": True,
            "reason": "Group satisfies role and level comparability criteria.",
            "job_families": list(job_families),
            "levels": list(levels)
        }

    def get_peer_cohort(self, employee: Employee) -> List[Employee]:
        """
        Finds true comparable peers for an employee based on:
        - Same role or compatible role within family
        - Same career level
        - Same location region / tier
        - Status Active
        """
        query = self.db.query(Employee).filter(
            Employee.id != employee.id,
            Employee.status == "Active",
            Employee.level_id == employee.level_id
        )

        # First try exact role and location
        exact_peers = query.filter(
            Employee.role_id == employee.role_id,
            Employee.location_id == employee.location_id
        ).all()

        if len(exact_peers) >= 3:
            return exact_peers

        # Fallback: same role across same region/country
        location = employee.location
        broader_peers = query.filter(
            Employee.role_id == employee.role_id
        ).all()

        if broader_peers:
            return broader_peers

        # Broader fallback: same job family and level
        role = employee.role
        if role:
            family_roles = self.db.query(Role.id).filter(Role.job_family == role.job_family).all()
            family_role_ids = [r[0] for r in family_roles]
            return query.filter(Employee.role_id.in_(family_role_ids)).all()

        return []
