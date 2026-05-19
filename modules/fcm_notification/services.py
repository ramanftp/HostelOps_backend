
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

def save_token(user_id:int,token:str):
    from core.database import SessionLocal
    from modules.fcm_notification.models import NotificationToken

    db = SessionLocal()
    existing_token = db.query(NotificationToken).filter_by(token=token).first()
    if existing_token:
        existing_token.user_id = user_id
        db.commit()
        return existing_token
    new_token = NotificationToken(user_id=user_id, token=token)
    db.add(new_token)
    db.commit()
    db.refresh(new_token)
    return new_token