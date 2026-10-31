"""
Role Entity Model
Represents a job role within the organization.
"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.orm import relationship
from database.db_connection import Base

class Role(Base):
    __tablename__ = "roles"

    id = Column(String(50), primary_key=True)  # e.g., ROLE-SWE
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    department = Column(String(100), nullable=False, index=True)
    job_family = Column(String(100), nullable=False, index=True) # Engineering, AI & Data, Product, etc.
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    employees = relationship("Employee", back_populates="role")
    compensation_bands = relationship("CompensationBand", back_populates="role")
    comparison_groups = relationship("ComparisonGroup", back_populates="role")

    def __repr__(self):
        return f"<Role(id='{self.id}', name='{self.name}', department='{self.department}')>"
