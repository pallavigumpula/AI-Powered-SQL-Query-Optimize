"""
Supporting Models
User authentication, Currency exchange, Audit logs, Comparison groups, and Data quality issues.
"""

from datetime import datetime, date
from sqlalchemy import Column, String, Float, Boolean, Date, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import relationship
from database.db_connection import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String(50), primary_key=True) # e.g., USR-001
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False, index=True) # Employee, Manager, HR Partner, IT/Operations Partner, System Administrator
    employee_id = Column(String(50), ForeignKey("employees.id"), nullable=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    employee = relationship("Employee")

    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"


class CurrencyExchangeRate(Base):
    __tablename__ = "currency_exchange_rates"

    id = Column(String(50), primary_key=True) # e.g., FX-EUR-USD-2026-01
    from_currency = Column(String(10), nullable=False, index=True)
    to_currency = Column(String(10), nullable=False, index=True) # Base currency e.g., USD
    rate = Column(Float, nullable=False) # e.g., EUR to USD = 1.085
    effective_from = Column(Date, nullable=False, index=True)
    effective_to = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<CurrencyExchangeRate({self.from_currency}->{self.to_currency}: {self.rate})>"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(50), primary_key=True) # e.g., AUD-2026-000001
    entity_name = Column(String(50), nullable=False, index=True) # Employee, SalaryRecord, AdjustmentProposal, etc.
    entity_id = Column(String(100), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True) # CREATE, UPDATE, DELETE, STATUS_CHANGE, UNAUTHORIZED_MODIFICATION
    actor_id = Column(String(100), nullable=False)
    actor_role = Column(String(50), nullable=False)
    
    old_values = Column(Text, nullable=True) # JSON serialized
    new_values = Column(Text, nullable=True) # JSON serialized
    ip_address = Column(String(50), nullable=True)
    severity = Column(String(20), nullable=False, default="INFO") # INFO, WARNING, CRITICAL
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<AuditLog({self.action} on {self.entity_name}:{self.entity_id} by {self.actor_id})>"


class ComparisonGroup(Base):
    __tablename__ = "comparison_groups"

    id = Column(String(50), primary_key=True) # e.g., GRP-SWE-L3-NYC
    name = Column(String(100), nullable=False)
    role_id = Column(String(50), ForeignKey("roles.id"), nullable=True)
    level_id = Column(String(50), ForeignKey("levels.id"), nullable=True)
    location_id = Column(String(50), ForeignKey("locations.id"), nullable=True)
    rationale = Column(Text, nullable=False) # Justification for grouping
    is_valid = Column(Boolean, nullable=False, default=True) # False if grouped in error (Case 5)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    role = relationship("Role", back_populates="comparison_groups")
    members = relationship("ComparisonGroupMember", back_populates="group")

    def __repr__(self):
        return f"<ComparisonGroup(id='{self.id}', name='{self.name}', valid={self.is_valid})>"


class ComparisonGroupMember(Base):
    __tablename__ = "comparison_group_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    comparison_group_id = Column(String(50), ForeignKey("comparison_groups.id"), nullable=False, index=True)
    employee_id = Column(String(50), ForeignKey("employees.id"), nullable=False, index=True)
    joined_date = Column(Date, default=date.today, nullable=False)

    group = relationship("ComparisonGroup", back_populates="members")
    employee = relationship("Employee", back_populates="group_memberships")

    def __repr__(self):
        return f"<ComparisonGroupMember(group='{self.comparison_group_id}', emp='{self.employee_id}')>"


class DataQualityIssue(Base):
    __tablename__ = "data_quality_issues"

    id = Column(String(50), primary_key=True) # e.g., DQI-2026-000001
    issue_type = Column(String(50), nullable=False, index=True)
    # EXPIRED_BAND, FTE_IGNORED, MISSING_EXCHANGE_RATE, UNAUTHORIZED_ADJUSTMENT, INCOMPARABLE_ROLE_GROUPING, ARITHMETIC_ERROR
    severity = Column(String(20), nullable=False, default="HIGH", index=True) # LOW, MEDIUM, HIGH, CRITICAL
    entity_type = Column(String(50), nullable=False) # SalaryRecord, CompensationBand, Employee, ComparisonGroup
    entity_id = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=False)
    
    status = Column(String(30), nullable=False, default="OPEN", index=True) # OPEN, INVESTIGATING, RESOLVED, DISMISSED
    ground_truth_label = Column(String(50), nullable=True) # Ground truth edge case label (e.g., CASE_1_EXPIRED_BAND)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)

    def __repr__(self):
        return f"<DataQualityIssue(id='{self.id}', type='{self.issue_type}', severity='{self.severity}')>"
