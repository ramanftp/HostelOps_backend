from email.mime import base
import uuid

from sqlalchemy import UUID, Column, Integer, String, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from core.database import Base


class Bill(Base):
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, index=True)
    hostel_id = Column(Integer, ForeignKey("hostels.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    bill_number = Column(String(50), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    amount = Column(Integer, nullable=False)
    due_date = Column(DateTime, nullable=False)
    description = Column(String(500), nullable=True)
    status = Column(String(20), default="pending", nullable=False)  # pending, paid, overdue
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    hostel = relationship("Hostel", back_populates="bills")
    tenant = relationship("Tenant", back_populates="bills")
    transactions = relationship("Transaction", back_populates="bill", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    transaction_date = Column(DateTime(timezone=True), server_default=func.now())

    payment_method = Column(String(50), nullable=True)  # e.g., credit card, UPI, etc.
    status = Column(String(20), default="pending", nullable=False)  # pending, success, failed, verified
    transaction_id = Column(String(100), unique=True, nullable=True)
    bill_pdf_url = Column(String(200), nullable=True)  # URL to the generated PDF receipt
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    hostel_id = Column(Integer, ForeignKey("hostels.id"), nullable=False)
    bill = relationship("Bill", back_populates="transactions")


    tenant = relationship("Tenant", back_populates="transactions")
    hostel = relationship("Hostel", back_populates="transactions")