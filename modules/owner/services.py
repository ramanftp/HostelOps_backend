from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import secrets
import json
import re
import uuid

from fastapi import HTTPException
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .schemas import OwnerCreate
from .models import Owner
from core.config import settings

import logging
import requests
import redis

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)

OTP_PREFIX = "otp:"

def _otp_key(phone: str) -> str:
    return f"{OTP_PREFIX}{phone}"

logger = logging.getLogger(__name__)


class AuthServiceError(Exception):
    """Base exception for auth service"""
    pass


class UserNotFoundError(AuthServiceError):
    """User not found"""
    pass


class UserAlreadyExistsError(AuthServiceError):
    """User already exists"""
    pass


class InvalidOTPError(AuthServiceError):
    """Invalid OTP"""
    pass


class AccountLockedError(AuthServiceError):
    """Account is locked"""
    pass


# OTP Store (in production, use Redis)

# ============================================================================
# Phone Number Utilities
# ============================================================================

def normalize_phone(phone: str) -> str:
    """Normalize phone number to E.164 format"""
    # # Remove all non-digit characters
    # digits = re.sub(r"\D", "", phone)
    
    # # If it's a 10-digit Indian number, add +91
    # if len(digits) == 10:
    #     return f"+91{digits}"
    
    # # If it's 12 digits and starts with 91, add +
    # if len(digits) == 12 and digits.startswith("91"):
    #     return f"+{digits}"
    
    # # If it already has country code, ensure it has +
    # if len(digits) > 10 and not phone.startswith('+'):
    #     return f"+{digits}"
    
    return phone


# ============================================================================
# User Management Functions
# ============================================================================

def get_owner_by_id(db: Session, owner_id: int) -> Optional[Owner]:
    """Get owner by ID"""
    return db.get(Owner, owner_id)


def get_owner_by_phone(db: Session, phone_number: str) -> Optional[Owner]:
    """Get owner by phone number"""
    # normalized = normalize_phone(phone_number)
    owner =  db.execute(
        select(Owner).where(Owner.phone_number == phone_number)
    ).scalar_one_or_none()
    return owner

def register_owner(db: Session, owner_create: OwnerCreate) -> Owner:
    """Register a new owner"""
    normalized_phone = normalize_phone(owner_create.phone_number)
    
    # Check if phone or email already exists
    existing_owner = db.execute(
        select(Owner).where(
            or_(
                Owner.phone_number == normalized_phone,
                Owner.email == owner_create.email
            )
        )
    ).scalar_one_or_none()
    
    if existing_owner:
        raise UserAlreadyExistsError("Owner with this phone number or email already exists")
    
    new_owner = Owner(
        phone_number=normalized_phone,
        first_name=owner_create.first_name,
        last_name=owner_create.last_name,
        email=owner_create.email
    )
    
    db.add(new_owner)
    try:
        db.commit()
        db.refresh(new_owner)
        return new_owner
    except IntegrityError:
        db.rollback()
        raise UserAlreadyExistsError("Owner with this phone number or email already exists")


# ============================================================================
# OTP Functions
# ============================================================================

def _generate_otp(length: int = 6) -> str:
    """Generate a secure OTP"""
    # In production, use secrets
    import secrets
    import string
    alphabet = string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def send_otp(phone_number: str, purpose: str = "login", expire_minutes: int = 5) -> Dict[str, Any]:
    """Send OTP via SMS using MSG91"""
    try:
        normalized_phone = normalize_phone(phone_number)
        
        # Generate OTP
        otp = _generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=expire_minutes)
        
        # Log OTP for development
        logger.info(f"📱 OTP for {normalized_phone}: {otp}")
        print(f"📱 OTP for {phone_number}: {otp} (expires in {expire_minutes} minutes)")
        
        # Try to send via MSG91 if configured
        sms_sent = False 
        if settings.MSG91_AUTH_KEY and settings.MSG91_TEMPLATE_ID:
            sms_sent = send_otp_via_msg91(normalized_phone, otp, expire_minutes)
            if sms_sent:
                logger.info(f"SMS sent via MSG91 to {normalized_phone}")
        else:
            logger.warning("MSG91 not configured - OTP will not be sent via SMS")
        # 
        # Store OTP for verification
        ttl = expire_minutes * 60
        sms_sent = True

        # Store OTP in Redis with TTL
        redis_client.setex(
            _otp_key(phone_number),
            ttl,
            json.dumps( {
            "otp": otp,
            "expires_at": expires_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "purpose": purpose,
            "attempts": 0,
            "sms_sent": sms_sent
        })
        )
        
        # Prepare response
        response = {
            "ok": True,
            "message": "OTP generated successfully",
            "expires_in": expire_minutes * 60,
            "sms_sent": sms_sent
        }
        
        # Include OTP in debug mode for testing
        if settings.DEBUG:
            response["debug_otp"] = otp
            if not sms_sent:
                response["message"] = "OTP generated (SMS not sent - configure MSG91 for production)"
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to generate OTP: {e}")
        raise HTTPException(
            # status_code=stat.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate OTP"
        )

def verify_otp(phone_number: str, otp: str, purpose: str = "login") -> bool:
    """Verify OTP using Redis"""

    try:
        normalized_phone = normalize_phone(phone_number)

        key = _otp_key(phone_number)

        stored = redis_client.get(key)

        if not stored:
            raise InvalidOTPError("OTP expired or not found")

        data = json.loads(stored)

        # Check purpose
        if data["purpose"] != purpose:
            raise InvalidOTPError("OTP purpose mismatch")

        # Check attempts
        attempts = data.get("attempts", 0) + 1

        if attempts > 3:
            redis_client.delete(key)
            raise InvalidOTPError("Too many attempts. Request new OTP.")

        # Wrong OTP
        if data["otp"] != otp:
            data["attempts"] = attempts

            # Update attempts while keeping TTL
            ttl = redis_client.ttl(key)
            redis_client.setex(key, ttl, json.dumps(data))

            raise InvalidOTPError(f"Invalid OTP. {3 - attempts} attempts remaining.")

        # Success
        redis_client.delete(key)

        return True
        
    except InvalidOTPError:
        raise
    except Exception as e:
        logger.error(f"OTP verification error: {e}")
        raise InvalidOTPError("OTP verification failed")

def send_otp_via_msg91(phone: str, otp: str, expire_minutes: int = 5) -> bool:
    """
    Send OTP via MSG91 OTP API
    Returns True if successful, False otherwise
    """
    if not settings.MSG91_AUTH_KEY or not settings.MSG91_TEMPLATE_ID:
        logger.warning("MSG91 credentials missing")
        return False
    
    auth_key = settings.MSG91_AUTH_KEY
    template_id = settings.MSG91_TEMPLATE_ID

    sender = settings.MSG91_SENDER_ID 


    url = "https://api.msg91.com/api/v5/flow/"
    
    headers = {
        "authkey": auth_key,
        "Content-Type": "application/json"
    }
    
    payload = {
        "sender": sender,
        "mobiles": f"+91{phone}",  # Assuming Indian numbers
        "template_id": template_id ,
        "var": otp,
        "otp_length": len(otp),
        "otp_expiry": 5  # minutes
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)

        if response.status_code == 200:
            return True
        else:
            print("MSG91 Error:", response.text)
            return False

    except Exception as e:
        print("Failed:", e)
        return False
# ============================================================================
# Authentication Functions
# ============================================================================

def authenticate_with_otp(
    db: Session, 
    phone_number: str, 
    otp: str,
    ip_address: Optional[str] = None
) -> Dict[str, Any]:
    """
    Authenticate user with phone and OTP
    Returns user and flag indicating if user is new
    """
    try:
        user = get_owner_by_phone(db, phone_number)
        if not user:
            raise InvalidOTPError("User not found")
        
        # Verify OTP for all users including admin
        verify_otp(phone_number, otp, "login")
        
        normalized_phone = normalize_phone(phone_number)
        
        # Find or create user

        
        # Update login info
     
        
        db.flush()

        
        return {
            "user": user
        }
        
    except InvalidOTPError:
        # Track failed attempt if user exists
        normalized_phone = normalize_phone(phone_number)
        user = get_owner_by_phone(db, phone_number)
        
        # if user:
        #     user.failed_otp_attempts += 1
            
        #     # Lock account after 5 failed attempts
        #     if user.failed_otp_attempts >= 5:
        #         user.locked_until = datetime.utcnow() + timedelta(minutes=30)
            
        db.flush()
        
        raise
    except AccountLockedError:
        raise
    except Exception as e:
        logger.error(f"OTP authentication error: {e}")
        raise AuthServiceError("Authentication failed")


# ============================================================================
# Role and Permission Functions
# ============================================================================
def create_hostel(db: Session, hostel_data: Dict[str, Any], owner_id: int) -> None:
    """Create a hostel for the owner"""
    from .models import Hostel
    new_hostel = Hostel(owner_id=owner_id, **hostel_data.model_dump())
    db.add(new_hostel)
    db.commit()
    db.refresh(new_hostel)
    return new_hostel


# ============================================================================
# Aadhaar OCR Functions
# ============================================================================

def extract_text_from_image(image_path: str) -> str:
    """Extract text from image using Google Cloud Vision API"""
    import os
    from google.cloud import vision
    
    # Set Google Cloud credentials if provided
    if settings.GOOGLE_CLOUD_CREDENTIALS_PATH:
        credentials_path = settings.GOOGLE_CLOUD_CREDENTIALS_PATH.strip()
        if not os.path.isfile(credentials_path):
            raise FileNotFoundError(f"Google Cloud credentials file not found: {credentials_path}")
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
    
    client = vision.ImageAnnotatorClient()

    with open(image_path, "rb") as f:
        content = f.read()

    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    

    return response.text_annotations[0].description if response.text_annotations else ""


def parse_aadhaar_text(text: str) -> Dict[str, str]:
    """Parse Aadhaar card text to extract relevant information"""
    lines = [i.strip() for i in text.split("\n") if i.strip()]

    data = {
        "name": "",
        "aadhaar_no": "",
        "dob": "",
        "gender": "",
        "address": ""
    }

    # Aadhar Number
    for line in lines:
        if re.search(r'\d{4}\s\d{4}\s\d{4}', line):
            data["aadhaar_no"] = line.replace(" ", "")

    # DOB
    for line in lines:
        dob = re.findall(r'\d{2}/\d{2}/\d{4}', line)
        if dob:
            data["dob"] = dob[0]

    # Gender
    for line in lines:
        if re.search(r'Male', line, re.I):
            data["gender"] = "MALE"
        elif re.search(r'Female', line, re.I):
            data["gender"] = "FEMALE"

    # Name (usually before DOB)
    for i, line in enumerate(lines):
        if data["dob"] in line:
            data["name"] = lines[i-1]

    # Address (after keyword)
    address_started = False
    address_lines = []

    for line in lines:
        if "Address" in line:
            address_started = True
            continue
        if address_started:
            address_lines.append(line)

    data["address"] = " ".join(address_lines)

    return data


def process_aadhaar_image(image_path: str) -> Dict[str, str]:
    """Process Aadhaar image and extract data"""
    text = extract_text_from_image(image_path)
    return parse_aadhaar_text(text)