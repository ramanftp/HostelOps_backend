from datetime import datetime, timedelta
import logging
import os
import re
import shutil
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from requests import session
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from modules.owner import services
from modules.owner.models import Owner, Hostel, Room, RoomType, Tenant, TenantPayment
from modules.owner.schemas import (
    OTPRequest, OTPVerify, OTPResponse, LoginResponse,
    HostelCreate, HostelUpdate, HostelOut, OwnerCreate, OwnerUpdate, OwnerOut, OwnerdetailHostelRoomOut,
    RoomCreate, RoomHostelImgOut, RoomTypeSchema, RoomTypeCreate, RoomTypeUpdate, RoomUpdate, RoomOut,
    TenantCreate, TenantUpdate, TenantOut,
    TenantPaymentCreate, TenantPaymentUpdate, TenantPaymentOut, AadhaarData
)
from modules.owner.security import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_owner



auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
router = APIRouter(prefix="/owner", tags=["Owner"])


room_types = {  
    "1": "Single Room",
    "2": "2 Share Room",
    "3": "3 Share Room",
    "4": "4 Share Room",
    "5": "5 Share Room",
    "flat": "Flat",
    "rental": "Rental",
    "other": "Other"
}

logger = logging.getLogger(__name__)
# Helper function for error handling
def handle_service_error(db: Session, func, *args, **kwargs):
    """Helper function to handle service errors"""
    try:
        result = func(*args, **kwargs)
        db.commit()
        return result
    except services.UserNotFoundError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.UserAlreadyExistsError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except services.InvalidOTPError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except services.AccountLockedError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except services.AuthServiceError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


# ============================================================================
# OTP Authentication Endpoints
# ============================================================================

@auth_router.post("/send-otp", response_model=OTPResponse)
def send_otp(
    otp_request: OTPRequest,
    db: Session = Depends(get_db)
):
    """Send OTP to phone number for login/registration"""
    # verify user exists or create a new one (without committing yet)
    # Owner = services.get_user_by_phone(db, otp_request.phone_number)
    # if not Owner:
    #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found. Please register first.")

    result = services.send_otp(
        otp_request.phone_number, 
    )
    return OTPResponse(  
        ok=True,
        message=result["message"],
        expires_in=result["expires_in"]
    )


@auth_router.post("/verify-otp", response_model=LoginResponse)
def verify_otp_and_login(
    otp_verify: OTPVerify,
    request: Request,
    db: Session = Depends(get_db)
):
    """Verify OTP and login/register owner, returning access token"""
    try:
        # Authenticate with OTP
        auth_result = services.authenticate_with_otp(
            db, 
            otp_verify.phone_number, 
            otp_verify.otp,
            request.client.host
        )
        
        owner = auth_result["user"]
        print
        # Create access token
        access_token = create_access_token(
            subject=owner.phone_number,
            extra_data={
                "owner_id": owner.id,
            }
        )
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            owner=owner
        )
        
    except services.InvalidOTPError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except services.AccountLockedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@auth_router.post("/logout")
def logout():
    """Logout user (client should discard token)"""
    return {"message": "Successfully logged out"}


# ============================================================================
# Hostel Management Endpoints
# ============================================================================

@router.get("/room_types", response_model=List[RoomTypeSchema],tags=["Rooms"])
def get_room_types(
    db: Session = Depends(get_db)
):
    room_types = db.query(RoomType).all()
    return room_types
@router.post("/room_types", response_model=RoomTypeSchema, tags=["Rooms"])
def create_room_type(
    room_type: RoomTypeCreate,
    db: Session = Depends(get_db)
):
    db_room_type = RoomType(**room_type.model_dump())
    db.add(db_room_type)
    db.commit()
    db.refresh(db_room_type)
    return db_room_type

@router.patch("/room_types/{room_type_id}", response_model=RoomTypeSchema, tags=["Rooms"])
def update_room_type(
    room_type_id: int,
    room_type_update: RoomTypeUpdate,
    db: Session = Depends(get_db)
):
    room_type = db.query(RoomType).filter(RoomType.id == room_type_id).first()
    if not room_type:
        raise HTTPException(status_code=404, detail="Room type not found")
    update_data = room_type_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(room_type, field, value)
    db.commit()
    db.refresh(room_type)
    return room_type

@router.delete("/room_types/{room_type_id}", tags=["Rooms"])
def delete_room_type(
    room_type_id: int,
    db: Session = Depends(get_db)
):
    room_type = db.query(RoomType).filter(RoomType.id == room_type_id).first()
    if not room_type:
        raise HTTPException(status_code=404, detail="Room type not found")
    db.delete(room_type)
    db.commit()
    return {"message": "Room type deleted successfully"}


@router.post("/register", response_model=OwnerOut, tags=["Owner"])
def register_owner(
    owner_create: OwnerCreate,
    db: Session = Depends(get_db)
):
    """Register a new owner"""
    result = handle_service_error(db, services.register_owner, db, owner_create)
    return result


@router.get("/owners", response_model=List[OwnerOut], tags=["Owner"])
def get_owners(
    db: Session = Depends(get_db)
):
    """Get all owners"""
    owners = db.query(Owner).all()
    return owners

@router.get("/owners/{owner_id}", response_model=OwnerdetailHostelRoomOut, tags=["Owner"])
def get_owner(
    owner_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific owner by ID"""
    owner = db.query(Owner).filter(Owner.id == owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    return owner


@router.put("/owners/{owner_id}", response_model=OwnerOut, tags=["Owner"])
def update_owner(
    owner_id: int,
    owner_update: OwnerUpdate,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Update owner profile"""
    if current_owner["id"] != owner_id:
        raise HTTPException(status_code=403, detail="Cannot update other owner's profile")
    
    owner = db.query(Owner).filter(Owner.id == owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    
    update_data = owner_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(owner, field, value)
    db.commit()
    db.refresh(owner)
    return owner


@router.get("/hostels", response_model=List[HostelOut], tags=["Hostels"])
def get_hostels(
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Get all hostels for the current owner"""
    hostels = db.query(Hostel).filter(Hostel.owner_id == current_owner["id"]).all()
    
    # Populate room_type_name for each room
    for hostel in hostels:
        for room in hostel.rooms:
            if room.room_type_rel:
                room.room_type_name = room.room_type_rel.name
    
    return hostels


@router.post("/hostels", response_model=HostelOut, tags=["Hostels"])
def create_hostel(
    hostel: HostelCreate,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Create a new hostel"""
    db_hostel = services.create_hostel(db, hostel, current_owner["id"])
    return db_hostel


@router.get("/hostels/{hostel_id}", response_model=HostelOut, tags=["Hostels"])
def get_hostel(
    hostel_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Get a specific hostel"""
    hostel = db.query(Hostel).filter(
        Hostel.id == hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Hostel not found")
    return hostel


@router.put("/hostels/{hostel_id}", response_model=HostelOut, tags=["Hostels"])
def update_hostel(
    hostel_id: int,
    hostel_update: HostelUpdate,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Update a hostel"""
    hostel = db.query(Hostel).filter(
        Hostel.id == hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Hostel not found")
    update_data = hostel_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(hostel, field, value)
    db.commit()
    db.refresh(hostel)
    return hostel


@router.patch("/hostels/{hostel_id}", response_model=HostelOut, tags=["Hostels"])
def partial_update_hostel(
    hostel_id: int,
    hostel_update: HostelUpdate,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Partially update a hostel"""
    hostel = db.query(Hostel).filter(
        Hostel.id == hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Hostel not found")
    update_data = hostel_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(hostel, field, value)
    db.commit()
    db.refresh(hostel)
    return hostel


@router.delete("/hostels/{hostel_id}", tags=["Hostels"])
def delete_hostel(
    hostel_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Delete a hostel"""
    hostel = db.query(Hostel).filter(
        Hostel.id == hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Hostel not found")
    db.delete(hostel)
    db.commit()
    return {"message": "Hostel deleted successfully"}


# ============================================================================
# Room Management Endpoints
# ============================================================================

@router.get("/hostels/{hostel_id}/rooms", response_model=List[RoomHostelImgOut], tags=["Rooms"])
def get_rooms(
    hostel_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Get all rooms for a hostel"""
    # First check if hostel belongs to owner
    hostel = db.query(Hostel).filter(
        Hostel.id == hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Hostel not found")
    rooms = db.query(Room).filter(Room.hostel_id == hostel_id).all()
    
    # Populate room_type_name for each room
    for room in rooms:
        if room.room_type_rel:
            room.room_type_name = room.room_type_rel.name
    
    return rooms


@router.post("/hostels/{hostel_id}/rooms", response_model=RoomOut, tags=["Rooms"])
def create_room(
    hostel_id: int,
    room: RoomCreate,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Create a new room in a hostel"""
    # Check if hostel belongs to owner
    hostel = db.query(Hostel).filter(
        Hostel.id == hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Hostel not found")
    if room.hostel_id != hostel_id:
        raise HTTPException(status_code=400, detail="Hostel ID mismatch")
    
    # Convert room type name to ID if provided
    room_type_id = None
    if room.room_type:
        room_type_obj = db.query(RoomType).filter(RoomType.name == room.room_type).first()
        if not room_type_obj:
            raise HTTPException(status_code=400, detail=f"Room type '{room.room_type}' not found")
        room_type_id = room_type_obj.id
    
    # Create room data without room_type field, then add the ID
    room_data = room.model_dump()
    room_data.pop('room_type', None)  # Remove the string room_type
    room_data['room_type'] = room_type_id  # Add the integer room_type_id
    
    db_room = Room(**room_data)
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    
    # Populate room_type_name for response
    if db_room.room_type_rel:
        db_room.room_type_name = db_room.room_type_rel.name
    
    return db_room


@router.get("/rooms/{room_id}", response_model=RoomHostelImgOut, tags=["Rooms"])
def get_room(
    room_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Get a specific room"""
    room = db.query(Room).join(Hostel).filter(
        Room.id == room_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Populate room_type_name
    if room.room_type_rel:
        room.room_type_name = room.room_type_rel.name
    
    return room


@router.put("/rooms/{room_id}", response_model=RoomOut, tags=["Rooms"])
def update_room(
    room_id: int,
    room_update: RoomUpdate,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Update a room"""
    room = db.query(Room).join(Hostel).filter(
        Room.id == room_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    update_data = room_update.model_dump(exclude_unset=True)
    
    # Handle room_type conversion if provided
    if 'room_type' in update_data:
        room_type_name = update_data.pop('room_type')  # Remove the string
        if room_type_name:
            room_type_obj = db.query(RoomType).filter(RoomType.name == room_type_name).first()
            if not room_type_obj:
                raise HTTPException(status_code=400, detail=f"Room type '{room_type_name}' not found")
            update_data['room_type'] = room_type_obj.id  # Add the integer ID
    
    for field, value in update_data.items():
        setattr(room, field, value)
    db.commit()
    db.refresh(room)
    
    # Populate room_type_name for response
    if room.room_type_rel:
        room.room_type_name = room.room_type_rel.name
    
    return room


@router.delete("/rooms/{room_id}", tags=["Rooms"])
def delete_room(
    room_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Delete a room"""
    room = db.query(Room).join(Hostel).filter(
        Room.id == room_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    db.delete(room)
    db.commit()
    return {"message": "Room deleted successfully"}


@router.get("/tenants", response_model=List[TenantOut], tags=["Tenants"])
def get_tenants(
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Get all tenants for the current owner"""
    tenants = db.query(Tenant).join(Hostel).filter(Hostel.owner_id == current_owner["id"]).all()
    return tenants


@router.get("/hostels/{hostel_id}/tenants", response_model=List[TenantOut], tags=["Tenants"])
def get_tenants_by_hostel(
    hostel_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Get all tenants for a specific hostel"""
    hostel = db.query(Hostel).filter(
        Hostel.id == hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Hostel not found")
    tenants = db.query(Tenant).filter(Tenant.hostel_id == hostel_id).all()
    return tenants


@router.post("/hostels/{hostel_id}/tenants", response_model=TenantOut, tags=["Tenants"])
def create_tenant(
    hostel_id: int,
    tenant: TenantCreate,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Create a new tenant for a hostel"""
    hostel = db.query(Hostel).filter(
        Hostel.id == hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Hostel not found")
    if tenant.room_id is not None:
        room = db.query(Room).filter(
            Room.id == tenant.room_id,
            Room.hostel_id == hostel_id
        ).first()
        if not room:
            raise HTTPException(status_code=404, detail="Room not found in hostel")
    db_tenant = Tenant(**tenant.model_dump(), hostel_id=hostel_id)
    db.add(db_tenant)
    db.commit()
    db.refresh(db_tenant)
    return db_tenant


@router.post("/aadhaar-extract", response_model=AadhaarData, tags=["Tenants"])
def extract_aadhaar_data(
    front: UploadFile = File(...),
    back: UploadFile = File(...),
    current_owner: dict = Depends(get_current_owner)
):
    """Extract data from Aadhaar card (front + back)"""

    # Validate file types
    if not front.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Front must be an image")
    if not back.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Back must be an image")

    upload_dir = settings.aadhaar_image_dir
    os.makedirs(upload_dir, exist_ok=True)

    # Generate filenames
    def save_file(file: UploadFile):
        safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", file.filename)
        filename = f"_aadhaar_{uuid.uuid4().hex}_{safe_name}"
        path = os.path.join(upload_dir, filename)

        with open(path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return path, filename

    front_path, front_name = save_file(front)
    back_path, back_name = save_file(back)

    try:
        # Process images
        front_data = services.process_aadhaar_image(front_path)
        back_data = services.process_aadhaar_image(back_path)

        # Merge data safely (front priority)
        final_data = {
            "name": front_data.get("name") or back_data.get("name"),
            "aadhar_no": front_data.get("aadhar_no") or back_data.get("aadhar_no"),
            "dob": front_data.get("dob") or back_data.get("dob"),
            "gender": front_data.get("gender") or back_data.get("gender"),
            "address": back_data.get("address") or front_data.get("address"),
        }

        # Single clean return
        return AadhaarData(
            **final_data,
            image_path=f"{settings.aadhaar_image_url}/{front_name}"
        )

    except Exception as e:
        logger.error(f"Aadhaar processing error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process Aadhaar image")


@router.get("/rooms/{room_id}/tenants", response_model=List[TenantOut], tags=["Tenants"])
def get_tenants_by_room(
    room_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Get tenants assigned to a room"""
    room = db.query(Room).join(Hostel).filter(
        Room.id == room_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    tenants = db.query(Tenant).filter(Tenant.room_id == room_id).all()
    return tenants


@router.get("/tenants/{tenant_id}", response_model=TenantOut, tags=["Tenants"])
def get_tenant(
    tenant_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Get a specific tenant"""
    tenant = db.query(Tenant).join(Hostel).filter(
        Tenant.id == tenant_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.put("/tenants/{tenant_id}", response_model=TenantOut, tags=["Tenants"])
def update_tenant(
    tenant_id: int,
    tenant_update: TenantUpdate,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Update a tenant"""
    tenant = db.query(Tenant).join(Hostel).filter(
        Tenant.id == tenant_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    update_data = tenant_update.model_dump(exclude_unset=True)
    if update_data.get("room_id") is not None:
        room = db.query(Room).filter(
            Room.id == update_data["room_id"],
            Room.hostel_id == tenant.hostel_id
        ).first()
        if not room:
            raise HTTPException(status_code=404, detail="Room not found in hostel")
    for field, value in update_data.items():
        setattr(tenant, field, value)
    db.commit()
    db.refresh(tenant)
    return tenant


@router.delete("/tenants/{tenant_id}", tags=["Tenants"])
def delete_tenant(
    tenant_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Delete a tenant"""
    tenant = db.query(Tenant).join(Hostel).filter(
        Tenant.id == tenant_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    db.delete(tenant)
    db.commit()
    return {"message": "Tenant deleted successfully"}


# ============================================================================
# Tenant Payment Management Endpoints
# ============================================================================

@router.get("/tenants/{tenant_id}/payments", response_model=List[TenantPaymentOut], tags=["Payments"])
def get_tenant_payments(
    tenant_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Get all payments for a tenant"""
    tenant = db.query(Tenant).join(Hostel).filter(
        Tenant.id == tenant_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    payments = db.query(TenantPayment).filter(TenantPayment.tenant_id == tenant_id).all()
    return payments


@router.post("/tenants/{tenant_id}/payments", response_model=TenantPaymentOut, tags=["Payments"])
def create_tenant_payment(
    tenant_id: int,
    payment: TenantPaymentCreate,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Create a payment for a tenant"""
    tenant = db.query(Tenant).join(Hostel).filter(
        Tenant.id == tenant_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if payment.tenant_id != tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID mismatch")
    
    db_payment = TenantPayment(**payment.model_dump())
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment


@router.get("/payments/{payment_id}", response_model=TenantPaymentOut, tags=["Payments"])
def get_payment(
    payment_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Get a specific payment"""
    payment = db.query(TenantPayment).join(Tenant).join(Hostel).filter(
        TenantPayment.id == payment_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.get("/payments/{payment_id}/slip", response_class=HTMLResponse, tags=["Payments"])
def get_payment_slip(
    payment_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Return a printable payment slip HTML page"""
    payment = db.query(TenantPayment).join(Tenant).join(Hostel).filter(
        TenantPayment.id == payment_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    tenant = payment.tenant
    hostel = tenant.hostel
    payment_date = payment.payment_date.strftime("%Y-%m-%d %H:%M:%S") if payment.payment_date else "N/A"
    html = f"""
    <!DOCTYPE html>
    <html lang=\"en\">
    <head>
      <meta charset=\"UTF-8\" />
      <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
      <title>Payment Slip</title>
      <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f6f6f6; }}
        .container {{ max-width: 800px; margin: 24px auto; padding: 24px; background: #fff; border-radius: 8px; box-shadow: 0 0 20px rgba(0,0,0,0.08); }}
        .header {{ text-align: center; margin-bottom: 20px; }}
        .header h1 {{ margin: 0; font-size: 28px; }}
        .header p {{ margin: 4px 0; color: #555; }}
        .details, .footer {{ margin-top: 20px; }}
        .details table {{ width: 100%; border-collapse: collapse; }}
        .details th, .details td {{ padding: 10px 12px; border: 1px solid #ddd; text-align: left; }}
        .details th {{ background: #f0f0f0; }}
        .summary {{ margin-top: 24px; padding: 16px; background: #f9f9f9; border-radius: 6px; }}
        .print-button {{ display: inline-block; margin-top: 20px; padding: 10px 18px; background: #2d7cff; color: #fff; text-decoration: none; border-radius: 4px; }}
        @media print {{
          .print-button {{ display: none; }}
          body {{ background: #fff; }}
        }}
      </style>
    </head>
    <body>
      <div class=\"container\">
        <div class=\"header\">
          <h1>Payment Slip</h1>
          <p>Payment ID: {payment.id}</p>
          <p>Date: {payment_date}</p>
        </div>
        <div class=\"details\">
          <table>
            <tr><th>Field</th><th>Details</th></tr>
            <tr><td>Tenant Name</td><td>{tenant.name if tenant else 'N/A'}</td></tr>
            <tr><td>Tenant Phone</td><td>{tenant.phone_number if tenant else 'N/A'}</td></tr>
            <tr><td>Hostel</td><td>{hostel.name if hostel else 'N/A'}</td></tr>
            <tr><td>Payment Amount</td><td>₹{payment.amount}</td></tr>
            <tr><td>Payment Method</td><td>{payment.payment_method or 'N/A'}</td></tr>
            <tr><td>Transaction ID</td><td>{payment.transaction_id or 'N/A'}</td></tr>
            <tr><td>Payment Status</td><td>Completed</td></tr>
          </table>
        </div>
        <div class=\"summary\">
          <h2>Payment Summary</h2>
          <p>This slip confirms receipt of payment from the tenant for the current billing cycle.</p>
          <p>For any questions, contact the hostel administrator.</p>
        </div>
        <div class=\"footer\">
          <a href=\"#\" class=\"print-button\" onclick=\"window.print(); return false;\">Print Slip</a>
        </div>
      </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.put("/payments/{payment_id}", response_model=TenantPaymentOut, tags=["Payments"])
def update_payment(
    payment_id: int,
    payment_update: TenantPaymentUpdate,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Update a payment"""
    payment = db.query(TenantPayment).join(Tenant).join(Hostel).filter(
        TenantPayment.id == payment_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    update_data = payment_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(payment, field, value)
    db.commit()
    db.refresh(payment)
    return payment


@router.delete("/payments/{payment_id}", tags=["Payments"])
def delete_payment(
    payment_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Delete a payment"""
    payment = db.query(TenantPayment).join(Tenant).join(Hostel).filter(
        TenantPayment.id == payment_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    db.delete(payment)
    db.commit()
    return {"message": "Payment deleted successfully"}

@router.get("/dashboard", tags=["Dashboard"])
def get_dashboard_data(
    hostel_id: int | None = None,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """Get dashboard data for the owner"""

    if hostel_id:
        hostel = db.query(Hostel).filter(
            Hostel.id == hostel_id,
            Hostel.owner_id == current_owner["id"]
        ).first()

        if not hostel:
            raise HTTPException(status_code=404, detail="Hostel not found")

        room_filter = Room.hostel_id == hostel_id
        tenant_filter = Tenant.hostel_id == hostel_id

    else:
        # 🔥 IMPORTANT: filter by owner (you missed this earlier)
        hostel_ids = db.query(Hostel.id).filter(
            Hostel.owner_id == current_owner["id"]
        )

        room_filter = Room.hostel_id.in_(hostel_ids)
        tenant_filter = Tenant.hostel_id.in_(hostel_ids)

    rooms_count = db.query(Room).filter(room_filter).count() or 0
    bed_count = db.query(func.sum(Room.no_of_beds)).filter(room_filter).scalar() or 0
    tenants_count = db.query(Tenant).filter(tenant_filter).count() or 0
    total_amount = db.query(func.sum(Tenant.rent)).filter(tenant_filter).scalar() or 0
    total_payments = db.query(func.sum(TenantPayment.amount))\
        .join(Tenant)\
        .filter(tenant_filter)\
        .scalar() or 0

    payment_due = total_amount - total_payments

    return {
        "rooms_count": rooms_count,
        "bed_count": bed_count,
        "tenants_count": tenants_count,
        "vacant_beds": bed_count - tenants_count,
        "total_amount": total_amount,
        "total_payments": total_payments,
        "payment_due": payment_due
    }

# Include auth router
# router.include_router(auth_router)



