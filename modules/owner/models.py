from email.mime import base
import uuid

from sqlalchemy import UUID, Column, Integer, String, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from core.database import Base



class Owner(Base):
    __tablename__ = "owners"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(20), unique=True, nullable=False)
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    email = Column(String(100), unique=True, nullable=True)
    status = Column(String(20), default="active", nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    area = Column(String(100), nullable=True)
    street_1 = Column(String(200), nullable=True)
    street_2 = Column(String(200), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    zipcode = Column(String(20), nullable=True)
    photo_url = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    hostels = relationship("Hostel", back_populates="owner")





class Hostel(Base):
    __tablename__ = "hostels"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    address = Column(String(200), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    zipcode = Column(String(20), nullable=True)
    photos_urls = Column(JSON, nullable=True)  # List of photo URLs
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    bank_account_number = Column(String(50), nullable=True)
    bank_ifsc_code = Column(String(20), nullable=True)
    bank_name = Column(String(100), nullable=True)
    bank_account_holder_name = Column(String(100), nullable=True)   
    upi_id = Column(String(100), nullable=True)
    category = Column(String(20), nullable=True)  # women, men, coliving...
    is_cash = Column(Boolean, default=True)
    facilities = Column(JSON, nullable=True)  # List of facilities


    owner = relationship("Owner", back_populates="hostels")
    rooms = relationship("Room", back_populates="hostel", cascade="all, delete-orphan")
    tenants = relationship("Tenant", back_populates="hostel", cascade="all, delete-orphan")


class RoomType(Base):
    __tablename__ = "room_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(200), nullable=True)
    

class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    hostel_id = Column(Integer, ForeignKey("hostels.id"), nullable=False)
    room_number = Column(String(20), nullable=False)
    room_type = Column(Integer, ForeignKey("room_types.id"), nullable=True)  # e.g., Single, Double, Dormitory
    no_of_beds = Column(Integer, nullable=True)
    no_of_occupied_beds = Column(Integer, nullable=True, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    hostel = relationship("Hostel", back_populates="rooms")
    room_type_rel = relationship("RoomType", backref="rooms")
    tenants = relationship("Tenant", back_populates="room", cascade="all, delete-orphan")



class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    phone_number = Column(String(20), unique=True, nullable=False)
    emergency_contact_name = Column(String(100), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    emergency_contact_relationship = Column(String(50), nullable=True)
    gender = Column(String(20), nullable=True)
    photo_url = Column(String(200), nullable=True)
    aadhaar_number = Column(String(20), unique=True, nullable=True)
    identity_verified = Column(Boolean, default=False)
    rent = Column(Integer, nullable=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    hostel_id = Column(Integer, ForeignKey("hostels.id"), nullable=True)
    join_date = Column(DateTime(timezone=True), server_default=func.now())
    alternate_phone_number = Column(String(20), nullable=True)
    address = Column(String(200), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    security_deposit = Column(Integer, nullable=True)
    zipcode = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    payments = relationship("TenantPayment", back_populates="tenant", cascade="all, delete-orphan")

    hostel = relationship("Hostel", back_populates="tenants")
    room = relationship("Room", back_populates="tenants")
    




class TenantPayment(Base):
    __tablename__ = "tenant_payments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    payment_date = Column(DateTime(timezone=True), server_default=func.now())
    payment_method = Column(String(50), nullable=True)  # e.g., Cash, UPI, Bank Transfer
    transaction_id = Column(String(100), unique=True, nullable=True)

    tenant = relationship("Tenant", back_populates="payments")