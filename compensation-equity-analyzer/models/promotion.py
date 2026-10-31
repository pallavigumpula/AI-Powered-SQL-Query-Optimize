"""
Promotion Entity Model
Maintains historical promotion milestones and level progression.
"""

from datetime import datetime, date
from sqlalchemy import Column, String, Float, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from database.db_connection import Base

class Promotion(Base):
    __tablename__ = "promotions"

    id = Column(String(50), primary_key=True) # e.g., PROM-2025-000001
    employee_id = Column(String(50), ForeignKey("employees.id"), nullable=False, index=True)
    
    from_level_id = Column(String(50), ForeignKey("levels.id"), nullable=False)
    to_level_id = Column(String(50), ForeignKey("levels.id"), nullable=False)
    
    effective_date = Column(Date, nullable=False, index=True)
    justification = Column(Text, nullable=False)
    salary_increase_pct = Column(Float, nullable=True)
    approved_by = Column(String(50), nullable=True) # Manager or HR Partner
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    employee = relationship("Employee", back_populates="promotions")
    from_level = relationship("Level", foreign_keys=[from_level_id], back_populates="promotions_from")
    to_level = relationship("Level", foreign_keys=[to_level_id], back_populates="promotions_to")

    def __repr__(self):
        return f"<Promotion(id='{self.id}', emp='{self.employee_id}', {self.from_level_id}->{self.to_level_id})>"
