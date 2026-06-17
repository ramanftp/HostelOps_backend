
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

import logging
import os

from sqlalchemy import inspect

from modules.owner.routes import router, auth_router, manager, tenant
from modules.bill_payment.routes import router as bill_router
from modules.expenses.routes import router as expense_router
from modules.fcm_notification.routes import router as token_router
from modules.complaints.routes import router as complaint_router
from core.database import SessionLocal

from core.config import DATABASE_URL

import firebase_admin
from firebase_admin import credentials
from core.config import settings
from modules.subcriptions import subscriptions_router
cred = credentials.Certificate(settings.FIRE_BASE_CREDENTIALS_PATH)


logger = logging.getLogger(__name__)

app = FastAPI(title="HostelOps API", version="1.0.0")

# Ensure upload base directory exists
os.makedirs(settings.UPLOAD_BASE_DIR, exist_ok=True)

# Mount static files for uploaded images using configured base directory
app.mount(settings.UPLOAD_URL_BASE, StaticFiles(directory=settings.UPLOAD_BASE_DIR), name="uploads")

# Also mount old uploads directory for backward compatibility
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads_legacy")


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

app.include_router(subscriptions_router)  # Include subscriptions router
app.include_router(auth_router)
app.include_router(router)
app.include_router(manager)
app.include_router(tenant)
app.include_router(bill_router)
app.include_router(expense_router)
app.include_router(token_router)  # Include FCM notification router
app.include_router(complaint_router)  # Include complaints router



