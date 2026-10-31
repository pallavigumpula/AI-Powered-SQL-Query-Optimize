"""
Employees and Detailed Profile Routes
Search, filters, peer context, full compensation breakdown, and tenure timelines.
"""

from fastapi import APIRouter, Depends, Request, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pathlib import Path
from typing import Optional

from database.db_connection import get_db
from models import (
    Employee, Role, Level, Location, SalaryRecord, PerformanceEvidence,
    Promotion, AdjustmentProposal, DataQualityIssue, CompensationBand
)
from routes.auth import get_current_user
from services.disparity_detector import DisparityDetector

router = APIRouter(prefix="/employees", tags=["Employees"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

@router.get("", response_class=HTMLResponse)
def list_employees(
    request: Request,
    q: Optional[str] = Query(None, description="Search by name, email, or ID"),
    role_id: Optional[str] = Query(None),
    level_id: Optional[str] = Query(None),
    location_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    fte: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=10, le=100),
    db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    query = db.query(Employee)

    # Search filter
    if q:
        search = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Employee.id.ilike(search),
                Employee.first_name.ilike(search),
                Employee.last_name.ilike(search),
                Employee.email.ilike(search)
            )
        )
    if role_id:
        query = query.filter(Employee.role_id == role_id)
    if level_id:
        query = query.filter(Employee.level_id == level_id)
    if location_id:
        query = query.filter(Employee.location_id == location_id)
    if status:
        query = query.filter(Employee.status == status)
    if fte is not None:
        query = query.filter(Employee.fte == fte)

    total_count = query.count()
    employees = query.order_by(Employee.id).offset((page - 1) * page_size).limit(page_size).all()

    roles = db.query(Role).order_by(Role.name).all()
    levels = db.query(Level).order_by(Level.hierarchy_order).all()
    locations = db.query(Location).order_by(Location.city).all()

    total_pages = max(1, (total_count + page_size - 1) // page_size)

    return templates.TemplateResponse("employees.html", {
        "request": request,
        "current_user": current_user,
        "employees": employees,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "roles": roles,
        "levels": levels,
        "locations": locations,
        "filters": {
            "q": q or "",
            "role_id": role_id or "",
            "level_id": level_id or "",
            "location_id": location_id or "",
            "status": status or "",
            "fte": fte if fte is not None else ""
        }
    })

@router.get("/{emp_id}", response_class=HTMLResponse)
def employee_details(
    emp_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    employee = db.query(Employee).filter(Employee.id == emp_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail=f"Employee {emp_id} not found.")

    # Disparity analysis for this employee
    detector = DisparityDetector(db)
    analysis = detector.analyze_employee(employee)

    # Historical salary records
    salary_history = db.query(SalaryRecord).filter(
        SalaryRecord.employee_id == emp_id
    ).order_by(SalaryRecord.effective_date.desc()).all()

    # Performance reviews
    perf_records = db.query(PerformanceEvidence).filter(
        PerformanceEvidence.employee_id == emp_id
    ).order_by(PerformanceEvidence.review_date.desc()).all()

    # Promotions
    promotions = db.query(Promotion).filter(
        Promotion.employee_id == emp_id
    ).order_by(Promotion.effective_date.desc()).all()

    # Proposals
    proposals = db.query(AdjustmentProposal).filter(
        AdjustmentProposal.employee_id == emp_id
    ).order_by(AdjustmentProposal.created_at.desc()).all()

    # Exceptions
    exceptions = db.query(DataQualityIssue).filter(
        DataQualityIssue.entity_id.in_([s.id for s in salary_history] + [emp_id])
    ).all()

    # Active compensation band
    current_sal = employee.current_salary_record
    active_band = current_sal.band if current_sal else None

    return templates.TemplateResponse("employee_details.html", {
        "request": request,
        "current_user": current_user,
        "employee": employee,
        "analysis": analysis,
        "current_salary": current_sal,
        "active_band": active_band,
        "salary_history": salary_history,
        "performance_records": perf_records,
        "promotions": promotions,
        "proposals": proposals,
        "exceptions": exceptions
    })
