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


router = APIRouter(prefix="/razorpay", tags=["Authentication"])


RAZORPAY_KEY_ID = settings.RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET = settings.RAZORPAY_KEY_SECRET


@router.get("/plans")
def get_plans():
    url = "https://api.razorpay.com/v1/plans"

    response = requests.get(
        url,
        auth=HTTPBasicAuth(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
    )

    if response.status_code != 200:
        return {"error": response.text}

    return response.json()


@router.get("/subscriptions")
def get_subscriptions():
    url = "https://api.razorpay.com/v1/subscriptions"

    response = requests.get(
        url,
        auth=HTTPBasicAuth(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
    )

    if response.status_code != 200:
        return {"error": response.text}

    return response.json()

@router.get("/my-subscriptions/{owner_id}")
def get_user_subscriptions(owner_id: str):
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





# RAZORPAY_KEY_ID = "rzp_test_SlaqMb6ab1wheq"
# RAZORPAY_KEY_SECRET = "KuZgMkHtrNeC3CSd1VYeXx2Z"
import razorpay
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


subscriptions_store = {}

@router.post("/create-subscription")
def create_subscription(data: dict):
    plan_key = data["plan_key"] 
    owner_id = data["owner_id"] 
    plans = get_plans()
    plan = next((p for p in plans if p["key"] == plan_key), None)

    if not plan:
        return {"error": "Invalid plan"}

    subscription = client.subscription.create({
        "plan_id": plan["plan_id"],
        "customer_notify": 1,
        "total_count": 12,
        "notes": {
            "owner_id": owner_id,
        }
    })

    return {
        "subscription_id": subscription["id"],
        "plan_name": plan["name"]
    }


from pydantic import BaseModel
from typing import Optional, Dict, Any


class SubscriptionEntity(BaseModel):
    id: str
    plan_id: Optional[str]
    status: Optional[str]
    notes: Optional[Dict[str, Any]]


class SubscriptionPayload(BaseModel):
    entity: SubscriptionEntity


class Payload(BaseModel):
    subscription: Optional[SubscriptionPayload]


class RazorpayWebhook(BaseModel):
    event: str
    payload: Payload

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