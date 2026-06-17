from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import secrets
import json
import re
import uuid

from fastapi import Depends, HTTPException
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from core.database import get_db
from modules.subcriptions.models import Plan, Subscriptions



def create_plans(plans):
    plans_data = plans.get("items", [])
    for plan in plans_data:
        db = next(get_db())
        # Check if the plan already exists in the database
        existing_plan = db.query(Plan).filter(Plan.name == plan["item"]["name"]).first()
        if existing_plan:
            continue  # Skip if the plan already exists
        duration_months = 0
        if plan["period"] == 'monthly':
            duration_months = 1
        elif plan["period"] == "yearly":
            duration_months = 12

        new_plan = Plan(
            name=plan["item"]["name"],
            plan_id=plan["id"],
            description=plan["item"]["description"],
            price=plan["item"]["amount"],
            duration_months=duration_months,  # Convert seconds to months
            features=plan["item"].get("features", [])
        )
        db.add(new_plan)
        db.commit()
        db.refresh(new_plan)


def create_subscription(subscription_data: Dict[str, Any], owner_id: int):
    db = next(get_db())
    get_plan = db.query(Plan).filter(Plan.plan_id == subscription_data["plan_id"]).first()
    subscription = Subscriptions(
        plan_id=get_plan.id,
        subscription_id=subscription_data["id"],
        owner_id=owner_id,
        customer_id=subscription_data["notes"]["customer_id"],
        start_date=datetime.fromtimestamp(subscription_data["start_at"]),
        end_date=datetime.fromtimestamp(subscription_data["end_at"]),
        is_active=subscription_data["status"] == "active"
    )
    db = next(get_db())
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription
