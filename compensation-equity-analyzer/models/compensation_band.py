"""
CompensationBand Entity Model
Defines salary ranges (Min, Mid, Max) for Role + Level + Location combinations.
"""

from datetime import datetime, date
from sqlalchemy import Column, String, Float, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database.db_connection import Base

class CompensationBand(Base):
    __tablename__ = "compensation_bands"

    id = Column(String(100), primary_key=True) # e.g., BAND-ROLE-SWE-LVL-L3-LOC-NYC-2026
    role_id = Column(String(50), ForeignKey("roles.id"), nullable=False, index=True)
    level_id = Column(String(50), ForeignKey("levels.id"), nullable=False, index=True)
    location_id = Column(String(50), ForeignKey("locations.id"), nullable=False, index=True)
    currency = Column(String(10), nullable=False, default="USD")
    
    min_salary = Column(Float, nullable=False)
    mid_salary = Column(Float, nullable=False)
    max_salary = Column(Float, nullable=False)
    
    effective_from = Column(Date, nullable=False, index=True)
    effective_to = Column(Date, nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    role = relationship("Role", back_populates="compensation_bands")
    level = relationship("Level", back_populates="compensation_bands")
    location = relationship("Location", back_populates="compensation_bands")

    @property
    def spread_percentage(self) -> float:
        if self.min_salary and self.min_salary > 0:
            return round(((self.max_salary - self.min_salary) / self.min_salary) * 100, 2)
        return 0.0

    def is_currently_effective(self, as_of_date: date = None) -> bool:
        check_date = as_of_date or date.today()
        return self.is_active and (self.effective_from <= check_date <= self.effective_to)

    def __repr__(self):
        return f"<CompensationBand(id='{self.id}', role='{self.role_id}', level='{self.level_id}', mid={self.mid_salary})>"
