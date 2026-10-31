"""
Routes Package
Exports authentication, dashboard, employee, compensation, analysis, proposal, and report routers.
"""

from routes.auth import router as auth_router
from routes.dashboard import router as dashboard_router
from routes.employees import router as employees_router
from routes.compensation import router as compensation_router
from routes.analysis import router as analysis_router
from routes.proposals import router as proposals_router
from routes.reports import router as reports_router

__all__ = [
    "auth_router",
    "dashboard_router",
    "employees_router",
    "compensation_router",
    "analysis_router",
    "proposals_router",
    "reports_router",
]
