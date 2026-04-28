from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from modules.owner import services
from sqlalchemy import select
from fastapi.security import HTTPBearer

security = HTTPBearer()

# OAuth2 scheme (using phone number as username)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/verify-otp", auto_error=False)

# Token settings
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES or 30 * 24 * 60  # 30 days
ALGORITHM = "HS256"
SECRET_KEY = settings.SECRET_KEY


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra_data: Optional[Dict[str, Any]] = None
) -> str:
    """Create a JWT access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.utcnow()
    }
    
    if extra_data:
        to_encode.update(extra_data)
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str):
    token = token.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user_id",
            )

        return payload

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
async def get_current_owner(
    token: str = Depends(security),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get current owner from token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
    
    # Verify token
    payload = verify_token(token)
    if not payload:
        raise credentials_exception
    
    phone_number: str = payload.get("sub")
    owner_id: int = payload.get("owner_id")
    
    if not phone_number or not owner_id:
        raise credentials_exception
    
    # Get user from database
    user = services.get_owner_by_id(db, owner_id)
    if not user:
        raise credentials_exception
    
    # Check if user is active
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Return user info with roles
    return {
        "id": user.id,
        "phone_number": user.phone_number,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "owner": user
    }

