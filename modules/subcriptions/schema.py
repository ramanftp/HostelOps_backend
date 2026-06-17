import enum

from pydantic import BaseModel, Field, ConfigDict, json, validator
from typing import Optional, List
from datetime import datetime
import re



# Base schemas with ORM mode
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PlanCreate(BaseSchema):
    name: str
    plan_id: str
    description: Optional[str] = None
    price: int  # Price in cents
    duration_months: int  # Duration of the plan in months
    features: Optional[List[str]] = None  # List of features included in the plan

class PlanBase(BaseSchema):
    name: str
    description: Optional[str] = None
    price: int  # Price in cents
    duration_months: int  # Duration of the plan in months
    features: Optional[List[str]] = None  # List of features included in the plan


class SubscriptionCreate(BaseSchema):
    plan_key: str  # Key to identify the plan (e.g., "basic", "premium")
    subscription_id: Optional[str] = None  # Razorpay subscription ID
    customer_email:Optional[str] = None
    customer_name: Optional[str] = None
    customer_contact: Optional[str] = None
    owner_id: Optional[int] = None  # ID of the owner subscribing to the plan

class SubscriptionBase(BaseModel):
    status: Optional[str] = None
    plan: Optional[PlanBase] = None
    subscription_id: Optional[str] = None


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