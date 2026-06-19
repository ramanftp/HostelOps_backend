from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from . import services
from .schema import ComplaintCreate, ComplaintUpdate, ComplaintOut, ComplaintTypeOut

router = APIRouter(prefix="/complaints", tags=["Complaints"])


@router.get("/", response_model=List[ComplaintOut], tags=["Complaints"])
def list_complaints(db: Session = Depends(get_db)):
    return services.get_complaints(db)


@router.get("/types", response_model=List[ComplaintTypeOut], tags=["Complaints"])
def list_complaint_types(db: Session = Depends(get_db)):
    return services.get_complaint_types(db)


@router.get("/{complaint_id}", response_model=ComplaintOut, tags=["Complaints"])
def get_complaint(complaint_id: int, db: Session = Depends(get_db)):
    complaint = services.get_complaint(db, complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint


@router.get("/hostel/{hostel_id}", response_model=List[ComplaintOut], tags=["Complaints"])
def get_complaints_by_hostel(hostel_id: int, db: Session = Depends(get_db)):
    return services.get_complaints_by_hostel(db, hostel_id)


@router.get("/tenant/{tenant_id}", response_model=List[ComplaintOut], tags=["Complaints"])
def get_complaints_by_tenant(tenant_id: int, db: Session = Depends(get_db)):
    return services.get_complaints_by_tenant(db, tenant_id)



@router.get("/owner/{owner_id}", response_model=List[ComplaintOut], tags=["Complaints"])
def get_complaints_by_owner(owner_id: int, db: Session = Depends(get_db)):
    return services.get_complaints_by_owner(db, owner_id)


@router.post("/", response_model=ComplaintOut, tags=["Complaints"])
def create_complaint(complaint: ComplaintCreate, db: Session = Depends(get_db)):
    return services.create_complaint(db, complaint)


@router.put("/{complaint_id}", response_model=ComplaintOut, tags=["Complaints"])
def update_complaint(complaint_id: int, complaint_update: ComplaintUpdate, db: Session = Depends(get_db)):
    updated_complaint = services.update_complaint(db, complaint_id, complaint_update)
    if not updated_complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return updated_complaint


@router.delete("/{complaint_id}", tags=["Complaints"])
def delete_complaint(complaint_id: int, db: Session = Depends(get_db)):
    if not services.delete_complaint(db, complaint_id):
        raise HTTPException(status_code=404, detail="Complaint not found")
    return {"message": "Complaint deleted successfully"}
