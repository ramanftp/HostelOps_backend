from celery import shared_task
from datetime import datetime
from sqlalchemy import extract
from sqlalchemy.orm import Session
from core.database import SessionLocal
from modules.owner.models import Tenant
from modules.bill_payment.models import Bill
import uuid
from calendar import monthrange

@shared_task(name="tasks.generate_monthly_bills")
def generate_monthly_bills():
    db = SessionLocal()

    today = datetime.now().date()

    tenants = db.query(Tenant).filter(
        Tenant.active == True
    ).all()

    for tenant in tenants:

        join_date = tenant.join_date.date()
        join_day = join_date.day

        # current month last day
        last_day = monthrange(today.year, today.month)[1]

        # billing day = same join day or month end fallback
        billing_day = min(join_day, last_day)

        if today.day == billing_day:

            existing = db.query(Bill).filter(
                Bill.tenant_id == tenant.id,
                extract('year', Bill.created_at) == today.year,
                extract('month', Bill.created_at) == today.month
            ).first()

            if existing:
                continue

            bill = Bill(
                hostel_id=tenant.hostel_id,
                tenant_id=tenant.id,
                bill_number=str(uuid.uuid4()),
                amount=tenant.rent or 0,
                due_date=datetime(today.year, today.month, billing_day),
                description=f"Rent Bill - {today.strftime('%B %Y')}",
                status="pending"
            )

            db.add(bill)

    db.commit()
    db.close()