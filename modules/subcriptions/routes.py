from datetime import datetime, timedelta
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, requests, status, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from pydantic import json
from redis.connection import parse_url
from requests import session
from requests.models import HTTPBasicAuth
from sqlalchemy import Transaction, and_, func
from sqlalchemy.orm import Query, Session
from core.config import settings
from core.database import get_db
import requests

from modules.subcriptions import services
from modules.owner.models import Owner
from modules.owner.security import get_current_owner
from modules.subcriptions.models import Plan
from modules.subcriptions.schema import PlanBase, SubscriptionBase, SubscriptionCreate


router = APIRouter(prefix="/razorpay", tags=["Subscriptions"])


RAZORPAY_KEY_ID = settings.RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET = settings.RAZORPAY_KEY_SECRET


@router.get("/plans")
def get_plans(
    db: Session = Depends(get_db)
):
    url = "https://api.razorpay.com/v1/plans"

    response = requests.get(
        url,
        auth=HTTPBasicAuth(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
    )

    if response.status_code != 200:
        return {"error": response.text}
    services.create_plans(response.json())

    return response.json()


@router.get("/subscriptions")
def get_subscriptions(
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    url = "https://api.razorpay.com/v1/subscriptions"

    response = requests.get(
        url,
        auth=HTTPBasicAuth(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
    )

    if response.status_code != 200:
        return {"error": response.text}

    return response.json()


@router.get("/subscriptions/{subscription_id}")
def get_subscription_details(
    subscription_id: str,
    # current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    url = f"https://api.razorpay.com/v1/subscriptions/{subscription_id}"

    response = requests.get(
        url,
        auth=HTTPBasicAuth(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
    )

    if response.status_code != 200:
        return {"error": response.text}

    data = response.json()
    # db_subscription = services.create_subscription(subscription)
    # owner.subscription_id = db_subscription.id
    # db.commit()
    # db.refresh(owner)
    return data


@router.get("/my-subscriptions/{owner_id}")
def get_user_subscriptions(
    owner_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    
    owner = db.query(Owner).filter(Owner.id == owner_id).first() 
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    
    url = "https://api.razorpay.com/v1/subscriptions"

    response = requests.get(
        url,
        auth=HTTPBasicAuth(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
    )

    if response.status_code != 200:
        return {"error": response.text}

    data = response.json()

    # Filter subscriptions by owner_id inside notes
    filtered = [
        sub for sub in data["items"]
        if sub.get("notes", {}).get("owner_id") == owner_id
    ]

    return {
        "count": len(filtered),
        "items": filtered
    }




RAZORPAY_KEY_ID = settings.RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET = settings.RAZORPAY_KEY_SECRET

import razorpay
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


subscriptions_store = {}

@router.post("/create-subscription")
def create_subscription(data: SubscriptionCreate,
                        db: Session = Depends(get_db)
                        ):

    plan_key = data.plan_key

    plans = get_plans()
    plan = next((p for p in plans["items"] if p["id"] == plan_key), None)

    if not plan:
        raise HTTPException(status_code=400, detail="Invalid plan")
    db_plan = db.query(Plan).filter(Plan.plan_id == plan["id"]).first()
    owner = db.query(Owner).filter(Owner.phone_number == data.customer_contact or Owner.email == data.customer_email)
    if owner:
        raise HTTPException(status_code=400, detail="Owner with this contact or email already exists")

    try:
        customer = client.customer.create({
            "name": data.customer_name,
            "email": data.customer_email,
            "contact": data.customer_contact,
            "fail_existing": 0
        })
    except razorpay.errors.BadRequestError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Razorpay Error: {str(e)}"
        )
    subscription = client.subscription.create({
        "plan_id": plan["id"],
        "customer_notify": 1,
        "total_count": 12,
        "customer_email":data.customer_email,
        "notes": {
            "db_plan_id":db_plan.id,
            "customer_id": customer["id"]
        }
    })


    return {
        "customer_id": customer["id"],
        "subscription_id": subscription["id"],
        "short_url": subscription["short_url"],
        "plan_name": plan["item"]["name"],
    }



@router.post("/webhook")
async def webhook(request: Request):
    import json
    body = await request.json()

    event = body.get("event")

    if event == "subscription.activated":
        sub = body["payload"]["subscription"]["entity"]

        owner_id = sub["notes"]["owner_id"]
        plan_key = sub["notes"]["plan_key"]

        subscriptions_store[owner_id] = {
            "status": "active",
            "plan": plan_key,
            "subscription_id": sub["id"]
        }

        print("Stored:", subscriptions_store)

    return {"status": "ok"}



owners_store = {}

# 🔥 1. Create Owner
@router.post("/admin/create-owner")
def create_owner(data: dict):
    owner_id = len(owners_store) + 1

    owners_store[owner_id] = {
        "name": data["name"],
        "email": data["email"],
        "phone": data["phone"],
        "account_id": None,
        "kyc_status": "pending",
        "docs": []
    }

    return {"owner_id": owner_id}


# 🔥 2. Upload Documents
@router.post("/admin/upload-doc/{owner_id}")
async def upload_doc(owner_id: int, file: UploadFile = File(...)):
    path = f"uploads/{owner_id}_{file.filename}"

    with open(path, "wb") as f:
        f.write(await file.read())

    owners_store[owner_id]["docs"].append(path)

    return {"message": "uploaded"}


# 🔥 3. Create Razorpay Sub Account
@router.post("/admin/create-subaccount/{owner_id}")
def create_subaccount(owner_id: int):
    owner = owners_store.get(owner_id)

    account = client.account.create({
        "email": owner["email"],
        "phone": owner["phone"],
        "type": "route",
        "reference_id": f"owner_{owner_id}",
        "legal_business_name": owner["name"],
        "business_type": "individual"
    })

    owners_store[owner_id]["account_id"] = account["id"]

    return {"account_id": account["id"]}


# 🔥 4. Add Bank Details
@router.post("/admin/add-bank/{owner_id}")
def add_bank(owner_id: int, data: dict):
    account_id = owners_store[owner_id]["account_id"]

    client.fund_account.create({
        "account_type": "bank_account",
        "bank_account": {
            "name": data["name"],
            "ifsc": data["ifsc"],
            "account_number": data["account_number"]
        },
        "contact_id": account_id
    })

    owners_store[owner_id]["kyc_status"] = "approved"

    return {"message": "Bank added"}