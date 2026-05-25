from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ComplaintTypeBase(BaseSchema):
    name: str
    description: Optional[str] = None


class ComplaintTypeOut(ComplaintTypeBase):
    id: int
    created_at: datetime
    updated_at: datetime


class ComplaintBase(BaseSchema):
    hostel_id: Optional[int] = None
    tenant_id: Optional[int] = None
    owner_id: Optional[int] = None
    complaint_type_id: int
    description: str
    status: Optional[str] = Field(default="open")
    priority: Optional[str] = Field(default="normal")


class ComplaintCreate(ComplaintBase):
    pass


class ComplaintUpdate(BaseSchema):
    hostel_id: Optional[int] = None
    tenant_id: Optional[int] = None
    owner_id: Optional[int] = None
    complaint_type_id: Optional[int] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None


class ComplaintOut(ComplaintBase):
    id: int
    created_at: datetime
    updated_at: datetime
    complaint_type: Optional[ComplaintTypeOut] = None
