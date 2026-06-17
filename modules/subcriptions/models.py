# from email.mime import base
# import uuid

from sqlalchemy import UUID, Column, Integer, String, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from core.database import Base



class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(String(100), unique=True, nullable=False)  # Razorpay plan ID
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    price = Column(Integer, nullable=False)  # Price in cents
    duration_months = Column(Integer, nullable=False)  # Duration of the plan in months
    features = Column(JSON, nullable=True)  # List of features included in the plan
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    subscriptions = relationship("Subscriptions", back_populates="plan")







class Subscriptions(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=False)
    subscription_id = Column(String(100), unique=True, nullable=False)  # Razorpay subscription ID
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    customer_id = Column(String(100), nullable=True)  # Razorpay customer ID
    start_date = Column(DateTime, default=func.now())
    end_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


    owner = relationship("Owner", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")