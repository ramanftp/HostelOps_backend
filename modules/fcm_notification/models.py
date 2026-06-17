from email.mime import base
import uuid

from sqlalchemy import UUID, Column, Integer, String, Boolean, DateTime, JSON, ForeignKey, Float, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import object_session, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime
import enum

from core.database import Base


class NotificationToken(Base):
    __tablename__ = "notification_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    device_name = Column(String(255), nullable=True)
    brand = Column(String(255), nullable=True)
    device_id = Column(String(255), nullable=True)
    platform = Column(String(255), nullable=True)
    os_version = Column(String(255), nullable=True)
    city = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    role = Column(String(50), nullable=True) # tenant, owner, staff
