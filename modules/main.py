
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

import logging

from sqlalchemy import inspect

from modules.owner.routes import router, auth_router
from modules.bill_payment.routes import router as bill_router
from modules.expenses.routes import router as expense_router
from core.fcm_notification.routes import router as token_router
from core.database import SessionLocal

from core.config import DATABASE_URL

import firebase_admin
from firebase_admin import credentials
from core.config import settings
cred = credentials.Certificate(settings.FIRE_BASE_CREDENTIALS_PATH)


logger = logging.getLogger(__name__)

app = FastAPI(title="HostelOps API", version="1.0.0")

# Mount static files for uploaded images
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


firebase_admin.initialize_app(cred)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return JSONResponse({
        "api_version": "1.0.0",
        "message": "HostelOps API is running"
    })


app.include_router(auth_router)
app.include_router(router)
app.include_router(bill_router)
app.include_router(expense_router)
app.include_router(token_router)  # Include FCM notification router



