"""
Unit and Workflow Tests for Proposal and Approval Lifecycle
"""

import pytest
from datetime import date
from database.db_connection import SessionLocal
from models import Employee, AdjustmentProposal, ApprovalHistory, SalaryRecord
from services.approval_service import ApprovalService

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_proposal_lifecycle(db):
    service = ApprovalService(db)
    emp = db.query(Employee).first()
    assert emp is not None

    # 1. Create proposal
    proposal = service.create_proposal(
        employee_id=emp.id,
        proposed_salary=175000.0,
        reason="Market Equity Adjustment",
        supporting_evidence="High performer with 4.5 rating; pay below peer median.",
        actor_id="manager@yottaflex.ai",
        actor_role="Manager",
        priority="High",
        effective_date=date(2026, 11, 1)
    )
    assert proposal.id.startswith("ADJ-2026-")
    assert proposal.status in ["Pending Manager Review", "Pending HR Review"]

    # 2. Manager submit comments -> Pending HR Review
    if proposal.status == "Pending Manager Review":
        proposal = service.transition_status(
            proposal_id=proposal.id,
            new_status="Pending HR Review",
            actor_id="manager@yottaflex.ai",
            actor_role="Manager",
            comments="I strongly endorse this adjustment."
        )
    assert proposal.status == "Pending HR Review"

    # 3. Unauthorized approval attempt by Employee should fail
    with pytest.raises(PermissionError):
        service.transition_status(
            proposal_id=proposal.id,
            new_status="Approved",
            actor_id="employee@yottaflex.ai",
            actor_role="Employee"
        )

    # 4. HR Partner approves
    proposal = service.transition_status(
        proposal_id=proposal.id,
        new_status="Approved",
        actor_id="hr@yottaflex.ai",
        actor_role="HR Partner",
        comments="Approved following compensation committee review."
    )
    assert proposal.status == "Approved"

    # 5. Implementation creates event and appends new historical salary record
    old_sal_count = db.query(SalaryRecord).filter(SalaryRecord.employee_id == emp.id).count()
    event, new_record = service.implement_adjustment(
        proposal_id=proposal.id,
        actor_id="admin@yottaflex.ai",
        actor_role="System Administrator"
    )

    assert proposal.status == "Implemented"
    assert event.is_authorized is True
    assert new_record.is_current is True
    assert new_record.amount == 175000.0
    
    # History preserved: previous count + 1
    new_sal_count = db.query(SalaryRecord).filter(SalaryRecord.employee_id == emp.id).count()
    assert new_sal_count == old_sal_count + 1
