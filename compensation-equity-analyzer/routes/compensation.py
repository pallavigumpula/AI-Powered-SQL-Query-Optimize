"""
Compensation Bands, Salary History, and Peer Cohort Comparison Routes
"""

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from pathlib import Path
from typing import Optional

from database.db_connection import get_db
from models import (
    CompensationBand, SalaryRecord, Role, Level, Location, Employee
)
from routes.auth import get_current_user
from services.comparison_service import ComparisonService
from services.disparity_detector import DisparityDetector

router = APIRouter(tags=["Compensation"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

@router.get("/compensation-bands", response_class=HTMLResponse)
def list_compensation_bands(
    request: Request,
    role_id: Optional[str] = Query(None),
    level_id: Optional[str] = Query(None),
    location_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=10, le=100),
    db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    query = db.query(CompensationBand)

    if role_id:
        query = query.filter(CompensationBand.role_id == role_id)
    if level_id:
        query = query.filter(CompensationBand.level_id == level_id)
    if location_id:
        query = query.filter(CompensationBand.location_id == location_id)
    if is_active is not None:
        query = query.filter(CompensationBand.is_active == is_active)

    total_count = query.count()
    bands = query.order_by(CompensationBand.id).offset((page - 1) * page_size).limit(page_size).all()

    roles = db.query(Role).order_by(Role.name).all()
    levels = db.query(Level).order_by(Level.hierarchy_order).all()
    locations = db.query(Location).order_by(Location.city).all()

    total_pages = max(1, (total_count + page_size - 1) // page_size)

    return templates.TemplateResponse("compensation.html", {
        "request": request,
        "current_user": current_user,
        "bands": bands,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "roles": roles,
        "levels": levels,
        "locations": locations,
        "filters": {
            "role_id": role_id or "",
            "level_id": level_id or "",
            "location_id": location_id or "",
            "is_active": str(is_active) if is_active is not None else ""
        }
    })

@router.get("/salary-history", response_class=HTMLResponse)
def salary_history_view(
    request: Request,
    emp_id: Optional[str] = Query(None),
    currency: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=100),
    db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    query = db.query(SalaryRecord).join(Employee)

    if emp_id:
        query = query.filter(SalaryRecord.employee_id.ilike(f"%{emp_id.strip()}%"))
    if currency:
        query = query.filter(SalaryRecord.currency == currency)

    total_count = query.count()
    records = query.order_by(SalaryRecord.effective_date.desc(), SalaryRecord.employee_id)\
                   .offset((page - 1) * page_size).limit(page_size).all()

    total_pages = max(1, (total_count + page_size - 1) // page_size)

    return templates.TemplateResponse("salary_history.html", {
        "request": request,
        "current_user": current_user,
        "records": records,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "emp_id": emp_id or "",
        "currency": currency or ""
    })

@router.get("/salary-comparison", response_class=HTMLResponse)
def salary_comparison_view(
    request: Request,
    emp_id: Optional[str] = Query("EMP-000001"),
    db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    target_emp = db.query(Employee).filter(Employee.id == emp_id).first()
    if not target_emp:
        target_emp = db.query(Employee).first()

    comparison_service = ComparisonService(db)
    detector = DisparityDetector(db)

    peers = comparison_service.get_peer_cohort(target_emp) if target_emp else []
    analysis = detector.analyze_employee(target_emp) if target_emp else {}

    # Extract peer metrics
    peer_data = []
    for p in peers:
        sal = p.current_salary_record
        if sal:
            peer_data.append({
                "id": p.id,
                "name": p.full_name,
                "role": p.role.name if p.role else "",
                "level": p.level.code if p.level else "",
                "location": p.location.city if p.location else "",
                "fte": p.fte,
                "normalized_salary": sal.normalized_salary,
                "performance_rating": p.performance_records[0].rating if p.performance_records else 3.0,
                "tenure_years": p.tenure_record.company_tenure_years if p.tenure_record else 1.0,
            })

    all_employees = db.query(Employee).order_by(Employee.id).limit(100).all()

    return templates.TemplateResponse("comparison.html", {
        "request": request,
        "current_user": current_user,
        "target_emp": target_emp,
        "analysis": analysis,
        "peers": peer_data,
        "all_employees": all_employees
    })
