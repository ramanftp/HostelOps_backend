from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from modules.owner.security import get_current_owner

from .models import Staff, WorkType, Status, Shift
from .schemas import StaffMasterData, StaffMasterCreate, StaffMasterUpdate, StaffsData, StaffCreate, StaffUpdate

router = APIRouter(prefix="/staffs", tags=["Staffs"])


@router.get(
    "/work-types",
    response_model=list[StaffMasterData]
)
def get_work_types(
    db: Session = Depends(get_db)
):
    return db.query(WorkType).all()


@router.post(
    "/work-types",
    response_model=StaffMasterData
)
def create_work_type(
    work_type: StaffMasterCreate,
    db: Session = Depends(get_db)
):
    db_work_type = WorkType(**work_type.model_dump())

    db.add(db_work_type)
    db.commit()
    db.refresh(db_work_type)

    return db_work_type


@router.patch(
    "/work-types/{work_type_id}",
    response_model=StaffMasterData
)
def update_work_type(
    work_type_id: int,
    work_type_update: StaffMasterUpdate,
    db: Session = Depends(get_db)
):
    work_type = db.query(WorkType).filter(
        WorkType.id == work_type_id
    ).first()

    if not work_type:
        raise HTTPException(
            status_code=404,
            detail="Work type not found"
        )

    update_data = work_type_update.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(work_type, field, value)

    db.commit()
    db.refresh(work_type)

    return work_type


@router.delete("/work-types/{work_type_id}")
def delete_work_type(
    work_type_id: int,
    db: Session = Depends(get_db)
):
    work_type = db.query(WorkType).filter(
        WorkType.id == work_type_id
    ).first()

    if not work_type:
        raise HTTPException(
            status_code=404,
            detail="Work type not found"
        )

    db.delete(work_type)
    db.commit()

    return {
        "message": "Work type deleted successfully"
    }

@router.get(
    "/statuses",
    response_model=list[StaffMasterData]
)
def get_statuses(
    db: Session = Depends(get_db)
):
    return db.query(Status).all()


@router.post(
    "/statuses",
    response_model=StaffMasterData
)
def create_status(
    status: StaffMasterCreate,
    db: Session = Depends(get_db)
):
    db_status = Status(**status.model_dump())

    db.add(db_status)
    db.commit()
    db.refresh(db_status)

    return db_status


@router.patch(
    "/statuses/{status_id}",
    response_model=StaffMasterData
)
def update_status(
    status_id: int,
    status_update: StaffMasterUpdate,
    db: Session = Depends(get_db)
):
    status = db.query(Status).filter(
        Status.id == status_id
    ).first()

    if not status:
        raise HTTPException(
            status_code=404,
            detail="Status not found"
        )

    update_data = status_update.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(status, field, value)

    db.commit()
    db.refresh(status)

    return status


@router.delete("/statuses/{status_id}")
def delete_status(
    status_id: int,
    db: Session = Depends(get_db)
):
    status = db.query(Status).filter(
        Status.id == status_id
    ).first()

    if not status:
        raise HTTPException(
            status_code=404,
            detail="Status not found"
        )

    db.delete(status)
    db.commit()

    return {
        "message": "Status deleted successfully"
    }

@router.get(
    "/shifts",
    response_model=list[StaffMasterData]
)
def get_shifts(
    db: Session = Depends(get_db)
):
    return db.query(Shift).all()


@router.post(
    "/shifts",
    response_model=StaffMasterData
)
def create_shift(
    shift: StaffMasterCreate,
    db: Session = Depends(get_db)
):
    db_shift = Shift(**shift.model_dump())

    db.add(db_shift)
    db.commit()
    db.refresh(db_shift)

    return db_shift


@router.patch(
    "/shifts/{shift_id}",
    response_model=StaffMasterData
)
def update_shift(
    shift_id: int,
    shift_update: StaffMasterUpdate,
    db: Session = Depends(get_db)
):
    shift = db.query(Shift).filter(
        Shift.id == shift_id
    ).first()

    if not shift:
        raise HTTPException(
            status_code=404,
            detail="Shift not found"
        )

    update_data = shift_update.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(shift, field, value)

    db.commit()
    db.refresh(shift)

    return shift


@router.delete("/shifts/{shift_id}")
def delete_shift(
    shift_id: int,
    db: Session = Depends(get_db)
):
    shift = db.query(Shift).filter(
        Shift.id == shift_id
    ).first()

    if not shift:
        raise HTTPException(
            status_code=404,
            detail="Shift not found"
        )

    db.delete(shift)
    db.commit()

    return {
        "message": "Shift deleted successfully"
    }

@router.get(
    "/staffs",
    response_model=list[StaffsData]
)
def get_staffs(
    db: Session = Depends(get_db),
    owner :int = Depends(get_current_owner)
):
    Staff_ids = db.query(Staff).all()
    res = []
    for staff in Staff_ids:
        res.append({
            "id": staff.id,
            "name": staff.name,
            "mobile": staff.mobile,
            "salary": staff.salary,
            "work_type": db.query(WorkType).filter(WorkType.id == staff.work_type_id).first(),
            "status": db.query(Status).filter(Status.id == staff.status_id).first(),
            "shift": db.query(Shift).filter(Shift.id == staff.shift_id).first(),
            "hostel_id": staff.hostel_id,
            "owner_id": staff.owner_id
        })   
    return res



@router.get(
    "/{staff_id}",
    response_model=StaffsData
)
def get_staff(
    staff_id: int,
    db: Session = Depends(get_db),
     owner :int = Depends(get_current_owner)
):
    staff = db.query(Staff).filter(
        Staff.id == staff_id
    ).first()

    if not staff:
        raise HTTPException(
            status_code=404,
            detail="Staff not found"
        )

    return staff


@router.post(
    "/create",
    response_model=StaffsData
)
def create_staff(
    staff: StaffCreate,
    db: Session = Depends(get_db),
    owner :int = Depends(get_current_owner)
):
    db_staff = Staff(**staff.model_dump())

    db.add(db_staff)
    db.commit()
    db.refresh(db_staff)

    return db_staff


@router.patch(
    "/{staff_id}",
    response_model=StaffsData
)
def update_staff(
    staff_id: int,
    staff_update: StaffUpdate,
    db: Session = Depends(get_db),
    owner :int = Depends(get_current_owner)
):
    staff = db.query(Staff).filter(
        Staff.id == staff_id
    ).first()

    if not staff:
        raise HTTPException(
            status_code=404,
            detail="Staff not found"
        )

    update_data = staff_update.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(staff, field, value)

    db.commit()
    db.refresh(staff)

    return staff


@router.delete("/{staff_id}")
def delete_staff(
    staff_id: int,
    db: Session = Depends(get_db),
    owner :int = Depends(get_current_owner)
):
    staff = db.query(Staff).filter(
        Staff.id == staff_id
    ).first()

    if not staff:
        raise HTTPException(
            status_code=404,
            detail="Staff not found"
        )

    db.delete(staff)
    db.commit()

    return {
        "message": "Staff deleted successfully"
    }