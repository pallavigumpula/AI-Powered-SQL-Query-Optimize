"""
Tenure Entity Model
Tracks internal company tenure, current role tenure, and total career experience.
"""

from datetime import datetime, date
from sqlalchemy import Column, String, Integer, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database.db_connection import Base

class Tenure(Base):
    __tablename__ = "tenures"

    id = Column(String(50), primary_key=True) # e.g., TEN-EMP-000001
    employee_id = Column(String(50), ForeignKey("employees.id"), unique=True, nullable=False, index=True)
    
    total_months_experience = Column(Integer, nullable=False, default=0)
    company_tenure_months = Column(Integer, nullable=False, default=0)
    role_tenure_months = Column(Integer, nullable=False, default=0)
    prior_experience_months = Column(Integer, nullable=False, default=0)
    
    last_calculated_date = Column(Date, default=date.today, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    employee = relationship("Employee", back_populates="tenure_record")

    @property
    def company_tenure_years(self) -> float:
        return round(self.company_tenure_months / 12.0, 1)

    @property
    def total_experience_years(self) -> float:
        return round(self.total_months_experience / 12.0, 1)

    def __repr__(self):
        return f"<Tenure(emp='{self.employee_id}', company_months={self.company_tenure_months})>"
