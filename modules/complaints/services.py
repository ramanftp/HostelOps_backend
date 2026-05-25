from typing import List, Optional
from sqlalchemy.orm import Session

from .models import Complaint, ComplaintType
from .schema import ComplaintCreate, ComplaintUpdate


def get_complaints(db: Session) -> List[Complaint]:
    return db.query(Complaint).all()


def get_complaint_types(db: Session) -> List[ComplaintType]:
    return db.query(ComplaintType).all()


def get_complaint(db: Session, complaint_id: int) -> Optional[Complaint]:
    return db.query(Complaint).filter(Complaint.id == complaint_id).first()


def get_complaints_by_hostel(db: Session, hostel_id: int) -> List[Complaint]:
    return db.query(Complaint).filter(Complaint.hostel_id == hostel_id).all()


def get_complaints_by_tenant(db: Session, tenant_id: int) -> List[Complaint]:
    return db.query(Complaint).filter(Complaint.tenant_id == tenant_id).all()


def get_complaints_by_owner(db: Session, owner_id: int) -> List[Complaint]:
    return db.query(Complaint).filter(Complaint.owner_id == owner_id).all()


def create_complaint(db: Session, complaint: ComplaintCreate) -> Complaint:
    db_complaint = Complaint(**complaint.model_dump())
    db.add(db_complaint)
    db.commit()
    db.refresh(db_complaint)
    return db_complaint


def update_complaint(db: Session, complaint_id: int, complaint_update: ComplaintUpdate) -> Optional[Complaint]:
    db_complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not db_complaint:
        return None

    update_data = complaint_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_complaint, field, value)

    db.commit()
    db.refresh(db_complaint)
    return db_complaint


def delete_complaint(db: Session, complaint_id: int) -> bool:
    db_complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not db_complaint:
        return False

    db.delete(db_complaint)
    db.commit()
    return True
