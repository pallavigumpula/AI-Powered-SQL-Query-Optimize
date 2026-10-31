"""
Employee Entity Model
Core representation of company employees.
"""

from datetime import datetime, date
from sqlalchemy import Column, String, Float, Date, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from database.db_connection import Base

class Employee(Base):
    __tablename__ = "employees"

    id = Column(String(50), primary_key=True)  # e.g., EMP-000001
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    department = Column(String(100), nullable=False, index=True)
    
    role_id = Column(String(50), ForeignKey("roles.id"), nullable=False, index=True)
    level_id = Column(String(50), ForeignKey("levels.id"), nullable=False, index=True)
    location_id = Column(String(50), ForeignKey("locations.id"), nullable=False, index=True)
    manager_id = Column(String(50), ForeignKey("employees.id"), nullable=True, index=True)
    
    hire_date = Column(Date, nullable=False, index=True)
    status = Column(String(20), nullable=False, default="Active", index=True) # Active, On Leave, Terminated
    fte = Column(Float, nullable=False, default=1.0) # Full-Time Equivalent (e.g., 1.0, 0.8, 0.5)
    currency = Column(String(10), nullable=False, default="USD")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    role = relationship("Role", back_populates="employees")
    level = relationship("Level", back_populates="employees")
    location = relationship("Location", back_populates="employees")
    
    manager = relationship("Employee", remote_side=[id], backref="direct_reports")
    
    salary_records = relationship("SalaryRecord", back_populates="employee", order_by="desc(SalaryRecord.effective_date)")
    performance_records = relationship("PerformanceEvidence", foreign_keys="[PerformanceEvidence.employee_id]", back_populates="employee", order_by="desc(PerformanceEvidence.review_date)")
    tenure_record = relationship("Tenure", back_populates="employee", uselist=False)
    promotions = relationship("Promotion", back_populates="employee", order_by="desc(Promotion.effective_date)")
    adjustment_proposals = relationship("AdjustmentProposal", back_populates="employee")
    group_memberships = relationship("ComparisonGroupMember", back_populates="employee")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def current_salary_record(self):
        """Returns the latest active salary record."""
        if self.salary_records:
            return self.salary_records[0]
        return None

    def __repr__(self):
        return f"<Employee(id='{self.id}', name='{self.full_name}', role='{self.role_id}')>"
