import enum

from pydantic import BaseModel, Field, ConfigDict, validator
from typing import Optional, List
from datetime import datetime
import re



# Base schemas with ORM mode
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# User schemas
class OwnerBase(BaseSchema):
    phone_number: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = Field(None, max_length=100)
    area: Optional[str] = None
    street_1: Optional[str] = None
    street_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zipcode: Optional[str] = None
    photo_url: Optional[str] = None

class OwnerCreate(OwnerBase):
    pass

class OwnerUpdate(BaseSchema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = None
    area: Optional[str] = None
    street_1: Optional[str] = None
    street_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zipcode: Optional[str] = None
    photo_url: Optional[str] = None


class OwnerOut(OwnerBase):
    id: int
    status: str
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class OwnerdetailHostelRoomOut(OwnerOut):
    hostels: List["HostelOut"] = []
    

# OTP schemas
class OTPRequest(BaseModel):
    phone_number: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')


class OTPVerify(BaseModel):
    phone_number: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')
    otp: str = Field(..., min_length=4, max_length=6)


class OTPResponse(BaseModel):
    ok: bool
    message: str
    expires_in: int
    debug_otp: Optional[str] = None
    sms_sent: Optional[bool] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    owner: OwnerOut


# Hostel schemas
class HostelBase(BaseSchema):
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zipcode: Optional[str] = None
    photos_urls: Optional[List[str]] = None
    bank_account_number: Optional[str] = None
    bank_ifsc_code: Optional[str] = None
    bank_name: Optional[str] = None
    category: Optional[str] = None
    bank_account_holder_name: Optional[str] = None
    upi_id: Optional[str] = None
    is_cash: Optional[bool] = True
    facilities: Optional[List[str]] = None

class HostelCreate(HostelBase):
    pass

class HostelUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zipcode: Optional[str] = None
    photos_urls: Optional[List[str]] = None
    bank_account_number: Optional[str] = None
    bank_ifsc_code: Optional[str] = None
    bank_name: Optional[str] = None
    category: Optional[str] = None
    bank_account_holder_name: Optional[str] = None
    upi_id: Optional[str] = None
    is_cash: Optional[bool] = None
    facilities: Optional[List[str]] = None

class HostelOut(HostelBase):
    id: int
    owner_id: int
    rooms: List["RoomOut"] = []
    tenants: List["TenantOut"] = []
    created_at: datetime
    updated_at: datetime


# Room schemas
class RoomBase(BaseSchema):
    room_number: str = Field(..., max_length=20)
    no_of_beds: Optional[int] = None

class RoomCreate(RoomBase):
    hostel_id: int
    room_type: Optional[int] = None  # Room type name for creation

class RoomUpdate(BaseSchema):
    room_number: Optional[str] = Field(None, max_length=20)
    room_type: Optional[int] = None  # Nested RoomType for updates
    no_of_beds: Optional[int] = None
    no_of_occupied_beds: Optional[int] = None
    theme_color: Optional[str] = None
class RoomOut(RoomBase):
    id: int
    hostel_id: int
    room_type_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class RoomHostelImgOut(RoomOut):
    hostel_photos_urls: Optional[List[str]] = None

class RoomTypeSchema(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    theme_color: Optional[str] = None # Hex color code

    class Config:
        from_attributes = True  


class RoomTypeCreate(BaseModel):
    name: str = Field(..., max_length=50)
    description: Optional[str] = Field(None, max_length=200)


class RoomTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=200)


class TenantBase(BaseSchema):
    name: str = Field(..., max_length=100)
    email: Optional[str] = Field(None, max_length=100)
    phone_number: str = Field(..., pattern=r'^\+?[1-9]\d{1,14}$')
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] 
    emergency_contact_relationship: Optional[str] = None
    gender: Optional[str] = None
    photo_url: Optional[str] = None
    aadhaar_number: Optional[str] = None
    identity_verified: Optional[bool] = False
    rent: Optional[int] = None
    join_date: Optional[datetime] = None
    security_deposit: Optional[int] = None
    alternate_phone_number: Optional[str] 
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zipcode: Optional[str] = None


class TenantCreate(TenantBase):
    room_id: Optional[int] = None
    hostel_id: Optional[int] = None


class TenantUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str]
    emergency_contact_relationship: Optional[str] = None
    gender: Optional[str] = None
    security_deposit: Optional[int] = None
    alternate_phone_number: Optional[str] 
    join_date: Optional[datetime] = None
    photo_url: Optional[str] = None
    aadhaar_number: Optional[str] = None
    identity_verified: Optional[bool] = None
    rent: Optional[int] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zipcode: Optional[str] = None
    room_id: Optional[int] = None
    hostel_id: Optional[int] = None


class TenantOut(TenantBase):
    id: int
    hostel_id: Optional[int] = None
    room: Optional[RoomOut] = None
    created_at: datetime
    updated_at: datetime


# Aadhaar OCR schemas
class AadhaarData(BaseModel):
    name: str
    aadhaar_no: str
    dob: str
    gender: str
    address: str
    image_path: Optional[str] = None
