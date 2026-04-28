
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