"""
PerformanceEvidence Entity Model
Captures objective ratings and qualitative evidence for performance-based salary justification.
"""

from datetime import datetime, date
from sqlalchemy import Column, String, Integer, Float, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from database.db_connection import Base

class PerformanceEvidence(Base):
    __tablename__ = "performance_evidences"

    id = Column(String(100), primary_key=True) # e.g., PERF-EMP-000001-2025-H2
    employee_id = Column(String(50), ForeignKey("employees.id"), nullable=False, index=True)
    review_cycle = Column(String(20), nullable=False, index=True) # 2024-H1, 2025-H2, etc.
    
    rating = Column(Integer, nullable=False) # 1 to 5 scale
    goal_completion_percentage = Column(Float, nullable=False, default=100.0)
    evidence_summary = Column(Text, nullable=True) # Documented achievements, metrics
    
    reviewer_id = Column(String(50), ForeignKey("employees.id"), nullable=True)
    review_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    employee = relationship("Employee", foreign_keys=[employee_id], back_populates="performance_records")
    reviewer = relationship("Employee", foreign_keys=[reviewer_id])

    @property
    def rating_label(self) -> str:
        labels = {
            1: "Unsatisfactory",
            2: "Needs Improvement",
            3: "Meets Expectations",
            4: "Exceeds Expectations",
            5: "Outstanding"
        }
        return labels.get(self.rating, f"Rating {self.rating}")

    def __repr__(self):
        return f"<PerformanceEvidence(emp='{self.employee_id}', cycle='{self.review_cycle}', rating={self.rating})>"
