from datetime import datetime
from typing import List
import random
import string

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from modules.owner.security import get_current_owner
from modules.owner.models import Hostel, Tenant

from . import services
from .schema import (
    BillCreate, BillUpdate, BillOut,
    TransactionCreate, TransactionUpdate, TransactionOut
)

router = APIRouter(prefix="/owner/bills", tags=["Bills"])


# ============================================================================
# Bill Management Endpoints
# ============================================================================

@router.get("/", response_model=List[BillOut], tags=["Bills"])
def get_hostel_bills(
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Get all bills for the owner's hostels"""
    # Get all hostels owned by the current owner
    hostels = db.query(Hostel).filter(Hostel.owner_id == current_owner["id"]).all()
    hostel_ids = [hostel.id for hostel in hostels]
    
    if not hostel_ids:
        return []
    
    bills = []
    for hostel_id in hostel_ids:
        bills.extend(services.get_bills_by_hostel(db, hostel_id))
    
    return bills


@router.get("/hostel/{hostel_id}", response_model=List[BillOut], tags=["Bills"])
def get_bills_by_hostel(
    hostel_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Get all bills for a specific hostel"""
    # Verify ownership
    hostel = db.query(Hostel).filter(
        Hostel.id == hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Hostel not found")
    
    return services.get_bills_by_hostel(db, hostel_id)


@router.get("/tenant/{tenant_id}", response_model=List[BillOut], tags=["Bills"])
def get_bills_by_tenant(
    tenant_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Get all bills for a specific tenant"""
    # Verify ownership through hostel
    from modules.owner.models import Tenant
    tenant = db.query(Tenant).join(Hostel).filter(
        Tenant.id == tenant_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return services.get_bills_by_tenant(db, tenant_id)


@router.get("/{bill_id}", response_model=BillOut, tags=["Bills"])
def get_bill(
    bill_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Get a specific bill"""
    bill = services.get_bill(db, bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    # Verify ownership
    hostel = db.query(Hostel).filter(
        Hostel.id == bill.hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    return bill


@router.post("/", response_model=BillOut, tags=["Bills"])
def create_bill(
    bill: BillCreate,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Create a new bill"""
    # Verify hostel ownership
    hostel = db.query(Hostel).filter(
        Hostel.id == bill.hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Hostel not found")
    
    # Verify tenant belongs to the hostel
    from modules.owner.models import Tenant
    tenant = db.query(Tenant).filter(
        Tenant.id == bill.tenant_id,
        Tenant.hostel_id == bill.hostel_id
    ).first()
    if not tenant:
        raise HTTPException(status_code=400, detail="Tenant does not belong to this hostel")
    
    return services.create_bill(db, bill)


@router.put("/{bill_id}", response_model=BillOut, tags=["Bills"])
def update_bill(
    bill_id: int,
    bill_update: BillUpdate,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Update an existing bill"""
    bill = services.get_bill(db, bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    # Verify ownership
    hostel = db.query(Hostel).filter(
        Hostel.id == bill.hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    updated_bill = services.update_bill(db, bill_id, bill_update)
    if not updated_bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    return updated_bill


@router.delete("/{bill_id}", tags=["Bills"])
def delete_bill(
    bill_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Delete a bill"""
    bill = services.get_bill(db, bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    # Verify ownership
    hostel = db.query(Hostel).filter(
        Hostel.id == bill.hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    if not services.delete_bill(db, bill_id):
        raise HTTPException(status_code=404, detail="Bill not found")
    
    return {"message": "Bill deleted successfully"}


# ============================================================================
# Transaction Management Endpoints
# ============================================================================

@router.get("/{bill_id}/transactions", response_model=List[TransactionOut], tags=["Transactions"])
def get_bill_transactions(
    bill_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Get all transactions for a bill"""
    bill = services.get_bill(db, bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    # Verify ownership
    hostel = db.query(Hostel).filter(
        Hostel.id == bill.hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    return services.get_transactions_by_bill(db, bill_id)


@router.get("/transactions/{transaction_id}", response_model=TransactionOut, tags=["Transactions"])
def get_transaction(
    transaction_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Get a specific transaction"""
    transaction = services.get_transaction(db, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Verify ownership
    hostel = db.query(Hostel).filter(
        Hostel.id == transaction.hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return transaction


@router.post("/{bill_id}/transactions", response_model=TransactionOut, tags=["Transactions"])
def create_transaction(
    bill_id: int,
    transaction: TransactionCreate,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Create a new transaction for a bill"""
    bill = services.get_bill(db, bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    # Verify ownership
    hostel = db.query(Hostel).filter(
        Hostel.id == bill.hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    # Ensure transaction data matches bill
    if transaction.bill_id != bill_id:
        raise HTTPException(status_code=400, detail="Bill ID mismatch")
    if transaction.hostel_id != bill.hostel_id:
        raise HTTPException(status_code=400, detail="Hostel ID mismatch")
    if transaction.tenant_id != bill.tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID mismatch")
    
    return services.create_transaction(db, transaction)


@router.put("/transactions/{transaction_id}", response_model=TransactionOut, tags=["Transactions"])
def update_transaction(
    transaction_id: int,
    transaction_update: TransactionUpdate,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Update an existing transaction"""
    transaction = services.get_transaction(db, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Verify ownership
    hostel = db.query(Hostel).filter(
        Hostel.id == transaction.hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    updated_transaction = services.update_transaction(db, transaction_id, transaction_update)
    if not updated_transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return updated_transaction


@router.delete("/transactions/{transaction_id}", tags=["Transactions"])
def delete_transaction(
    transaction_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Delete a transaction"""
    transaction = services.get_transaction(db, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Verify ownership
    hostel = db.query(Hostel).filter(
        Hostel.id == transaction.hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if not services.delete_transaction(db, transaction_id):
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return {"message": "Transaction deleted successfully"}


# ============================================================================
# Utility Endpoints
# ============================================================================

@router.get("/overdue/all", response_model=List[BillOut], tags=["Bills"])
def get_overdue_bills(
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Get all overdue bills for the owner's hostels"""
    hostels = db.query(Hostel).filter(Hostel.owner_id == current_owner["id"]).all()
    hostel_ids = [hostel.id for hostel in hostels]
    
    if not hostel_ids:
        return []
    
    overdue_bills = []
    for hostel_id in hostel_ids:
        overdue_bills.extend(services.get_overdue_bills(db, hostel_id))
    
    return overdue_bills


@router.get("/pending/all", response_model=List[BillOut], tags=["Bills"])
def get_pending_bills(
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Get all pending bills for the owner's hostels"""
    hostels = db.query(Hostel).filter(Hostel.owner_id == current_owner["id"]).all()
    hostel_ids = [hostel.id for hostel in hostels]
    
    if not hostel_ids:
        return []
    
    pending_bills = []
    for hostel_id in hostel_ids:
        pending_bills.extend(services.get_pending_bills(db, hostel_id))
    
    return pending_bills


# ============================================================================
# Cash Transaction OTP Verification Endpoints
# ============================================================================

# In-memory storage for OTPs (in production, use Redis or database)
otp_storage = {}

def generate_otp():
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=6))

def send_otp_to_tenant(tenant_phone: str, otp: str):
    """
    Send OTP to tenant (mock implementation)
    In production, integrate with SMS service like Twilio, etc.
    """
    print(f"📱 Sending OTP {otp} to tenant phone: {tenant_phone}")
    # Mock: In production, use actual SMS service
    # Example with Twilio:
    # from twilio.rest import Client
    # client = Client(account_sid, auth_token)
    # client.messages.create(
    #     body=f"Your OTP for cash payment verification is: {otp}",
    #     from_='+1234567890',
    #     to=tenant_phone
    # )
    return True

@router.post("/transactions/{bill_id}/send-otp", tags=["Cash Transactions"])
def send_cash_payment_otp(
    bill_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Send OTP for cash transaction verification"""
    bill = services.get_bill(db, bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")


    
    # Verify ownership
    hostel = db.query(Hostel).filter(
        Hostel.id == bill.hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Transaction not found")
    

    
    # Get tenant details
    tenant = db.query(Tenant).filter(Tenant.id == bill.tenant_id).first()
    if not tenant or not tenant.phone:
        raise HTTPException(status_code=400, detail="Tenant phone number not found")
    
    # Generate OTP
    otp = generate_otp()
    
    # Store OTP with expiration (5 minutes)
    otp_storage[bill_id] = {
        "otp": otp,
        "expires_at": datetime.now().timestamp() + 300,  # 5 minutes
        "tenant_id": bill.tenant_id
    }
    
    # Send OTP to tenant
    send_otp_to_tenant(tenant.phone, otp)
    
    return {
        "message": "OTP sent successfully",
        "bill_id": bill_id,
        "tenant_phone": tenant.phone[-4:] + "****"  # Mask phone number
    }

@router.post("/transactions/{bill_id}/verify-otp", tags=["Cash Transactions"])
def verify_cash_payment_otp(
    bill_id: int,
    otp_data: dict,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Verify OTP and update cash transaction status"""
    if "otp" not in otp_data:
        raise HTTPException(status_code=400, detail="OTP is required")
    
    otp = otp_data["otp"]
    
    bill = services.get_bill(db, bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    

    
    # Verify ownership
    hostel = db.query(Hostel).filter(
        Hostel.id == bill.hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Check if OTP exists and is valid
    if bill_id not in otp_storage:
        raise HTTPException(status_code=400, detail="OTP not sent or expired")
    
    stored_otp_data = otp_storage[bill_id]
    
    # Check expiration
    if datetime.now().timestamp() > stored_otp_data["expires_at"]:
        del otp_storage[bill_id]
        raise HTTPException(status_code=400, detail="OTP expired")
    
    # Verify OTP
    if stored_otp_data["otp"] != otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    # Update transaction status to verified
    trancsation = TransactionCreate(
        bill_id=bill_id,
        amount=bill.amount,
        payment_method="cash",
        status="verified",
        tenant_id=stored_otp_data["tenant_id"],
        hostel_id=bill.hostel_id
    )
    
    # Update bill status to paid if transaction is verified
    if bill:
        bill_update = BillUpdate(status="paid")
        services.update_bill(db, bill.id, bill_update)
    
    # Clear OTP from storage
    del otp_storage[bill_id]
    
    return {
        "message": "OTP verified successfully",
        "transaction_id": trancsation,
        "status": "verified",
        "bill_status": "paid"
    }

@router.post("/transactions/{bill_id}/resend-otp", tags=["Cash Transactions"])
def resend_cash_payment_otp(
    bill_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Resend OTP for cash transaction verification"""
    bill = services.get_bill(db, bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    # Verify ownership
    hostel = db.query(Hostel).filter(
        Hostel.id == bill.hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Check if payment method is cash
    tenant = db.query(Tenant).filter(Tenant.id == bill.tenant_id).first()
    if not tenant or not tenant.phone:
        raise HTTPException(status_code=400, detail="Tenant phone number not found")
    
    # Generate new OTP
    otp = generate_otp()
    
    # Store OTP with expiration (5 minutes)
    otp_storage[bill_id] = {
        "otp": otp,
        "expires_at": datetime.now().timestamp() + 300,  # 5 minutes
        "tenant_id": bill.tenant_id
    }
    
    # Send OTP to tenant
    send_otp_to_tenant(tenant.phone, otp)
    
    return {
        "message": "OTP resent successfully",
        "transaction_id": bill_id,
        "tenant_phone": tenant.phone[-4:] + "****"  # Mask phone number
    }

