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
ACCESS_TOKEN_EXPIRE = settings.ACCESS_TOKEN_EXPIRE_MINUTES or 30 
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
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE)
    
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

def get_current_tenant(token: str = Depends(security), db: Session = Depends(get_db)):
    """Get current tenant from token"""
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
    tenant_id: int = payload.get("tenant_id")
    
    if not phone_number or not tenant_id:
        raise credentials_exception
    
    # Get tenant from database
    tenant = services.get_current_tenant(db, tenant_id)
    if not tenant:
        raise credentials_exception
    
    # Check if tenant is active
    if tenant.active != True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant account is inactive"
        )
    
    # Return tenant info with roles
    return {
        "id": tenant.id,
        "phone_number": tenant.phone_number,
        "email": tenant.email,
        "name": tenant.name,
        "tenant": tenant
    }

def get_current_manager(token: str = Depends(security), db: Session = Depends(get_db)):
    """Get current manager from token"""
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
    manager_id: int = payload.get("manager_id")
    owner_id: int = payload.get("owner_id")
    
    if not phone_number or not manager_id or not owner_id:
        raise credentials_exception
    
    # Get manager from database
    from modules.owner.models import Manager
    manager = db.query(Manager).filter(Manager.id == manager_id).first()
    if not manager:
        raise credentials_exception
    
    # Get owner from database
    owner = services.get_owner_by_id(db, owner_id)
    if not owner:
        raise credentials_exception
    
    # Return manager info with owner details
    return {
        "id": manager.id,
        "phone_number": manager.phone_number,
        "email": manager.email,
        "name": manager.name,
        "owner_id": manager.owner_id,
        "hostel_id": manager.hostel_id,
        "manager": manager,
        "owner": owner
    }