"""
Level Entity Model
Represents seniority/career levels (L1 through L6).
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.orm import relationship
from database.db_connection import Base

class Level(Base):
    __tablename__ = "levels"

    id = Column(String(50), primary_key=True)  # e.g., LVL-L1
    code = Column(String(20), unique=True, nullable=False, index=True) # L1, L2, L3, L4, L5, L6
    name = Column(String(100), nullable=False) # Associate, Mid, Senior, Staff, Principal, Executive
    hierarchy_order = Column(Integer, nullable=False, index=True) # 1 to 6
    min_experience_years = Column(Integer, nullable=False, default=0)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    employees = relationship("Employee", back_populates="level")
    compensation_bands = relationship("CompensationBand", back_populates="level")
    promotions_from = relationship("Promotion", foreign_keys="Promotion.from_level_id", back_populates="from_level")
    promotions_to = relationship("Promotion", foreign_keys="Promotion.to_level_id", back_populates="to_level")

    def __repr__(self):
        return f"<Level(id='{self.id}', code='{self.code}', name='{self.name}')>"
