"""
AdjustmentProposal, ApprovalHistory, and AdjustmentEvent Models
Complete lifecycle management for salary adjustment proposals.
"""

from datetime import datetime, date
from sqlalchemy import Column, String, Float, Boolean, Date, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from database.db_connection import Base

class AdjustmentProposal(Base):
    __tablename__ = "adjustment_proposals"

    id = Column(String(50), primary_key=True) # e.g., ADJ-2026-000001
    employee_id = Column(String(50), ForeignKey("employees.id"), nullable=False, index=True)
    
    current_salary = Column(Float, nullable=False)
    proposed_salary = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default="USD")
    
    percentage_change = Column(Float, nullable=False)
    reason = Column(String(200), nullable=False) # Market Equity, Promotion Adjustment, Anomaly Resolution
    supporting_evidence = Column(Text, nullable=False) # Anomaly report, performance rating, tenure metrics
    
    # State machine: Draft, Pending Manager Review, Pending HR Review, Approved, Rejected, Implemented, On Hold
    status = Column(String(50), nullable=False, default="Draft", index=True)
    priority = Column(String(20), nullable=False, default="Medium") # Low, Medium, High, Urgent
    
    submitted_by = Column(String(100), nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    
    effective_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    employee = relationship("Employee", back_populates="adjustment_proposals")
    approval_history = relationship("ApprovalHistory", back_populates="proposal", order_by="ApprovalHistory.action_timestamp")
    adjustment_event = relationship("AdjustmentEvent", back_populates="proposal", uselist=False)

    def __repr__(self):
        return f"<AdjustmentProposal(id='{self.id}', emp='{self.employee_id}', status='{self.status}')>"


class ApprovalHistory(Base):
    __tablename__ = "approval_history"

    id = Column(String(50), primary_key=True) # e.g., APPH-2026-000001
    proposal_id = Column(String(50), ForeignKey("adjustment_proposals.id"), nullable=False, index=True)
    
    previous_status = Column(String(50), nullable=False)
    new_status = Column(String(50), nullable=False)
    
    actor_id = Column(String(100), nullable=False) # Username or Email
    actor_role = Column(String(50), nullable=False) # Manager, HR Partner, Admin
    action_type = Column(String(50), nullable=False) # SUBMIT, APPROVE, REJECT, REQUEST_INFO, HOLD
    comments = Column(Text, nullable=True)
    
    action_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    proposal = relationship("AdjustmentProposal", back_populates="approval_history")

    def __repr__(self):
        return f"<ApprovalHistory(proposal='{self.proposal_id}', {self.previous_status}->{self.new_status})>"


class AdjustmentEvent(Base):
    __tablename__ = "adjustment_events"

    id = Column(String(50), primary_key=True) # e.g., EVT-2026-000001
    proposal_id = Column(String(50), ForeignKey("adjustment_proposals.id"), nullable=True, index=True)
    employee_id = Column(String(50), ForeignKey("employees.id"), nullable=False, index=True)
    
    old_salary = Column(Float, nullable=False)
    new_salary = Column(Float, nullable=False)
    effective_date = Column(Date, nullable=False, index=True)
    
    is_authorized = Column(Boolean, nullable=False, default=True, index=True)
    applied_by = Column(String(100), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    proposal = relationship("AdjustmentProposal", back_populates="adjustment_event")
    employee = relationship("Employee")

    def __repr__(self):
        return f"<AdjustmentEvent(id='{self.id}', emp='{self.employee_id}', authorized={self.is_authorized})>"
