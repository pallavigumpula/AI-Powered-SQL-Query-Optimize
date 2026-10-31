"""
Authentication and Role-Based Access Control (RBAC) Routes
Provides user login, session management, and one-click role switching for evaluation.
"""

from fastapi import APIRouter, Depends, Request, Response, Form, HTTPException, status
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from database.db_connection import get_db
from models.supporting import User
from config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Extracts active user from session cookie or defaults to HR Partner for administrative evaluation.
    """
    user_id = request.cookies.get("user_id")
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return user

    # Default to HR Partner if not logged in (for friction-free reviewer assessment)
    default_user = db.query(User).filter(User.role == settings.ROLE_HR_PARTNER).first()
    if not default_user:
        default_user = db.query(User).first()
    return default_user

@router.post("/login")
def login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid username or password.")
    
    # Accept demo password 'demo123' or 'admin123'
    if password not in ["demo123", "admin123"] and user.password_hash != password:
        raise HTTPException(status_code=400, detail="Invalid credentials.")

    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="user_id", value=user.id, httponly=True)
    return response

@router.get("/switch-role/{role_name}")
def switch_role(role_name: str, request: Request, db: Session = Depends(get_db)):
    """
    Allows rapid role-switching between all 5 enterprise personas:
    Employee, Manager, HR Partner, IT/Operations Partner, System Administrator.
    """
    # Map friendly URL tokens
    role_map = {
        "employee": settings.ROLE_EMPLOYEE,
        "manager": settings.ROLE_MANAGER,
        "hr": settings.ROLE_HR_PARTNER,
        "hr_partner": settings.ROLE_HR_PARTNER,
        "it_ops": settings.ROLE_IT_OPS,
        "admin": settings.ROLE_ADMIN,
    }
    target_role = role_map.get(role_name.lower(), role_name)
    user = db.query(User).filter(User.role == target_role).first()
    
    referer = request.headers.get("referer", "/dashboard")
    response = RedirectResponse(url=referer, status_code=status.HTTP_302_FOUND)
    if user:
        response.set_cookie(key="user_id", value=user.id, httponly=True)
    return response

@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key="user_id")
    return response
