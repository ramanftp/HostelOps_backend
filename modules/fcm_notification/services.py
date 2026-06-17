
from firebase_admin import messaging, credentials


def send_notifications(token:str,title:str,body:str):
   
   
   message=messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body
        ),
        token=token
    )
   response=messaging.send(message)
   return response  

def save_token(user_id:int,token:str, device_name:str=None, brand:str=None, device_id:str=None, platform:str=None, os_version:str=None, city:str=None, latitude:float=None, longitude:float=None, role:str=None):
    from core.database import SessionLocal
    from modules.fcm_notification.models import NotificationToken

    db = SessionLocal()
    existing_token = db.query(NotificationToken).filter_by(token=token).first()
    if existing_token:
        existing_token.user_id = user_id
        existing_token.device_name = device_name
        existing_token.brand = brand
        existing_token.device_id = device_id
        existing_token.platform = platform
        existing_token.os_version = os_version
        existing_token.city = city
        existing_token.latitude = latitude
        existing_token.longitude = longitude
        existing_token.role = role
        db.commit()
        return existing_token
    new_token = NotificationToken(user_id=user_id, token=token, device_name=device_name, brand=brand, device_id=device_id, platform=platform, os_version=os_version, city=city, latitude=latitude, longitude=longitude, role=role)
    db.add(new_token)
    db.commit()
    db.refresh(new_token)
    return new_token