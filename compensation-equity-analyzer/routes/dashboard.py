"""
Dashboard and KPI Overview Routes
Computes real-time KPI metrics and Chart.js analytics directly from database records.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from pathlib import Path
from collections import defaultdict
import numpy as np

from database.db_connection import get_db
from models import (
    Employee, SalaryRecord, CompensationBand, AdjustmentProposal,
    DataQualityIssue, Role, Level, Location
)
from routes.auth import get_current_user
from services.disparity_detector import DisparityDetector

router = APIRouter(tags=["Dashboard"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

@router.get("/", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_view(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)

    # 1. KPI Calculations from actual DB records
    total_employees = db.query(Employee).count()
    within_band = db.query(SalaryRecord).filter(SalaryRecord.is_current == True, SalaryRecord.band_status == "WITHIN_BAND").count()
    below_band = db.query(SalaryRecord).filter(SalaryRecord.is_current == True, SalaryRecord.band_status == "BELOW_MINIMUM").count()
    above_band = db.query(SalaryRecord).filter(SalaryRecord.is_current == True, SalaryRecord.band_status == "ABOVE_MAXIMUM").count()
    
    pending_hr = db.query(AdjustmentProposal).filter(AdjustmentProposal.status == "Pending HR Review").count()
    approved_adj = db.query(AdjustmentProposal).filter(AdjustmentProposal.status.in_(["Approved", "Implemented"])).count()
    exceptions_count = db.query(DataQualityIssue).filter(DataQualityIssue.status == "OPEN").count()

    # Disparities detected count
    detector = DisparityDetector(db)
    detected_disparities = detector.detect_all_disparities(limit=50)
    disparities_count = len(detected_disparities)

    # 2. Chart 1: Salary Distribution (histogram bins in USD thousands)
    curr_salaries = [
        s[0] for s in db.query(SalaryRecord.normalized_salary).filter(
            SalaryRecord.is_current == True, SalaryRecord.normalized_salary.isnot(None)
        ).all()
    ]
    bins = [0, 80000, 110000, 140000, 180000, 230000, 300000, 450000]
    bin_labels = ["< $80k", "$80k-$110k", "$110k-$140k", "$140k-$180k", "$180k-$230k", "$230k-$300k", "> $300k"]
    hist, _ = np.histogram(curr_salaries, bins=bins) if curr_salaries else ([0]*len(bin_labels), None)
    salary_dist_data = {
        "labels": bin_labels,
        "counts": [int(x) for x in hist]
    }

    # 3. Chart 2: Compensation by Role
    role_avgs = db.query(
        Role.name, func.avg(SalaryRecord.normalized_salary)
    ).join(Employee, Employee.role_id == Role.id)\
     .join(SalaryRecord, SalaryRecord.employee_id == Employee.id)\
     .filter(SalaryRecord.is_current == True)\
     .group_by(Role.name).all()
    role_chart = {
        "labels": [r[0] for r in role_avgs],
        "values": [round(float(r[1]), 2) if r[1] else 0 for r in role_avgs]
    }

    # 4. Chart 3: Compensation by Level
    level_avgs = db.query(
        Level.code, Level.name, func.avg(SalaryRecord.normalized_salary), Level.hierarchy_order
    ).join(Employee, Employee.level_id == Level.id)\
     .join(SalaryRecord, SalaryRecord.employee_id == Employee.id)\
     .filter(SalaryRecord.is_current == True)\
     .group_by(Level.code, Level.name, Level.hierarchy_order)\
     .order_by(Level.hierarchy_order).all()
    level_chart = {
        "labels": [f"{l[0]} - {l[1]}" for l in level_avgs],
        "values": [round(float(l[2]), 2) if l[2] else 0 for l in level_avgs]
    }

    # 5. Chart 4: Compensation by Location
    loc_avgs = db.query(
        Location.city, func.avg(SalaryRecord.normalized_salary)
    ).join(Employee, Employee.location_id == Location.id)\
     .join(SalaryRecord, SalaryRecord.employee_id == Employee.id)\
     .filter(SalaryRecord.is_current == True)\
     .group_by(Location.city).all()
    location_chart = {
        "labels": [l[0] for l in loc_avgs],
        "values": [round(float(l[1]), 2) if l[1] else 0 for l in loc_avgs]
    }

    # 6. Chart 5: Salary Band Comparison (Sample top roles min, mid, max vs actual)
    band_query = db.query(
        Role.code, Level.code,
        func.avg(CompensationBand.min_salary),
        func.avg(CompensationBand.mid_salary),
        func.avg(CompensationBand.max_salary)
    ).join(Role, CompensationBand.role_id == Role.id)\
     .join(Level, CompensationBand.level_id == Level.id)\
     .filter(CompensationBand.is_active == True)\
     .group_by(Role.code, Level.code)\
     .limit(8).all()

    # Get actual average per (role, level)
    actual_avgs = dict(
        db.query(
            func.concat(Role.code, "-", Level.code),
            func.avg(SalaryRecord.normalized_salary)
        ).join(Employee, SalaryRecord.employee_id == Employee.id)\
         .join(Role, Employee.role_id == Role.id)\
         .join(Level, Employee.level_id == Level.id)\
         .filter(SalaryRecord.is_current == True)\
         .group_by(Role.code, Level.code).all()
    )

    band_comp_chart = {
        "labels": [f"{b[0]}-{b[1]}" for b in band_query],
        "min": [round(b[2], 0) for b in band_query],
        "mid": [round(b[3], 0) for b in band_query],
        "max": [round(b[4], 0) for b in band_query],
        "actual": [round(actual_avgs.get(f"{b[0]}-{b[1]}", b[3]), 0) for b in band_query],
    }

    # 7. Chart 6: Disparity Distribution (% difference histogram)
    pct_diffs = [d["percentage_difference"] for d in detected_disparities]
    disp_bins = [-40, -25, -15, -5, 5, 15, 25, 40]
    disp_labels = ["-40% to -25%", "-25% to -15%", "-15% to -5%", "-5% to +5%", "+5% to +15%", "+15% to +25%", "> +25%"]
    disp_hist, _ = np.histogram(pct_diffs, bins=disp_bins) if pct_diffs else ([0]*len(disp_labels), None)
    disparity_dist_chart = {
        "labels": disp_labels,
        "counts": [int(x) for x in disp_hist]
    }

    # 8. Chart 7: Monthly Salary Trends
    trends = db.query(
        SalaryRecord.effective_date, func.avg(SalaryRecord.normalized_salary)
    ).group_by(SalaryRecord.effective_date)\
     .order_by(SalaryRecord.effective_date).all()
    trend_chart = {
        "labels": [t[0].strftime("%b %Y") for t in trends],
        "values": [round(float(t[1]), 2) for t in trends]
    }

    # 9. Chart 8: Review Proposal Status Breakdown
    prop_statuses = db.query(
        AdjustmentProposal.status, func.count(AdjustmentProposal.id)
    ).group_by(AdjustmentProposal.status).all()
    status_map = {
        "Draft": 0, "Pending Manager Review": 0, "Pending HR Review": 0,
        "Approved": 0, "Rejected": 0, "Implemented": 0, "On Hold": 0
    }
    for s, c in prop_statuses:
        status_map[s] = c
    proposal_chart = {
        "labels": list(status_map.keys()),
        "counts": list(status_map.values())
    }

    # Recent Audit Activity
    recent_issues = db.query(DataQualityIssue).order_by(DataQualityIssue.created_at.desc()).limit(5).all()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "current_user": current_user,
        "kpis": {
            "total_employees": total_employees,
            "within_band": within_band,
            "below_band": below_band,
            "above_band": above_band,
            "disparities_detected": disparities_count,
            "pending_hr_reviews": pending_hr,
            "exceptions_count": exceptions_count,
            "approved_adjustments": approved_adj
        },
        "charts": {
            "salary_dist": salary_dist_data,
            "role_comp": role_chart,
            "level_comp": level_chart,
            "location_comp": location_chart,
            "band_comp": band_comp_chart,
            "disparity_dist": disparity_dist_chart,
            "monthly_trends": trend_chart,
            "proposal_status": proposal_chart
        },
        "recent_issues": recent_issues,
        "disparities_preview": detected_disparities[:6]
    })
