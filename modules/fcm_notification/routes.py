
from fastapi import APIRouter, Depends, FastAPI

from core.database import  get_db, SessionLocal
from modules.bill_payment import services



from core.config import settings



router = APIRouter(prefix="/token", tags=["Token"])


from pydantic import BaseModel, Field, ConfigDict, json, validator
from typing import Optional, List
from datetime import datetime

class NotificationTokenCreate(BaseModel):
    token: str
    user_id: int
    device_name: Optional[str]
    brand: Optional[str]
    device_id: Optional[str]
    platform: Optional[str]
    os_version: Optional[str]
    city: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    role: Optional[str]

class NotificationTokenOut(BaseModel):
    id: int
    token: str
    user_id: int
    device_name: Optional[str]
    brand: Optional[str]
    device_id: Optional[str]
    platform: Optional[str]
    os_version: Optional[str]
    city: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    role: Optional[str]
    created_at: datetime
    updated_at: datetime

@router.post("/save_token")
def save_token(token: NotificationTokenCreate):
    from modules.fcm_notification import services  

    services.save_token(token.user_id, token.token, token.device_name, token.brand, token.device_id, token.platform, token.os_version, token.city, token.latitude, token.longitude, token.role)
    return {"message": "Token saved successfully"}
 


@router.post("/send_notification")
def send_notification(user_id:int,title:str,body:str):
    from modules.fcm_notification import services  
    db = SessionLocal()
    token = db.query(services.NotificationToken).filter(services.NotificationToken.user_id == user_id).first()
    response=services.send_notifications(token,title,body)
    return {"message_id":response}  