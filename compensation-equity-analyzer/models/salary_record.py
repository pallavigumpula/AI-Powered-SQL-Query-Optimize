"""
SalaryRecord Entity Model
Maintains historical, immutable compensation time-series records per employee.
"""

from datetime import datetime, date
from sqlalchemy import Column, String, Float, Boolean, Date, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from database.db_connection import Base

class SalaryRecord(Base):
    __tablename__ = "salary_records"

    id = Column(String(100), primary_key=True) # e.g., SAL-EMP-000001-2026-01
    employee_id = Column(String(50), ForeignKey("employees.id"), nullable=False, index=True)
    band_id = Column(String(100), ForeignKey("compensation_bands.id"), nullable=True, index=True)
    
    amount = Column(Float, nullable=False) # Actual nominal salary in local currency
    currency = Column(String(10), nullable=False, default="USD")
    effective_date = Column(Date, nullable=False, index=True)
    fte = Column(Float, nullable=False, default=1.0)
    
    # Normalized calculations (normalized to USD and FTE 1.0)
    normalized_salary = Column(Float, nullable=True) # (amount * exchange_rate) / fte
    compa_ratio = Column(Float, nullable=True) # (normalized_salary / band.mid_salary) * 100
    within_band_position = Column(Float, nullable=True) # ((normalized - min) / (max - min)) * 100
    band_status = Column(String(30), nullable=False, default="WITHIN_BAND") 
    # WITHIN_BAND, BELOW_MINIMUM, ABOVE_MAXIMUM, EXPIRED_BAND, MISSING_BAND

    is_current = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    employee = relationship("Employee", back_populates="salary_records")
    band = relationship("CompensationBand")

    def __repr__(self):
        return f"<SalaryRecord(id='{self.id}', emp='{self.employee_id}', amount={self.amount}, date='{self.effective_date}')>"
