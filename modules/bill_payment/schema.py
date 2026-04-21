import enum

from pydantic import BaseModel, Field, ConfigDict, validator
from typing import Optional, List
from datetime import datetime
import re

from modules.owner.schemas import HostelOut, TenantOut, TenantOut


# Base schemas with ORM mode
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True) 

# Bill schemas
class BillBase(BaseSchema):
    hostel_id: int
    tenant_id: int
    amount: int
    due_date: datetime
    description: Optional[str] = None
    status: Optional[str] = "pending"

class BillCreate(BillBase):
    pass

class BillUpdate(BaseSchema):
    amount: Optional[int] = None
    due_date: Optional[datetime] = None
    description: Optional[str] = None
    status: Optional[str] = None

class BillOut(BillBase):
    id: int
    bill_number: str
    created_at: datetime
    updated_at: datetime
    tenant : Optional["TenantOut"] = None

class TransactionBase(BaseSchema):
    bill_id: int
    amount: int
    payment_method: Optional[str] = None
    status: Optional[str] = "success"
    tenant_id: int
    hostel_id: int


class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseSchema):
    amount: Optional[int] = None
    payment_method: Optional[str] = None
    status: Optional[str] = None

class TransactionOut(TransactionBase):
    id: int
    transaction_date: datetime
    tenant : Optional["TenantOut"] = None
    bill: Optional["BillOut"] = None