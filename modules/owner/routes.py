from datetime import datetime, timedelta
import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Body
from fastapi.responses import HTMLResponse
from pydantic import Json
from requests import session
from sqlalchemy import JSON, Transaction, and_, func
from sqlalchemy.orm import Query, Session

from core.config import settings
from core.database import get_db
from modules.bill_payment.schema import BillOut
from modules.owner import services
from modules.owner.models import Category, Facility, HouseRules, Owner, Hostel, Policies, Room, RoomType, Tenant, Manager
from modules.bill_payment.models import Bill, Transaction as BillTransaction
from modules.expenses.models import Expense
from modules.owner.schemas import (
    CategoryCreate, CategoryOut, CategoryUpdate, FacilityCreate, FacilityOut, HouseRuleCreate, HouseRuleOut, HouseRuleUpdate, HouseRuleUpdate, ManagerCreate, ManagerOut, ManagerUpdate, OTPRequest, OTPVerify, OTPResponse, LoginResponse,
    HostelCreate, HostelUpdate, HostelOut, OwnerCreate, OwnerUpdate, OwnerOut, OwnerdetailHostelRoomOut, PolicyCreate, PolicyOut, PolicyUpdate,
    RoomCreate, RoomHostelImgOut, RoomTypeSchema, RoomTypeCreate, RoomTypeUpdate, RoomUpdate, RoomOut,
    TenantCreate, TenantUpdate, TenantOut, AadhaarData
)
from modules.owner.security import create_access_token, ACCESS_TOKEN_EXPIRE, get_current_owner, get_current_manager
from modules.subcriptions.models import Subscriptions, Plan
from modules.subcriptions.schema import SubscriptionBase



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
    """Send OTP to phone number for login"""
    # verify user exists
    manager = services.get_manager_by_phone(db, otp_request.phone_number)
    Owner = services.get_owner_by_phone(db, otp_request.phone_number)
    if not Owner and not manager:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found. Please register first.")
    
    result = services.send_otp(
        otp_request.phone_number,
        purpose="login"
    )
    return OTPResponse(  
        ok=True,
        message=result["message"],
        expires_in=result["expires_in"],
        debug_otp=result.get("debug_otp"),
        sms_sent=result.get("sms_sent")
    )






@auth_router.post("/verify-otp")
def verify_otp_and_login(
    otp_verify: OTPVerify,
    request: Request,
    db: Session = Depends(get_db)
):
    """Verify OTP and login/register owner, returning access token"""
    try:
        # owner = db.query(Owner).filter(Owner.phone_number == otp_verify.phone_number).first()

        # Authenticate with OTP
        auth_result = services.authenticate_with_otp(
            db, 
            otp_verify.phone_number, 
            otp_verify.otp,
            request.client.host
        )
        manager = db.query(Manager).filter(Manager.phone_number == otp_verify.phone_number).first()
        if manager:
            owner = db.query(Owner).filter(Owner.id == manager.owner_id).first()
        else:
            owner = auth_result["user"]
        
        # Create access token
        if manager:
            access_token = create_access_token(
                subject=manager.phone_number,
                extra_data={
                    "owner_id": manager.owner_id,
                    "manager_id": manager.id
                }
            )
        else:
            access_token = create_access_token(
                subject=owner.phone_number,
                extra_data={
                    "owner_id": owner.id,
                }
            )
        subscription = owner.subscriptions[0] if owner.subscriptions else None,
        plan_id = subscription[0].plan_id if subscription else 5
        plan = db.query(Plan).filter(Plan.id == plan_id).first() 
        if manager:
            managers = [manager]
        else:    
            managers = db.query(Manager).filter(Manager.owner_id == owner.id).all()
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE * 24 * 60,
            "owner": owner,
            "subscription": subscription,
            "plan": plan,
            "is_manager": bool(manager),
            "managers": managers
        }
        
    except services.InvalidOTPError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except services.UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
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

@router.get("/categories", response_model=List[CategoryOut], tags=["Hostels"])
def get_categories(
    db: Session = Depends(get_db)
):
    categories = db.query(Category).all()
    return categories

@router.post("/categories", response_model=CategoryOut, tags=["Hostels"])
def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db)
):
    db_category = Category(**category.model_dump())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category
@router.patch("/categories/{category_id}", response_model=CategoryOut, tags=["Hostels"])
def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    db: Session = Depends(get_db)
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    update_data = category_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category

@router.delete("/categories/{category_id}", tags=["Hostels"])
def delete_category(
    category_id: int,
    db: Session = Depends(get_db)
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(category)
    db.commit()
    return {"message": "Category deleted successfully"}

@router.get("/house_rules", response_model=List[HouseRuleOut], tags=["Hostels"])
def get_house_rules(
    db: Session = Depends(get_db)
):
    house_rules = db.query(HouseRules).all()
    return house_rules

@router.post("/house_rules", response_model=HouseRuleOut, tags=["Hostels"])
def create_house_rule(
    house_rule: HouseRuleCreate,
    db: Session = Depends(get_db)
):
    db_house_rule = HouseRules(**house_rule.model_dump())
    db.add(db_house_rule)
    db.commit()
    db.refresh(db_house_rule)
    return db_house_rule

@router.patch("/house_rules/{house_rule_id}", response_model=HouseRuleOut, tags=["Hostels"])
def update_house_rule(
    house_rule_id: int,
    house_rule_update: HouseRuleUpdate,
    db: Session = Depends(get_db)
):
    house_rule = db.query(HouseRules).filter(HouseRules.id == house_rule_id).first()
    if not house_rule:
        raise HTTPException(status_code=404, detail="House rule not found")
    update_data = house_rule_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(house_rule, field, value)
    db.commit()
    db.refresh(house_rule)
    return house_rule

@router.delete("/house_rules/{house_rule_id}", tags=["Hostels"])
def delete_house_rule(
    house_rule_id: int,
    db: Session = Depends(get_db)
):
    house_rule = db.query(HouseRules).filter(HouseRules.id == house_rule_id).first()
    if not house_rule:
        raise HTTPException(status_code=404, detail="House rule not found")
    db.delete(house_rule)
    db.commit()
    return {"message": "House rule deleted successfully"}

@router.get("/policies", response_model=List[PolicyOut], tags=["Hostels"])
def get_policies(
    db: Session = Depends(get_db)
):
    policies = db.query(Policies).all()
    return policies
@router.post("/policies", response_model=PolicyOut, tags=["Hostels"])
def create_policy(
    policy: PolicyCreate,
    db: Session = Depends(get_db)
):
    db_policy = Policies(**policy.model_dump())
    db.add(db_policy)
    db.commit()
    db.refresh(db_policy)
    return db_policy

@router.patch("/policies/{policy_id}", response_model=PolicyOut, tags=["Hostels"])
def update_policy(
    policy_id: int,
    policy_update: PolicyUpdate,
    db: Session = Depends(get_db)
):
    policy = db.query(Policies).filter(Policies.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    update_data = policy_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(policy, field, value)
    db.commit()
    db.refresh(policy)
    return policy
@router.delete("/policies/{policy_id}", tags=["Hostels"])
def delete_policy(
    policy_id: int,
    db: Session = Depends(get_db)
):
    policy = db.query(Policies).filter(Policies.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    db.delete(policy)
    db.commit()
    return {"message": "Policy deleted successfully"}

@router.post("/register", tags=["Owner"])
def register_owner(
    owner_create: OwnerCreate,
    db: Session = Depends(get_db)
):
    """Register a new owner with OTP verification and auto-login"""
    owner = handle_service_error(db, services.register_owner, db, owner_create)
    
  
    from modules.subcriptions.services import create_subscription
    from modules.subcriptions.routes import get_plans, get_subscription_details
    subscription = get_subscription_details(owner_create.subscription_id)
    db_subscription = create_subscription(subscription, owner.id)
    owner.subscription_id = db_subscription.id
    db.commit()

    
    return {
        "owner": owner
    }

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


@router.post("/hostels", response_model=HostelOut, tags=["Hostels"], status_code=status.HTTP_201_CREATED)
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


@router.delete("/hostels/{hostel_id}", tags=["Hostels"], status_code=status.HTTP_204_NO_CONTENT)
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
    tenants = db.query(Tenant).filter(Tenant.hostel_id == hostel_id, Tenant.active == True).all()
    if tenants:
        raise HTTPException(status_code=400, detail="Cannot delete hostel with active tenants")
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
        room_type_obj = db.query(RoomType).filter(RoomType.id == room.room_type).first()
        if room_type_obj:
            room_type_id = room_type_obj.id
        else:
            room_type_id = db.query(RoomType).first()    
    
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
    tenants = db.query(Tenant).join(Hostel).filter(Hostel.owner_id == current_owner["id"], Tenant.active == True).all()
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
    tenants = db.query(Tenant).filter(Tenant.hostel_id == hostel_id, Tenant.active == True).all()
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

    room = db.query(Room).filter(
            Room.id == tenant.room_id,
            Room.hostel_id == hostel_id
        ).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found in hostel")
    db_tenant = Tenant(**tenant.model_dump(exclude={'hostel_id'}), hostel_id=hostel_id)
    db.add(db_tenant)
    db.commit()
    db.refresh(db_tenant)
    create_bill = services.create_bill_for_new_tenant(db, db_tenant)
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

    try:
        # Read file contents
        front_content = front.file.read()
        back_content = back.file.read()

        # Process images directly from bytes
        front_data = services.process_aadhaar_image_bytes(front_content)
        back_data = services.process_aadhaar_image_bytes(back_content)

        # Merge data safely (front priority)
        final_data = {
            "name": front_data.get("name"),
            "aadhaar_no": front_data.get("aadhaar_no"),
            "dob": front_data.get("dob"),
            "gender": front_data.get("gender"),
            "address": back_data.get("address"),
        }

        # Single clean return
        return AadhaarData(**final_data)

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
    tenants = db.query(Tenant).filter(Tenant.room_id == room_id,Tenant.active == True).all()
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
        Tenant.active == True,
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
        Tenant.active == True,
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
    tenant.active = False  # Soft delete by marking as inactive
    db.commit()
    return {"message": "Tenant deleted successfully"}


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
        expense_filter = Expense.hostel_id == hostel_id

    else:
        hostel_ids = db.query(Hostel.id).filter(
            Hostel.owner_id == current_owner["id"]
        )

        room_filter = Room.hostel_id.in_(hostel_ids)
        tenant_filter =  and_(
        Tenant.hostel_id.in_(hostel_ids),
        Tenant.active.is_(True)
    )
        expense_filter = Expense.hostel_id.in_(hostel_ids)

    # Filter expenses by owner
    expense_filter = expense_filter & (Expense.created_by == current_owner["id"])

    rooms_count = db.query(Room).filter(room_filter).count() or 0
    bed_count = db.query(func.sum(Room.no_of_beds)).filter(room_filter).scalar() or 0
    tenants_count = db.query(Tenant).filter(tenant_filter).count() or 0
    if not hostel_id:
        total_amount = db.query(func.sum(Bill.amount)).filter(Bill.status != "paid", Bill.hostel_id.in_(hostel_ids)).scalar() or 0
    else:
        total_amount = db.query(func.sum(Bill.amount)).filter(Bill.status != "paid", Bill.hostel_id == hostel_id).scalar() or 0
    total_payments = db.query(func.sum(BillTransaction.amount))\
        .join(Tenant)\
        .filter(tenant_filter)\
        .scalar() or 0
    total_expenses = db.query(func.sum(Expense.amount)).filter(expense_filter).scalar() or 0

    payment_due = total_amount - total_payments

    return {
        "rooms_count": rooms_count,
        "bed_count": bed_count,
        "tenants_count": tenants_count,
        "vacant_beds": bed_count - tenants_count,
        "total_amount": total_amount,
        "total_payments": total_payments,
        "total_expenses": total_expenses,
        "payment_due": payment_due
    }

# ============================================================================
# Image Upload Endpoints
# ============================================================================

import os
import shutil
import uuid

from core.config import settings

# Ensure upload directories exist
os.makedirs(settings.owner_image_dir, exist_ok=True)
os.makedirs(settings.tenant_image_dir, exist_ok=True)
os.makedirs(settings.hostel_image_dir, exist_ok=True)

# Also ensure old uploads directory exists for backward compatibility
os.makedirs("uploads", exist_ok=True)

@router.post("/upload-photo", tags=["Uploads"])
async def upload_photo(
    file: UploadFile = File(...),
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Upload a photo for the current owner"""
    owner_id = current_owner["id"]
    
    owner = db.query(Owner).filter(Owner.id == owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(settings.owner_image_dir, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    url = f"{settings.owner_image_url}/{unique_filename}"
    owner.photo_url = url

    db.commit()
    db.refresh(owner)

    return {"url": url, "message": "Photo uploaded successfully"}


@router.post("/upload/owner/{owner_id}/photo", tags=["Uploads"])
async def upload_owner_photo(
    owner_id: int,
    file: UploadFile = File(...),
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Upload a single photo for an owner"""
    if current_owner["id"] != owner_id:
        raise HTTPException(status_code=403, detail="Cannot upload photos for other owners")

    owner = db.query(Owner).filter(Owner.id == owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(settings.owner_image_dir, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    url = f"{settings.owner_image_url}/{unique_filename}"
    owner.photo_url = url

    db.commit()
    db.refresh(owner)

    return {"url": url, "message": "Owner photo uploaded successfully"}


@router.post("/upload/tenant/{tenant_id}/photo", tags=["Uploads"])
async def upload_tenant_photo(
    tenant_id: int,
    file: UploadFile = File(...),
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Upload a single photo for a tenant"""
    tenant = db.query(Tenant).join(Hostel).filter(
        Tenant.id == tenant_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(settings.tenant_image_dir, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    url = f"{settings.tenant_image_url}/{unique_filename}"
    tenant.photo_url = url

    db.commit()
    db.refresh(tenant)

    return {"url": url, "message": "Tenant photo uploaded successfully"}


@router.get("/upload/hostel/{hostel_id}/agreement", tags=["Uploads Agreements"])
async def get_agreements(
    hostel_id: int,
    db:Session = Depends(get_db),
    current_owner: dict = Depends(get_current_owner),

):
    owner_id = current_owner["id"]
    hostel = db.query(Hostel).filter(Hostel.id == hostel_id).first()


    return {
        "owner_id": owner_id,
        "rental_agreement": hostel.rental_agreement,
        "police_verification": hostel.police_verification
    }


@router.post("/upload/hostel/agreement", tags=["Uploads Agreements"])
async def upload_agreements(
    db:Session = Depends(get_db),
    police_verification: Optional[UploadFile] = File(None),
    rental_agreement: Optional[UploadFile] = File(None),
    current_owner: dict = Depends(get_current_owner),
):
    """
    Uploads Files and PDF/IMG
    """

    owner_id = current_owner["id"]

    # Get next hostel sequence for this owner
    last_sequence = (
        db.query(func.max(Hostel.hostel_sequence))
        .filter(Hostel.owner_id == owner_id)
        .scalar()
    )

    next_sequence = (last_sequence or 0) + 1
    rent_folder = f"owner/{owner_id}/hostel_{next_sequence}/rental_agreement"
    police_verification_folder = f"owner/{owner_id}/hostel_{next_sequence}/police_verification"
    rent_url = ""
    police_url = ""
    if rental_agreement :
        try:
            ext = os.path.splitext(rental_agreement.filename)[1]
            file_key = f"{rent_folder}/{uuid.uuid4()}{ext}"
            services.s3_client.upload_fileobj(
                Fileobj=rental_agreement.file,
                Bucket=services.BUCKET,
                Key=file_key,
                ExtraArgs={
                    "ContentType": rental_agreement.content_type,
                    "ACL": "public-read",
                },
            )
            rent_url = f"{settings.S3_ENDPOINT_URL}/{services.BUCKET}/{file_key}"
        except Exception as e:
            raise HTTPException(status_code=403, detail="upload file failed")
    if police_verification:
        try:
            ext = os.path.splitext(police_verification.filename)[1]
            file_key = f"{police_verification_folder}/{uuid.uuid4()}{ext}"
            services.s3_client.upload_fileobj(
                Fileobj=police_verification.file,
                Bucket=services.BUCKET,
                Key=file_key,
                ExtraArgs={
                    "ContentType": police_verification.content_type,
                    "ACL": "public-read",
                },
            )
            police_url = f"{settings.S3_ENDPOINT_URL}/{services.BUCKET}/{file_key}"
        except Exception as e:
            raise HTTPException(status_code=403, detail="upload file failed")

    return {
        "message": " uploaded successfully.",
        "police_verification": police_url,
        "rental_agreement":rent_url
    }

@router.delete("/upload/hostel/{hostel_id}/rental_agreement", tags=["Uploads Agreements"])
async def delete_rental_agreement(
    hostel_id: int,
    db:Session = Depends(get_db),
    current_owner: dict = Depends(get_current_owner),
):
    """
    Delete one photo.
    """
    hostel = db.query(Hostel).filter(Hostel.owner_id == current_owner['id']).filter(Hostel.hostel_id == hostel_id).first()

    key = hostel.rental_agreement.split(f"{services.BUCKET}/")[1]

    services.s3_client.delete_object(
        Bucket=services.BUCKET,
        Key=key,
    )
    if hostel:
        hostel.rental_agreement = None
    services.check_is_agrement(db, hostel_id)

    return {
        "message": "Rental agreement deleted successfully."
    }


@router.delete("/upload/hostel/{hostel_id}/police_verification", tags=["Uploads Agreements"])
async def delete_police_verification(
    hostel_id: int,
    db:Session = Depends(get_db),
    current_owner: dict = Depends(get_current_owner),
):
    """
    Delete one photo.
    """
    hostel = db.query(Hostel).filter(Hostel.owner_id == current_owner['id']).filter(Hostel.hostel_id == hostel_id).first()

    key = hostel.police_verification.split(f"{services.BUCKET}/")[1]

    services.s3_client.delete_object(
        Bucket=services.BUCKET,
        Key=key,
    )
    if hostel:
        hostel.police_verification = None

    services.check_is_agrement(db, hostel_id)

    return {
        "message": "Police verification deleted successfully."
    }


#UPDATE - Upload More Photos

#DELETE - Delete Single Photo
from pydantic import BaseModel

class DeletePhotoRequest(BaseModel):
    photo_url: str


@router.delete("/upload/hostel/{hostel_sequence}/photo", tags=["Uploads with owner_id"])
async def delete_photo(
    hostel_sequence: int,
    request: DeletePhotoRequest,
    current_owner: dict = Depends(get_current_owner),
):
    """
    Delete one photo.
    """

    key = request.photo_url.split(f"{services.BUCKET}/")[1]

    services.s3_client.delete_object(
        Bucket=services.BUCKET,
        Key=key,
    )

    return {
        "message": "Photo deleted successfully."
    }


#DELETE - Delete All Photos

@router.delete("/upload/hostel/{hostel_sequence}/photos", tags=["Uploads with owner_id"])
async def delete_all_photos(
    hostel_sequence: int,
    current_owner: dict = Depends(get_current_owner),
):
    """
    Delete all hostel photos.
    """

    owner_id = current_owner["id"]

    folder = f"owner/{owner_id}/hostel_{hostel_sequence}/"

    response = services.s3_client.list_objects_v2(
        Bucket=services.BUCKET,
        Prefix=folder,
    )

    if "Contents" not in response:
        return {
            "message": "No photos found."
        }

    objects = []

    for obj in response["Contents"]:
        objects.append({"Key": obj["Key"]})

    services.s3_client.delete_objects(
        Bucket=services.BUCKET,
        Delete={"Objects": objects},
    )

    return {
        "message": "All photos deleted successfully."
    }



@router.post("/upload/hostel/{hostel_sequence}/photos", tags=["Uploads with owner_id"])
async def upload_more_photos(
    hostel_sequence: int,
    files: list[UploadFile] = File(...),
    current_owner: dict = Depends(get_current_owner),
):
    """
    Add more photos to existing hostel folder.
    """

    owner_id = current_owner["id"]

    folder = f"owner/{owner_id}/hostel_{hostel_sequence}"

    urls = []

    for file in files:

        ext = os.path.splitext(file.filename)[1]

        file_key = f"{folder}/{uuid.uuid4()}{ext}"

        services.s3_client.upload_fileobj(
            Fileobj=file.file,
            Bucket=services.BUCKET,
            Key=file_key,
            ExtraArgs={
                "ContentType": file.content_type,
                "ACL": "public-read",
            },
        )

        urls.append(
            f"{settings.S3_ENDPOINT_URL}/{services.BUCKET}/{file_key}"
        )

    return {
        "message": "Photos uploaded successfully.",
        "urls": urls,
    }

#READ - Get All Photos
@router.get("/upload/hostel/{hostel_sequence}/photos", tags=["Uploads with owner_id"])
async def get_hostel_photos(
    hostel_sequence: int,
    current_owner: dict = Depends(get_current_owner),
):
    """
    Get all photos of a hostel.
    """

    # Logged in owner id
    owner_id = current_owner["id"]

    # Hostel folder
    folder = f"owner/{owner_id}/hostel_{hostel_sequence}/"

    # Get all files from S3 folder
    response = services.s3_client.list_objects_v2(
        Bucket=services.BUCKET,
        Prefix=folder,
    )

    photos = []

    # Folder exists
    if "Contents" in response:

        for obj in response["Contents"]:

            photo_url = (
                f"{settings.S3_ENDPOINT_URL}/"
                f"{services.BUCKET}/"
                f"{obj['Key']}"
            )

            photos.append(photo_url)

    return {
        "owner_id": owner_id,
        "hostel_sequence": hostel_sequence,
        "photos": photos,
    }

#CREATE - Upload New Hostel Photos
@router.post("/upload/hostel/photos", tags=["Uploads with owner_id"])
async def upload_hostel_photos(
    files: list[UploadFile] = File(...),
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """
    Upload hostel photos before hostel creation.
    Creates folders like:
        owner/{owner_id}/hostel_1/
        owner/{owner_id}/hostel_2/
        ...
    """

    owner_id = current_owner["id"]

    # Get next hostel sequence for this owner
    last_sequence = (
        db.query(func.max(Hostel.hostel_sequence))
        .filter(Hostel.owner_id == owner_id)
        .scalar()
    )

    next_sequence = (last_sequence or 0) + 1
    folder = f"owner/{owner_id}/hostel_{next_sequence}"

    uploaded_urls = []

    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

    for file in files:
        try:
            ext = os.path.splitext(file.filename)[1].lower()

            # Check file extension
            if ext not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"{file.filename} is not a supported image. Only JPG, JPEG and PNG are allowed."
                )

            # Read file
            contents = await file.read()

            if not contents:
                raise HTTPException(
                    status_code=400,
                    detail=f"{file.filename} is empty."
                )

            # Reset pointer for upload
            file.file.seek(0)

            file_key = f"{folder}/{uuid.uuid4()}{ext}"

            # Set correct Content-Type
            if ext == ".png":
                content_type = "image/png"
            else:
                content_type = "image/jpeg"

            services.s3_client.upload_fileobj(
                Fileobj=file.file,
                Bucket=services.BUCKET,
                Key=file_key,
                ExtraArgs={
                    "ContentType": content_type,
                    "ACL": "public-read",
                },
            )

            file_url = (
                f"{settings.S3_ENDPOINT_URL}/{services.BUCKET}/{file_key}"
            )

            uploaded_urls.append(file_url)

        except HTTPException:
            raise

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload {file.filename}: {str(e)}",
            )

    return {
        "owner_id": owner_id,
        "hostel_sequence": next_sequence,
        "folder": folder,
        "urls": uploaded_urls,
        "message": f"{len(uploaded_urls)} photos uploaded successfully."
    }






@router.post("/upload/hostel/{hostel_id}/photos", tags=["Uploads"])
async def upload_hostel_photos(
    hostel_id: int,
    files: list[UploadFile] = File(...) ,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Upload multiple photos for a hostel"""

    # ✅ Verify hostel ownership
    hostel = db.query(Hostel).filter(
        Hostel.id == hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()

    if not hostel:
        raise HTTPException(status_code=404, detail="Hostel not found")

    urls = []

    for file in files:
        try:
            # ✅ Validate file type
            if not file.content_type.startswith("image/"):
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} must be an image"
                )

            # ✅ Read content to validate size (optional but recommended)
            contents = await file.read()
            if len(contents) == 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} is empty"
                )

            # ✅ Reset pointer after read (CRITICAL)
            file.file.seek(0)

            # ✅ Generate unique file path (organized per hostel)
            file_ext = os.path.splitext(file.filename)[1].lower()
            file_key = f"hostel/{hostel_id}/{uuid.uuid4()}{file_ext}"

            services.s3_client.upload_fileobj(
                Fileobj=file.file,
                Bucket=services.BUCKET,
                Key=file_key,
                ExtraArgs={
                    "ContentType": file.content_type,
                    "ACL": "public-read"
                },
            )


            # ✅ Build correct path-style URL
            file_url = (
                f"{settings.S3_ENDPOINT_URL}/{BUCKET}/{file_key}"
            )

            urls.append(file_url)

        except HTTPException:
            raise

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Upload failed for {file.filename}: {str(e)}"
            )

    # ✅ Append to existing photos array
    if hostel.photos_urls:
        hostel.photos_urls.extend(urls)
    else:
        hostel.photos_urls = urls

    db.commit()
    db.refresh(hostel)

    return {
        "urls": urls,
        "message": f"Uploaded {len(urls)} photos successfully"
    }



@router.delete("/upload/hostel/{hostel_id}/photos", tags=["Uploads"])
def delete_hostel_photos(
    hostel_id: int,
    photo_urls: List[str] = Body(...),
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Delete one or more hostel photos and remove them from storage"""
    hostel = db.query(Hostel).filter(
        Hostel.id == hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Hostel not found")

    if not hostel.photos_urls:
        raise HTTPException(status_code=400, detail="Hostel has no photos to delete")

    deleted_urls = []
    remaining_urls = []

    for url in hostel.photos_urls:
        if url in photo_urls:
            filename = os.path.basename(url)
            if filename:
                file_path = os.path.join(settings.hostel_image_dir, filename)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        deleted_urls.append(url)
                    except OSError:
                        remaining_urls.append(url)
                else:
                    deleted_urls.append(url)
        else:
            remaining_urls.append(url)

    hostel.photos_urls = remaining_urls
    db.commit()
    db.refresh(hostel)

    return {"deleted_urls": deleted_urls, "photos_urls": hostel.photos_urls}

@router.get("/facilities", tags=["Facilities"])
def get_facilities(
    db: Session = Depends(get_db)
):
    """Get list of predefined facilities"""
    facilitys = db.query(Facility).all()
    return facilitys




@router.post("/facilities", tags=["Facilities"])
def create_facility(
    facility: FacilityCreate,
    db: Session = Depends(get_db),
):
    """Create a new facility"""

    db_facility = Facility(**facility.model_dump())

    db.add(db_facility)
    db.commit()
    db.refresh(db_facility)

    return db_facility



@router.delete("/facilities/{facility_id}", tags=["Facilities"])
def delete_facility(
    facility_id: str,
    db: Session = Depends(get_db)
):
    """Delete a facility (admin only)"""
    # This endpoint can be implemented to allow admins to remove facilities
    db_facility = db.query(services.Facility).filter(services.Facility.id == facility_id).first()
    if not db_facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    db.delete(db_facility)
    db.commit()
    return {"message": "Facility deleted successfully"} 

# Include auth router
# router.include_router(auth_router)



# TENANT MANAGEMENT ENDPOINTS


tenant = APIRouter(prefix="/tenant", tags=["Tenants"])


@auth_router.post("/tenant/send-otp", response_model=OTPResponse, tags=["Tenant Authentication"])
def send_tenant_otp(
    otp_request: OTPRequest,
    db: Session = Depends(get_db)
):
    """Send OTP to tenant's phone number for login/verification"""
    tenant = services.get_tenant_by_phone(db, otp_request.phone_number)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found. Please contact owner.")
    
    result = services.send_otp(
        otp_request.phone_number
    )
    return OTPResponse(  
        ok=True,
        message=result["message"],
        expires_in=result["expires_in"]
    )


@auth_router.post("/tenant/verify-otp",  tags=["Tenant Authentication"])
def verify_tenant_otp_and_login(
    otp_verify: OTPVerify,
    request: Request,
    db: Session = Depends(get_db)
):
    """Verify tenant OTP and login, returning access token"""
    try:
        auth_result = services.authenticate_tenant_with_otp(
            db, 
            otp_verify.phone_number, 
            otp_verify.otp,
            request.client.host
        )
        
        tenant = auth_result["tenant"]
        
        access_token = create_access_token(
            subject=tenant.phone_number,
            extra_data={
                "tenant_id": tenant.id,
                "hostel_id": tenant.hostel_id
            }
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE * 24 * 60,
            "tenant": tenant,
            "owner_id": tenant.hostel.owner_id
        }
        
    except services.InvalidOTPError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except services.UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except services.AccountLockedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@auth_router.post("/tenant/logout", tags=["Tenant Authentication"])
def tenant_logout():
    """Logout tenant (client should discard token)"""
    return {"message": "Successfully logged out"}

from .security import get_current_tenant
@tenant.get("/me", tags=["Tenants"])
def get_current_tenant(current_tenant: dict = Depends(get_current_tenant)):
    """Get current tenant profile"""
    tenant = current_tenant
    return current_tenant

@tenant.get("/MyPG",  tags=["Tenants"])   
def get_tenant_pg(current_tenant: dict = Depends(get_current_tenant), db: Session = Depends(get_db)):
    """Get the PG/Hostel details of the tenant"""
    tenant = current_tenant
    hostel = db.query(Hostel).filter(Hostel.id == tenant['tenant'].hostel_id).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Hostel not found")
    return hostel

@tenant.get("/MyBills",  tags=["Tenants"])
def get_tenant_bills(current_tenant: dict = Depends(get_current_tenant), db: Session = Depends(get_db)):
    """Get all bills for the tenant"""
    bills = db.query(Bill).filter(Bill.tenant_id == current_tenant["tenant_id"]).all()
    return bills


@tenant.get("/hostels", tags=["Tenants"])
def get_hostels(
    db: Session = Depends(get_db)
):
    """Get all hostels for the current owner"""
    hostels = db.query(Hostel).all()
    
    
    return hostels

@tenant.post("/pay-bill/{bill_id}", tags=["Tenants"])
def pay_bill(
    bill_id: int,
    current_tenant: dict = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """Pay a specific bill"""
    bill = db.query(Bill).filter(Bill.id == bill_id, Bill.tenant_id == current_tenant["tenant_id"]).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    if bill.status == "paid":
        raise HTTPException(status_code=400, detail="Bill is already paid")
    
    # Here you would integrate with a payment gateway to process the payment
    # For this example, we'll just mark it as paid
    bill.status = "paid"
    db.commit()
    db.refresh(bill)
    
    return {"message": "Bill paid successfully", "bill": bill}


# Manager router for owner-related endpoints
manager = APIRouter(prefix="/manager", tags=["Manager"])


@manager.post("/create", response_model=ManagerOut, tags=["Manager"])
def create_manager(
    manager_create: ManagerCreate,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Create a new manager under the current owner"""
    db_manager = services.create_manager(db, manager_create, current_owner["id"])
    return db_manager

@manager.get("/managers", response_model=List[ManagerOut], tags=["Manager"])
def get_managers(
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Get all managers for the current owner"""
    managers = db.query(Manager).filter(Manager.owner_id == current_owner["id"]).all()
    return managers

@manager.patch("/managers/{manager_id}", response_model=ManagerOut, tags=["Manager"])
def update_manager(
    manager_id: int,
    manager_update: ManagerUpdate,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Update a manager's details"""
    manager = db.query(Manager).filter(
        Manager.id == manager_id,
        Manager.owner_id == current_owner["id"]
    ).first()
    if not manager:
        raise HTTPException(status_code=404, detail="Manager not found")
    
    update_data = manager_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(manager, field, value)
    db.commit()
    db.refresh(manager)
    return manager

@manager.delete("/managers/{manager_id}", tags=["Manager"])
def delete_manager(
    manager_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Delete a manager"""
    manager = db.query(Manager).filter(
        Manager.id == manager_id,
        Manager.owner_id == current_owner["id"]
    ).first()
    if not manager:
        raise HTTPException(status_code=404, detail="Manager not found")
    db.delete(manager)
    db.commit()
    return {"message": "Manager deleted successfully"}

# Manager-specific routes for managing their assigned hostel
@manager.get("/my-hostel", response_model=HostelOut, tags=["Manager"])
def get_manager_hostel(
    current_manager: dict = Depends(get_current_manager),
    db: Session = Depends(get_db)
):
    """Get the hostel assigned to the current manager"""
    if not current_manager["hostel_id"]:
        raise HTTPException(status_code=404, detail="No hostel assigned to this manager")
    
    hostel = db.query(Hostel).filter(Hostel.id == current_manager["hostel_id"]).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Hostel not found")
    
    # Populate room_type_name for each room
    for room in hostel.rooms:
        if room.room_type_rel:
            room.room_type_name = room.room_type_rel.name
    
    return hostel

@manager.get("/my-hostel/rooms", response_model=List[RoomHostelImgOut], tags=["Manager"])
def get_manager_hostel_rooms(
    current_manager: dict = Depends(get_current_manager),
    db: Session = Depends(get_db)
):
    """Get all rooms for the manager's assigned hostel"""
    if not current_manager["hostel_id"]:
        raise HTTPException(status_code=404, detail="No hostel assigned to this manager")
    
    rooms = db.query(Room).filter(Room.hostel_id == current_manager["hostel_id"]).all()
    
    # Populate room_type_name for each room
    for room in rooms:
        if room.room_type_rel:
            room.room_type_name = room.room_type_rel.name
    
    return rooms

@manager.get("/my-hostel/tenants", response_model=List[TenantOut], tags=["Manager"])
def get_manager_hostel_tenants(
    current_manager: dict = Depends(get_current_manager),
    db: Session = Depends(get_db)
):
    """Get all tenants for the manager's assigned hostel"""
    if not current_manager["hostel_id"]:
        raise HTTPException(status_code=404, detail="No hostel assigned to this manager")
    
    tenants = db.query(Tenant).filter(
        Tenant.hostel_id == current_manager["hostel_id"],
        Tenant.active == True
    ).all()
    return tenants

@manager.get("/my-hostel/bills", response_model=List[BillOut], tags=["Manager"])
def get_manager_hostel_bills(
    current_manager: dict = Depends(get_current_manager),
    db: Session = Depends(get_db)
):
    """Get all bills for the manager's assigned hostel"""
    if not current_manager["hostel_id"]:
        raise HTTPException(status_code=404, detail="No hostel assigned to this manager")
    
    bills = db.query(Bill).filter(Bill.hostel_id == current_manager["hostel_id"]).all()
    return bills

@manager.get("/my-hostel/expenses", tags=["Manager"])
def get_manager_hostel_expenses(
    current_manager: dict = Depends(get_current_manager),
    db: Session = Depends(get_db)
):
    """Get all expenses for the manager's assigned hostel"""
    if not current_manager["hostel_id"]:
        raise HTTPException(status_code=404, detail="No hostel assigned to this manager")
    
    expenses = db.query(Expense).filter(
        Expense.hostel_id == current_manager["hostel_id"],
        Expense.created_by == current_manager["owner_id"]
    ).all()
    return expenses

@manager.get("/my-hostel/dashboard", tags=["Manager"])
def get_manager_dashboard(
    current_manager: dict = Depends(get_current_manager),
    db: Session = Depends(get_db)
):
    """Get dashboard data for the manager's assigned hostel"""
    if not current_manager["hostel_id"]:
        raise HTTPException(status_code=404, detail="No hostel assigned to this manager")
    
    hostel_id = current_manager["hostel_id"]
    
    room_filter = Room.hostel_id == hostel_id
    tenant_filter = and_(Tenant.hostel_id == hostel_id, Tenant.active.is_(True))
    expense_filter = Expense.hostel_id == hostel_id
    
    rooms_count = db.query(Room).filter(room_filter).count() or 0
    bed_count = db.query(func.sum(Room.no_of_beds)).filter(room_filter).scalar() or 0
    tenants_count = db.query(Tenant).filter(tenant_filter).count() or 0
    total_amount = db.query(func.sum(Bill.amount)).filter(
        Bill.status != "paid",
        Bill.hostel_id == hostel_id
    ).scalar() or 0
    total_payments = db.query(func.sum(BillTransaction.amount))\
        .join(Tenant)\
        .filter(tenant_filter)\
        .scalar() or 0
    total_expenses = db.query(func.sum(Expense.amount)).filter(expense_filter).scalar() or 0
    
    payment_due = total_amount - total_payments
    
    return {
        "rooms_count": rooms_count,
        "bed_count": bed_count,
        "tenants_count": tenants_count,
        "vacant_beds": bed_count - tenants_count,
        "total_amount": total_amount,
        "total_payments": total_payments,
        "total_expenses": total_expenses,
        "payment_due": payment_due
    }