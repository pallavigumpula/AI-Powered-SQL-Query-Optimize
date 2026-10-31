"""
Location Entity Model
Represents geographical offices and cost of living factors.
"""

from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime
from sqlalchemy.orm import relationship
from database.db_connection import Base

class Location(Base):
    __tablename__ = "locations"

    id = Column(String(50), primary_key=True)  # e.g., LOC-US-NYC
    code = Column(String(20), unique=True, nullable=False, index=True)
    city = Column(String(100), nullable=False)
    country = Column(String(100), nullable=False)
    region = Column(String(50), nullable=False) # Americas, EMEA, APAC
    cost_of_living_index = Column(Float, nullable=False, default=1.0) # Relative to base
    default_currency = Column(String(10), nullable=False, default="USD")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    employees = relationship("Employee", back_populates="location")
    compensation_bands = relationship("CompensationBand", back_populates="location")

    def __repr__(self):
        return f"<Location(id='{self.id}', city='{self.city}', country='{self.country}')>"
