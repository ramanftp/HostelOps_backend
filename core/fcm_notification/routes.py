
from fastapi import APIRouter, FastAPI

from modules.bill_payment import services



from core.config import settings



router = APIRouter(prefix="/token", tags=["Token"])

@router.post("/save_token")
def save_token(token:str,id:int):
    # services.save_token(token,id)
    return {"message":"Token saved successfully"}   
 


@router.post("/send_notification")
def send_notification(token:str,title:str,body:str):
    from core.fcm_notification import services  

    response=services.send_notifications(token,title,body)
    return {"message_id":response}  