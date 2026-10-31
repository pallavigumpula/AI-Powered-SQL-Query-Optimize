"""
Reports, Data Exports, and System Integrity Settings Routes
Full CSV, JSON, SQL seed download endpoints, and downloadable executive equity report.
"""

import io
import csv
import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.db_connection import get_db
from models import (
    Employee, SalaryRecord, CompensationBand, AdjustmentProposal,
    DataQualityIssue, Role, Level, Location
)
from routes.auth import get_current_user
from services.disparity_detector import DisparityDetector
from services.validator import DataValidator
from services.evaluator import GroundTruthEvaluator
from services.reproducibility import run_reproducibility_check
from config import DATA_DIR, DATABASE_DIR, DOCS_DIR, settings

router = APIRouter(tags=["Reports & Exports"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

@router.get("/reports", response_class=HTMLResponse)
def reports_overview(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)

    total_employees = db.query(Employee).count()
    total_salary_records = db.query(SalaryRecord).count()
    detector = DisparityDetector(db)
    disparities = detector.detect_all_disparities(limit=50)
    open_issues = db.query(DataQualityIssue).filter(DataQualityIssue.status == "OPEN").all()
    proposals = db.query(AdjustmentProposal).all()

    # Department equity index: avg compa-ratio by department
    dept_stats = db.query(
        Employee.department,
        func.count(Employee.id),
        func.avg(SalaryRecord.compa_ratio),
        func.avg(SalaryRecord.normalized_salary)
    ).join(SalaryRecord, SalaryRecord.employee_id == Employee.id)\
     .filter(SalaryRecord.is_current == True)\
     .group_by(Employee.department).all()

    departments = []
    for d in dept_stats:
        departments.append({
            "name": d[0],
            "headcount": d[1],
            "avg_compa_ratio": round(float(d[2]), 2) if d[2] else 100.0,
            "avg_salary": round(float(d[3]), 2) if d[3] else 0.0,
        })

    return templates.TemplateResponse("reports.html", {
        "request": request,
        "current_user": current_user,
        "total_employees": total_employees,
        "total_salary_records": total_salary_records,
        "disparities": disparities,
        "open_issues": open_issues,
        "proposals": proposals,
        "departments": departments,
        "generated_date": datetime.utcnow().strftime("%B %d, %Y")
    })

# --- CSV & JSON EXPORT ENDPOINTS ---
@router.get("/api/v1/export/employees/csv")
def export_employees_csv(db: Session = Depends(get_db)):
    employees = db.query(Employee).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "first_name", "last_name", "email", "department", "role_id", "level_id", "location_id", "hire_date", "status", "fte", "currency"])
    for e in employees:
        writer.writerow([e.id, e.first_name, e.last_name, e.email, e.department, e.role_id, e.level_id, e.location_id, e.hire_date, e.status, e.fte, e.currency])
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=employees_export.csv"}
    )

@router.get("/api/v1/export/salary-history/csv")
def export_salary_history_csv(db: Session = Depends(get_db)):
    records = db.query(SalaryRecord).limit(10000).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "employee_id", "band_id", "amount", "currency", "effective_date", "fte", "normalized_salary", "compa_ratio", "within_band_position", "band_status", "is_current"])
    for s in records:
        writer.writerow([s.id, s.employee_id, s.band_id, s.amount, s.currency, s.effective_date, s.fte, s.normalized_salary, s.compa_ratio, s.within_band_position, s.band_status, s.is_current])
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=salary_history_export.csv"}
    )

@router.get("/api/v1/export/bands/csv")
def export_bands_csv(db: Session = Depends(get_db)):
    bands = db.query(CompensationBand).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "role_id", "level_id", "location_id", "currency", "min_salary", "mid_salary", "max_salary", "effective_from", "effective_to", "is_active"])
    for b in bands:
        writer.writerow([b.id, b.role_id, b.level_id, b.location_id, b.currency, b.min_salary, b.mid_salary, b.max_salary, b.effective_from, b.effective_to, b.is_active])
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=compensation_bands_export.csv"}
    )

@router.get("/api/v1/export/disparities/csv")
def export_disparities_csv(db: Session = Depends(get_db)):
    detector = DisparityDetector(db)
    disparities = detector.detect_all_disparities(limit=500)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["employee_id", "name", "role", "level", "location", "actual_salary", "normalized_salary", "group_median", "salary_diff", "pct_diff", "z_score", "performance_rating", "tenure_years", "explanation", "recommendation"])
    for d in disparities:
        writer.writerow([
            d.get("employee_id"), d.get("employee_name"), d.get("role"), d.get("level"), d.get("location"),
            d.get("actual_salary"), d.get("normalized_salary"), d.get("group_median_salary"),
            d.get("salary_difference"), d.get("percentage_difference"), d.get("z_score"),
            d.get("performance_rating"), d.get("tenure_years"),
            d.get("possible_explanation"), d.get("review_recommendation")
        ])
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=compensation_disparities_report.csv"}
    )

@router.get("/api/v1/export/proposals/csv")
def export_proposals_csv(db: Session = Depends(get_db)):
    proposals = db.query(AdjustmentProposal).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "employee_id", "current_salary", "proposed_salary", "currency", "pct_change", "status", "priority", "reason", "submitted_by", "effective_date"])
    for p in proposals:
        writer.writerow([p.id, p.employee_id, p.current_salary, p.proposed_salary, p.currency, p.percentage_change, p.status, p.priority, p.reason, p.submitted_by, p.effective_date])
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=adjustment_proposals_export.csv"}
    )

@router.get("/api/v1/export/ground-truth/csv")
def export_ground_truth_csv():
    fpath = DATA_DIR / "ground_truth.csv"
    if not fpath.exists():
        raise HTTPException(status_code=404, detail="Ground truth CSV not generated.")
    return FileResponse(fpath, media_type="text/csv", filename="ground_truth.csv")

@router.get("/api/v1/export/ground-truth/json")
def export_ground_truth_json():
    fpath = DATA_DIR / "ground_truth.json"
    if not fpath.exists():
        raise HTTPException(status_code=404, detail="Ground truth JSON not generated.")
    return FileResponse(fpath, media_type="application/json", filename="ground_truth.json")

@router.get("/api/v1/export/seed/sql")
def export_seed_sql():
    fpath = DATABASE_DIR / "seed.sql"
    if not fpath.exists():
        raise HTTPException(status_code=404, detail="Seed SQL file not found.")
    return FileResponse(fpath, media_type="application/sql", filename="seed.sql")

@router.get("/api/v1/export/dataset/json")
def export_full_dataset_json(db: Session = Depends(get_db)):
    employees = db.query(Employee).limit(1000).all()
    dataset = []
    for e in employees:
        sal = e.current_salary_record
        dataset.append({
            "id": e.id,
            "name": e.full_name,
            "role": e.role.name if e.role else "",
            "level": e.level.code if e.level else "",
            "location": e.location.city if e.location else "",
            "fte": e.fte,
            "current_salary": sal.amount if sal else 0.0,
            "normalized_salary": sal.normalized_salary if sal else 0.0,
            "currency": e.currency,
            "compa_ratio": sal.compa_ratio if sal else None,
            "band_status": sal.band_status if sal else "UNKNOWN",
            "hire_date": str(e.hire_date)
        })
    return StreamingResponse(
        io.BytesIO(json.dumps(dataset, indent=2).encode("utf-8")),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=yottaflex_equity_dataset.json"}
    )

# --- SETTINGS & SYSTEM INTEGRITY ---
@router.get("/settings", response_class=HTMLResponse)
def settings_view(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)

    # Read latest summary reports
    val_file = DOCS_DIR / "validation_summary.json"
    eval_file = DOCS_DIR / "evaluation_report.json"
    rep_file = DOCS_DIR / "reproducibility_report.json"

    val_data = json.load(open(val_file)) if val_file.exists() else {}
    eval_data = json.load(open(eval_file)) if eval_file.exists() else {}
    rep_data = json.load(open(rep_file)) if rep_file.exists() else {}

    return templates.TemplateResponse("settings.html", {
        "request": request,
        "current_user": current_user,
        "settings": settings,
        "validation": val_data,
        "evaluation": eval_data,
        "reproducibility": rep_data
    })
