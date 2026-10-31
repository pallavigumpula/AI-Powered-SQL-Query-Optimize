"""
YottaFlex.ai Compensation Equity Analyzer - Main Application Entry Point
FastAPI Enterprise Application with RBAC, Data Pipelines, and Disparity Analytics.
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import uvicorn

from config import settings
from database.db_connection import init_db, SessionLocal
from models.supporting import User
from routes import (
    auth_router,
    dashboard_router,
    employees_router,
    compensation_router,
    analysis_router,
    proposals_router,
    reports_router
)

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_SUBTITLE,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Base Directories
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

# Mount Static Files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Jinja2 Templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Register Routers
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(employees_router)
app.include_router(compensation_router)
app.include_router(analysis_router)
app.include_router(proposals_router)
app.include_router(reports_router)

@app.on_event("startup")
def on_startup():
    """Ensure database schema is verified on application launch."""
    init_db()

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Renders authentication page with demo credentials for all 5 roles."""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "app_name": settings.APP_NAME,
        "app_subtitle": settings.APP_SUBTITLE
    })

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": "MySQL" if settings.USE_MYSQL else "SQLite Fallback",
        "seed": settings.RANDOM_SEED
    }

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
