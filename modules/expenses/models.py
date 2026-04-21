import uuid

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from core.database import Base


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    hostel_id = Column(Integer, ForeignKey("hostels.id"), nullable=False)
    description = Column(String(500), nullable=False)
    amount = Column(Integer, nullable=False)
    date = Column(DateTime, nullable=False)
    category = Column(String(100), nullable=True)  # e.g., maintenance, utilities, supplies
    created_by = Column(Integer, ForeignKey("owners.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    hostel = relationship("Hostel", back_populates="expenses")
    owner = relationship("Owner", back_populates="expenses")