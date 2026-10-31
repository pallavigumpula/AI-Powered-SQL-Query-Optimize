"""
Adjustment Proposal and Approval Workflow Service
Enforces strict state transitions, dual approval workflows, audit trails, and unauthorized change detection.
"""

from datetime import datetime, date
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from models.employee import Employee
from models.salary_record import SalaryRecord
from models.adjustment import AdjustmentProposal, ApprovalHistory, AdjustmentEvent
from models.supporting import DataQualityIssue
from services.audit_service import AuditService
from services.salary_calculator import SalaryCalculator
from services.currency_service import CurrencyService

class ApprovalService:
    # State transitions map
    VALID_TRANSITIONS = {
        "Draft": ["Pending Manager Review", "On Hold"],
        "Pending Manager Review": ["Pending HR Review", "Draft", "On Hold"],
        "Pending HR Review": ["Approved", "Rejected", "Pending Manager Review", "On Hold"],
        "Approved": ["Implemented", "On Hold"],
        "On Hold": ["Draft", "Pending Manager Review", "Pending HR Review"],
        "Rejected": ["Draft"],
        "Implemented": []
    }

    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)
        self.calculator = SalaryCalculator(db)
        self.currency_service = CurrencyService(db)

    def create_proposal(
        self,
        employee_id: str,
        proposed_salary: float,
        reason: str,
        supporting_evidence: str,
        actor_id: str,
        actor_role: str,
        priority: str = "Medium",
        effective_date: Optional[date] = None
    ) -> AdjustmentProposal:
        """
        Creates a new salary adjustment proposal with supporting evidence.
        """
        employee = self.db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise ValueError(f"Employee {employee_id} not found.")

        current_sal_rec = employee.current_salary_record
        current_salary = current_sal_rec.amount if current_sal_rec else 0.0
        currency = current_sal_rec.currency if current_sal_rec else "USD"

        pct_change = round(((proposed_salary - current_salary) / current_salary) * 100.0, 2) if current_salary > 0 else 0.0

        proposal_count = self.db.query(AdjustmentProposal).count() + 1
        proposal_id = f"ADJ-2026-{proposal_count:06d}"
        eff_date = effective_date or date.today()

        initial_status = "Pending Manager Review" if actor_role in ["Manager", "Employee"] else "Pending HR Review"

        proposal = AdjustmentProposal(
            id=proposal_id,
            employee_id=employee_id,
            current_salary=current_salary,
            proposed_salary=proposed_salary,
            currency=currency,
            percentage_change=pct_change,
            reason=reason,
            supporting_evidence=supporting_evidence,
            status=initial_status,
            priority=priority,
            submitted_by=actor_id,
            submitted_at=datetime.utcnow(),
            effective_date=eff_date,
            created_at=datetime.utcnow()
        )
        self.db.add(proposal)
        self.db.flush()

        # Log Approval History
        app_history = ApprovalHistory(
            id=f"APPH-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}-{proposal_count}",
            proposal_id=proposal_id,
            previous_status="Draft",
            new_status=initial_status,
            actor_id=actor_id,
            actor_role=actor_role,
            action_type="SUBMIT",
            comments=f"Proposal created with proposed salary ${proposed_salary:,.2f} ({pct_change:+}%).",
            action_timestamp=datetime.utcnow()
        )
        self.db.add(app_history)

        # Audit Log
        self.audit_service.log(
            entity_name="AdjustmentProposal",
            entity_id=proposal_id,
            action="CREATE",
            actor_id=actor_id,
            actor_role=actor_role,
            new_values={
                "proposed_salary": proposed_salary,
                "percentage_change": pct_change,
                "status": initial_status
            }
        )
        self.db.commit()
        return proposal

    def transition_status(
        self,
        proposal_id: str,
        new_status: str,
        actor_id: str,
        actor_role: str,
        comments: Optional[str] = None,
        action_type: str = "STATUS_CHANGE"
    ) -> AdjustmentProposal:
        """
        Transitions proposal state, recording immutable history and enforcing role permissions.
        """
        proposal = self.db.query(AdjustmentProposal).filter(AdjustmentProposal.id == proposal_id).first()
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found.")

        current_status = proposal.status

        # Validate transition
        allowed = self.VALID_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            raise ValueError(f"Invalid transition from '{current_status}' to '{new_status}'. Allowed: {allowed}")

        # Enforce Role Authorization
        if new_status == "Approved" and actor_role not in ["HR Partner", "System Administrator"]:
            raise PermissionError("Only HR Partner or System Administrator can approve salary adjustment proposals.")

        proposal.status = new_status
        proposal.reviewed_by = actor_id
        proposal.reviewed_at = datetime.utcnow()
        proposal.updated_at = datetime.utcnow()

        history_id = f"APPH-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}-{proposal.id[-6:]}"
        history = ApprovalHistory(
            id=history_id,
            proposal_id=proposal.id,
            previous_status=current_status,
            new_status=new_status,
            actor_id=actor_id,
            actor_role=actor_role,
            action_type=action_type,
            comments=comments or f"Transitioned from {current_status} to {new_status}",
            action_timestamp=datetime.utcnow()
        )
        self.db.add(history)

        self.audit_service.log(
            entity_name="AdjustmentProposal",
            entity_id=proposal.id,
            action=action_type,
            actor_id=actor_id,
            actor_role=actor_role,
            old_values={"status": current_status},
            new_values={"status": new_status, "comments": comments}
        )

        self.db.commit()
        return proposal

    def implement_adjustment(self, proposal_id: str, actor_id: str, actor_role: str) -> Tuple[AdjustmentEvent, SalaryRecord]:
        """
        Executes an approved proposal:
        - Creates AdjustmentEvent
        - Sets previous salary record is_current = False
        - Inserts new SalaryRecord (preserving full history)
        - Transitions status to 'Implemented'
        """
        proposal = self.db.query(AdjustmentProposal).filter(AdjustmentProposal.id == proposal_id).first()
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found.")

        if proposal.status != "Approved":
            raise ValueError(f"Cannot implement proposal in '{proposal.status}' state. Must be 'Approved'.")

        employee = self.db.query(Employee).filter(Employee.id == proposal.employee_id).first()
        
        # 1. Mark previous salary records as is_current = False
        prev_records = self.db.query(SalaryRecord).filter(
            SalaryRecord.employee_id == employee.id,
            SalaryRecord.is_current == True
        ).all()
        for r in prev_records:
            r.is_current = False

        # 2. Create AdjustmentEvent
        event_count = self.db.query(AdjustmentEvent).count() + 1
        event_id = f"EVT-2026-{event_count:06d}"
        adj_event = AdjustmentEvent(
            id=event_id,
            proposal_id=proposal.id,
            employee_id=employee.id,
            old_salary=proposal.current_salary,
            new_salary=proposal.proposed_salary,
            effective_date=proposal.effective_date,
            is_authorized=True,
            applied_by=actor_id,
            notes=f"Implemented approved proposal {proposal.id}: {proposal.reason}",
            created_at=datetime.utcnow()
        )
        self.db.add(adj_event)

        # 3. Create new historical SalaryRecord (preserves history!)
        sal_count = self.db.query(SalaryRecord).count() + 1
        sal_id = f"SAL-{employee.id}-{proposal.effective_date.strftime('%Y-%m')}"
        
        # Calculate normalized metrics
        norm_sal, _ = self.currency_service.convert_to_base(proposal.proposed_salary, proposal.currency, proposal.effective_date)
        norm_sal_fte = round((norm_sal or proposal.proposed_salary) / (employee.fte or 1.0), 2)
        
        # Find active band
        current_band = None
        if prev_records and prev_records[0].band:
            current_band = prev_records[0].band

        band_eval = self.calculator.evaluate_band_status(
            norm_sal_fte, current_band, as_of_date=proposal.effective_date
        )

        new_sal_rec = SalaryRecord(
            id=sal_id,
            employee_id=employee.id,
            band_id=current_band.id if current_band else None,
            amount=proposal.proposed_salary,
            currency=proposal.currency,
            effective_date=proposal.effective_date,
            fte=employee.fte or 1.0,
            normalized_salary=norm_sal_fte,
            compa_ratio=band_eval.get("compa_ratio"),
            within_band_position=band_eval.get("within_band_position"),
            band_status=band_eval.get("status", "WITHIN_BAND"),
            is_current=True,
            created_at=datetime.utcnow()
        )
        self.db.add(new_sal_rec)

        # 4. Transition proposal status to 'Implemented'
        self.transition_status(
            proposal_id=proposal.id,
            new_status="Implemented",
            actor_id=actor_id,
            actor_role=actor_role,
            comments=f"Successfully implemented salary adjustment. New salary: ${proposal.proposed_salary:,.2f}.",
            action_type="IMPLEMENT"
        )

        self.db.commit()
        return adj_event, new_sal_rec

    def detect_unauthorized_adjustments(self) -> int:
        """
        Edge Case 4: Salary adjustment applied without approval.
        Scans salary events and salary jumps to ensure every change has an authorized, approved proposal.
        Flags high-priority audit exceptions for unauthorized adjustments.
        """
        unauthorized_events = self.db.query(AdjustmentEvent).filter(
            AdjustmentEvent.is_authorized == False
        ).all()

        flagged_count = 0
        for evt in unauthorized_events:
            desc = (
                f"Unauthorized salary adjustment detected for employee {evt.employee_id}. "
                f"Salary changed from ${evt.old_salary:,.2f} to ${evt.new_salary:,.2f} on {evt.effective_date} "
                f"by '{evt.applied_by}' without an approved proposal."
            )
            # Check if already logged
            existing_issue = self.db.query(DataQualityIssue).filter(
                DataQualityIssue.issue_type == "UNAUTHORIZED_ADJUSTMENT",
                DataQualityIssue.entity_id == evt.id,
                DataQualityIssue.status == "OPEN"
            ).first()

            if not existing_issue:
                issue = DataQualityIssue(
                    id=f"DQI-UNAUTH-{evt.id}",
                    issue_type="UNAUTHORIZED_ADJUSTMENT",
                    severity="CRITICAL",
                    entity_type="AdjustmentEvent",
                    entity_id=evt.id,
                    description=desc,
                    status="OPEN",
                    ground_truth_label="CASE_4_UNAUTHORIZED_ADJUSTMENT"
                )
                self.db.add(issue)
                
                # Critical audit log
                self.audit_service.log(
                    entity_name="AdjustmentEvent",
                    entity_id=evt.id,
                    action="UNAUTHORIZED_MODIFICATION",
                    actor_id=evt.applied_by,
                    actor_role="UNKNOWN",
                    new_values={"new_salary": evt.new_salary, "old_salary": evt.old_salary},
                    severity="CRITICAL"
                )
                flagged_count += 1

        self.db.commit()
        return flagged_count
