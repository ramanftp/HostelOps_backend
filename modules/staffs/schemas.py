
from pydantic import BaseModel
from typing import Optional


# ==================================================
# STAFF MASTER DATA SCHEMAS
# Used for WorkType, Status, Shift
# ==================================================

class StaffMasterData(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class StaffMasterCreate(BaseModel):
    name: str


class StaffMasterUpdate(BaseModel):
    name: Optional[str] = None


# ==================================================
# STAFF SCHEMAS
# ==================================================

class StaffsData(BaseModel):
    id: int
    name: str
    mobile: str
    salary: int
    work_type_id: int
    status_id: int
    shift_id: int

    class Config:
        from_attributes = True


class StaffCreate(BaseModel):
    name: str
    mobile: str
    salary: int
    work_type_id: int
    status_id: int
    shift_id: int


class StaffUpdate(BaseModel):
    name: Optional[str] = None
    mobile: Optional[str] = None
    salary: Optional[int] = None
    work_type_id: Optional[int] = None
    status_id: Optional[int] = None
    shift_id: Optional[int] = None


