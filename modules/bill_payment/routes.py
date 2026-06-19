from datetime import datetime
from typing import List
import random
import string

from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import Transaction
from sqlalchemy.orm import Session

from core.celery.task import generate_monthly_bills
from core.database import get_db
from modules.bill_payment.email_templates import generate_bill_pdf
from modules.owner.security import get_current_owner
from modules.owner.models import Hostel, Tenant

from . import services
from .schema import (
    BillCreate, BillOtp, BillUpdate, BillOut, ReminderRequest,
    TransactionCreate, TransactionUpdate, TransactionOut
)

from fastapi.responses import StreamingResponse
from email.message import EmailMessage
import smtplib

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
import redis
import json
import random
import string


# =========================
# REDIS SETUP
# =========================
redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True
)

OTP_EXPIRY = 300  # 5 minutes


# =========================

# =========================
# OTP UTIL FUNCTIONS
# =========================
def generate_otp():
    return ''.join(random.choices(string.digits, k=6))


def store_otp(bill_id: int, otp: str, tenant_id: int):
    data = {
        "otp": otp,
        "tenant_id": tenant_id,
        "attempts": 0
    }

    redis_client.setex(
        f"otp:{bill_id}",
        OTP_EXPIRY,
        json.dumps(data)
    )


def get_otp_data(bill_id: int):
    data = redis_client.get(f"otp:{bill_id}")
    if not data:
        return None
    return json.loads(data)


def delete_otp(bill_id: int):
    redis_client.delete(f"otp:{bill_id}")


def increment_attempts(bill_id: int):
    data = get_otp_data(bill_id)
    if not data:
        return None

    data["attempts"] += 1

    redis_client.setex(
        f"otp:{bill_id}",
        OTP_EXPIRY,
        json.dumps(data)
    )

    return data["attempts"]


def send_otp_to_tenant(phone: str, otp: str):
    # MOCK SMS
    print(f"📱 OTP {otp} sent to {phone}")
    return True


# ============================================================================
# SEND OTP
# ============================================================================
@router.post("/transactions/{bill_id}/send-otp", tags=["Cash Transactions"])
def send_cash_payment_otp(
    bill_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    bill = services.get_bill(db, bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    # ownership check
    hostel = db.query(Hostel).filter(
        Hostel.id == bill.hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()

    if not hostel:
        raise HTTPException(status_code=403, detail="Unauthorized")

    tenant = db.query(Tenant).filter(Tenant.id == bill.tenant_id).first()
    if not tenant or not tenant.phone_number:
        raise HTTPException(status_code=400, detail="Tenant phone not found")

    otp = generate_otp()

    store_otp(bill_id, otp, tenant.id)

    send_otp_to_tenant(tenant.phone_number, otp)

    return {
        "message": "OTP sent successfully",
        "bill_id": bill_id,
        "phone": "****" + tenant.phone_number[-4:]
    }


# ============================================================================
# VERIFY OTP
# ============================================================================
@router.post("/transactions/{bill_id}/verify-otp", tags=["Cash Transactions"])
def verify_cash_payment_otp(
    bill_id: int,
    otp_data: BillOtp,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    if not otp_data.otp:
        raise HTTPException(status_code=400, detail="OTP is required")

    bill = services.get_bill(db, bill_id)
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    hostel = db.query(Hostel).filter(
        Hostel.id == bill.hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()

    if not hostel:
        raise HTTPException(status_code=403, detail="Unauthorized")

    stored = get_otp_data(bill_id)

    if not stored:
        raise HTTPException(status_code=400, detail="OTP expired or not found")

    # max 3 attempts
    if stored["attempts"] >= 3:
        delete_otp(bill_id)
        raise HTTPException(status_code=400, detail="Too many attempts")

    if stored["otp"] != otp_data.otp:
        attempts = increment_attempts(bill_id)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid OTP ({attempts}/3 attempts used)"
        )

    # ✅ OTP correct → create transaction
    new_txn = TransactionCreate(
        bill_id=bill_id,
        amount=bill.amount,
        payment_method="cash",
        status="verified",
        tenant_id=stored["tenant_id"],
        hostel_id=bill.hostel_id
    )   
    
    new_txn = services.create_transaction(db, new_txn)

    # update bill
    bill.status = "paid"



    delete_otp(bill_id)

    return {
        "message": "OTP verified successfully",
        "transaction_id": new_txn.id,
        "status": "verified",
        "bill_status": "paid"
    }

@router.post("/run-bills")
def run_bills():
    
    generate_monthly_bills()
    return {"message": "Bill generation started"}




@router.get("/download-bill/{bill_id}")
def download_bill(
    bill_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    # Get bill
    bill = services.get_bill(db, bill_id)

    if not bill:
        raise HTTPException(
            status_code=404,
            detail="Bill not found"
        )

    # Ownership check
    hostel = db.query(Hostel).filter(
        Hostel.id == bill.hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()

    if not hostel:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized"
        )

    # Generate PDF
    pdf_buffer = generate_bill_pdf(
        bill=bill,
        tenant=bill.tenant,
        hostel=bill.hostel
    )

    filename = f"{bill.bill_number}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "anmol.mishra@ftprotech.com"
SMTP_PASS = "dvywyerwvvshajkz"  # Use environment variables in production!

@router.post("/send-bill-email/{bill_id}")
def send_bill_email(
    bill_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):

    # Get bill
    bill = services.get_bill(db, bill_id)

    if not bill:
        raise HTTPException(
            status_code=404,
            detail="Bill not found"
        )

    # Ownership check
    hostel = db.query(Hostel).filter(
        Hostel.id == bill.hostel_id,
        Hostel.owner_id == current_owner["id"]
    ).first()

    if not hostel:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized"
        )

    tenant = bill.tenant

    if not tenant.email:
        raise HTTPException(
            status_code=400,
            detail="Tenant email not available"
        )

    # -----------------------------------
    # Generate PDF
    # -----------------------------------
    pdf_buffer = generate_bill_pdf(
        bill=bill,
        tenant=tenant,
        hostel=hostel
    )

    pdf_bytes = pdf_buffer.getvalue()

    # -----------------------------------
    # Email Message
    # -----------------------------------
    msg = EmailMessage()

    msg["Subject"] = f"Bill Invoice - {bill.bill_number}"
    msg["From"] = SMTP_USER
    msg["To"] = tenant.email

    msg.set_content(
        f"""
Hello {tenant.name},

Your new hostel bill has been generated.

Bill Number: {bill.bill_number}
Amount: ₹{bill.amount}
Due Date: {bill.due_date.strftime('%d-%m-%Y')}

Please find attached PDF invoice.

Thank you,
{hostel.name}
"""
    )

    # Attach PDF
    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=f"{bill.bill_number}.pdf"
    )

    # -----------------------------------
    # Send Email
    # -----------------------------------
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    return {
        "message": "Bill email sent successfully",
        "email": tenant.email
    }




# from twilio.rest import Client


# client = Client(ACCOUNT_SID, AUTH_TOKEN)


# @router.post("/send-reminder")
# def send_reminder(data: ReminderRequest):

#     variables = json.dumps({
#         "1": data.owner_name,
#         "2": data.tenant_name,
#         "3": data.room_no,
#         "4": data.pg_name,
#         "5": str(data.amount)
#     })

#     message = client.messages.create(
#         from_='whatsapp:+14155238886',
#         to=f'whatsapp:{data.phone}',
#         content_sid="HX1e2486cd1a8f742c880a665dcf318c24",
#         content_variables=variables
#     )

#     return {
#         "status": "sent",
#         "sid": message.sid
#     }