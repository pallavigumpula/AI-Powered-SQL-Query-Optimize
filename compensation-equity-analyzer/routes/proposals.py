"""
Proposals, Approval Management, Data Quality, and Audit Log Routes
"""

from fastapi import APIRouter, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
from typing import Optional
from datetime import date, datetime

from database.db_connection import get_db
from models import (
    AdjustmentProposal, ApprovalHistory, DataQualityIssue, AuditLog, Employee
)
from routes.auth import get_current_user
from services.approval_service import ApprovalService

router = APIRouter(tags=["Workflow"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

# --- PROPOSALS ---
@router.get("/proposals", response_class=HTMLResponse)
def list_proposals(
    request: Request,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    query = db.query(AdjustmentProposal).order_by(AdjustmentProposal.created_at.desc())
    if status_filter:
        query = query.filter(AdjustmentProposal.status == status_filter)

    proposals = query.all()
    employees = db.query(Employee).order_by(Employee.id).limit(100).all()

    return templates.TemplateResponse("proposals.html", {
        "request": request,
        "current_user": current_user,
        "proposals": proposals,
        "employees": employees,
        "status_filter": status_filter or ""
    })

@router.post("/proposals/create")
def create_proposal_action(
    request: Request,
    employee_id: str = Form(...),
    proposed_salary: float = Form(...),
    reason: str = Form(...),
    supporting_evidence: str = Form(...),
    priority: str = Form("Medium"),
    db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    service = ApprovalService(db)

    service.create_proposal(
        employee_id=employee_id,
        proposed_salary=proposed_salary,
        reason=reason,
        supporting_evidence=supporting_evidence,
        actor_id=current_user.email,
        actor_role=current_user.role,
        priority=priority,
        effective_date=date.today()
    )
    return RedirectResponse(url="/proposals", status_code=status.HTTP_302_FOUND)

# --- APPROVAL MANAGEMENT ---
@router.get("/approvals", response_class=HTMLResponse)
def approvals_management_view(
    request: Request,
    db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    # Pending reviews
    pending_manager = db.query(AdjustmentProposal).filter(AdjustmentProposal.status == "Pending Manager Review").all()
    pending_hr = db.query(AdjustmentProposal).filter(AdjustmentProposal.status == "Pending HR Review").all()
    approved = db.query(AdjustmentProposal).filter(AdjustmentProposal.status == "Approved").all()
    completed = db.query(AdjustmentProposal).filter(AdjustmentProposal.status.in_(["Implemented", "Rejected"])).limit(20).all()

    return templates.TemplateResponse("approvals.html", {
        "request": request,
        "current_user": current_user,
        "pending_manager": pending_manager,
        "pending_hr": pending_hr,
        "approved": approved,
        "completed": completed
    })

@router.post("/approvals/action")
def proposal_action(
    request: Request,
    proposal_id: str = Form(...),
    action: str = Form(...), # APPROVE, REJECT, REQUEST_INFO, SUBMIT_HR, IMPLEMENT
    comments: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    service = ApprovalService(db)

    if action == "SUBMIT_HR":
        service.transition_status(proposal_id, "Pending HR Review", current_user.email, current_user.role, comments)
    elif action == "APPROVE":
        service.transition_status(proposal_id, "Approved", current_user.email, current_user.role, comments)
    elif action == "REJECT":
        service.transition_status(proposal_id, "Rejected", current_user.email, current_user.role, comments)
    elif action == "REQUEST_INFO":
        service.transition_status(proposal_id, "On Hold", current_user.email, current_user.role, comments)
    elif action == "IMPLEMENT":
        service.implement_adjustment(proposal_id, current_user.email, current_user.role)

    return RedirectResponse(url="/approvals", status_code=status.HTTP_302_FOUND)

# --- DATA QUALITY ISSUES ---
@router.get("/data-quality", response_class=HTMLResponse)
def data_quality_view(
    request: Request,
    issue_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    query = db.query(DataQualityIssue).order_by(DataQualityIssue.created_at.desc())

    if issue_type:
        query = query.filter(DataQualityIssue.issue_type == issue_type)
    if status_filter:
        query = query.filter(DataQualityIssue.status == status_filter)

    issues = query.all()

    return templates.TemplateResponse("data_quality.html", {
        "request": request,
        "current_user": current_user,
        "issues": issues,
        "issue_type": issue_type or "",
        "status_filter": status_filter or ""
    })

@router.post("/data-quality/resolve")
def resolve_issue(
    request: Request,
    issue_id: str = Form(...),
    resolution_notes: str = Form(...),
    db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    issue = db.query(DataQualityIssue).filter(DataQualityIssue.id == issue_id).first()
    if issue:
        issue.status = "RESOLVED"
        issue.resolved_at = datetime.utcnow()
        issue.resolution_notes = f"Resolved by {current_user.email}: {resolution_notes}"
        db.commit()
    return RedirectResponse(url="/data-quality", status_code=status.HTTP_302_FOUND)

# --- AUDIT LOGS ---
@router.get("/audit-logs", response_class=HTMLResponse)
def audit_logs_view(
    request: Request,
    severity: Optional[str] = None,
    entity_name: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    query = db.query(AuditLog).order_by(AuditLog.created_at.desc())

    if severity:
        query = query.filter(AuditLog.severity == severity)
    if entity_name:
        query = query.filter(AuditLog.entity_name == entity_name)

    total_count = query.count()
    logs = query.offset((page - 1) * page_size).limit(page_size).all()
    total_pages = max(1, (total_count + page_size - 1) // page_size)

    return templates.TemplateResponse("audit_logs.html", {
        "request": request,
        "current_user": current_user,
        "logs": logs,
        "total_count": total_count,
        "page": page,
        "total_pages": total_pages,
        "severity": severity or "",
        "entity_name": entity_name or ""
    })
