"""
Disparity Detection and Advanced Equity Analysis Routes
Interactive filtering, statistical breakdowns, anomaly review triggers, and deep investigation views.
"""

from fastapi import APIRouter, Depends, Request, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path
from typing import Optional, List

from database.db_connection import get_db
from models import Employee, Role, Level, Location, DataQualityIssue
from routes.auth import get_current_user
from services.disparity_detector import DisparityDetector

router = APIRouter(tags=["Analysis"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

@router.get("/disparity-detection", response_class=HTMLResponse)
@router.get("/analysis", response_class=HTMLResponse)
def disparity_analysis_view(
    request: Request,
    role_id: Optional[str] = Query(None),
    level_id: Optional[str] = Query(None),
    location_id: Optional[str] = Query(None),
    min_pct_diff: Optional[float] = Query(None),
    performance_rating: Optional[int] = Query(None),
    only_anomalies: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=10, le=100),
    db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    detector = DisparityDetector(db)

    # Use high-performance vectorized batch detection
    all_disparities = detector.detect_all_disparities(limit=250)

    # Apply filters in-memory
    disparities = []
    for d in all_disparities:
        if role_id and d.get("role_id") != role_id and role_id not in d.get("role", ""):
            continue
        if level_id and d.get("level") != level_id:
            continue
        if location_id and d.get("location") != location_id:
            continue
        if min_pct_diff is not None and abs(d.get("percentage_difference", 0)) < min_pct_diff:
            continue
        if performance_rating is not None and d.get("performance_rating") != performance_rating:
            continue

        disparities.append(d)

    # Sort by absolute percentage difference descending
    disparities.sort(key=lambda x: abs(x.get("percentage_difference", 0)), reverse=True)

    total_count = len(disparities)
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    paginated_results = disparities[(page - 1) * page_size: page * page_size]

    roles = db.query(Role).order_by(Role.name).all()
    levels = db.query(Level).order_by(Level.hierarchy_order).all()
    locations = db.query(Location).order_by(Location.city).all()

    return templates.TemplateResponse("analysis.html", {
        "request": request,
        "current_user": current_user,
        "disparities": paginated_results,
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
            "min_pct_diff": min_pct_diff if min_pct_diff is not None else "",
            "performance_rating": performance_rating if performance_rating is not None else "",
            "only_anomalies": only_anomalies
        }
    })

@router.get("/analysis/{emp_id}", response_class=HTMLResponse)
def investigation_detail_view(
    emp_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    employee = db.query(Employee).filter(Employee.id == emp_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail=f"Employee {emp_id} not found.")

    detector = DisparityDetector(db)
    analysis = detector.analyze_employee(employee)

    # Find open exceptions
    exceptions = db.query(DataQualityIssue).filter(
        DataQualityIssue.entity_id.in_([s.id for s in employee.salary_records] + [employee.id])
    ).all()

    return templates.TemplateResponse("investigation.html", {
        "request": request,
        "current_user": current_user,
        "employee": employee,
        "analysis": analysis,
        "exceptions": exceptions
    })
