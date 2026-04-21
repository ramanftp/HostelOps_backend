from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

from modules.owner.schemas import HostelOut, OwnerOut


# Base schemas with ORM mode
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# Expense schemas
class ExpenseBase(BaseSchema):
    hostel_id: int
    description: str
    amount: int
    date: datetime
    category: Optional[str] = None
    created_by: int


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseSchema):
    description: Optional[str] = None
    amount: Optional[int] = None
    date: Optional[datetime] = None
    category: Optional[str] = None


class ExpenseOut(ExpenseBase):
    id: int
    created_at: datetime
    updated_at: datetime
    hostel: Optional[HostelOut] = None
    owner: Optional[OwnerOut] = None