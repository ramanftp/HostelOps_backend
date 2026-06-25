from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from core.database import Base


class ComplaintType(Base):
    __tablename__ = "complaint_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    complaints = relationship("Complaint", back_populates="complaint_type")


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    hostel_id = Column(Integer, ForeignKey("hostels.id"), nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=True)
    complaint_type_id = Column(Integer, ForeignKey("complaint_types.id"), nullable=False)
    description = Column(String(1000), nullable=False)
    status = Column(String(50), nullable=False, default="open")
    priority = Column(String(50), nullable=False, default="normal")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    hostel = relationship("Hostel", backref="complaints")
    tenant = relationship("Tenant", backref="complaints")
    owner = relationship("Owner", backref="complaints")
    complaint_type = relationship("ComplaintType", back_populates="complaints")


class NoticeBoard(Base):
    __tablename__ = "notice_boards"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    hostel_id = Column(Integer, ForeignKey("hostels.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=False)
    from_date = Column(DateTime, nullable=False)
    to_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    hostel = relationship("Hostel", backref="notice_boards")