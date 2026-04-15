from datetime import timedelta
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, logger, status, Request
from requests import session
from sqlalchemy.orm import Session

from core.database import get_db
from modules.owner import services
from modules.owner.models import Owner, Hostel, Room, Tenant, TenantPayment
from modules.owner.schemas import (
    OTPRequest, OTPVerify, OTPResponse, LoginResponse,
    HostelCreate, HostelUpdate, HostelOut, OwnerCreate, OwnerUpdate, OwnerOut, OwnerdetailHostelRoomOut,
    RoomCreate, RoomUpdate, RoomOut,
    TenantCreate, TenantUpdate, TenantOut,
    TenantPaymentCreate, TenantPaymentUpdate, TenantPaymentOut
)
from modules.owner.security import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_owner



auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
router = APIRouter(prefix="/owner", tags=["Owner"])

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

@router.get("/hostels/{hostel_id}/rooms", response_model=List[RoomOut], tags=["Rooms"])
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
    db_room = Room(**room.model_dump())
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    return db_room


@router.get("/rooms/{room_id}", response_model=RoomOut, tags=["Rooms"])
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
    for field, value in update_data.items():
        setattr(room, field, value)
    db.commit()
    db.refresh(room)
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


# Include auth router
router.include_router(auth_router)



