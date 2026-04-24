from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime

from .models import Bill, Transaction
from .schema import BillCreate, BillUpdate, TransactionCreate, TransactionUpdate


def get_bills_by_hostel(db: Session, hostel_id: int) -> List[Bill]:
    """Get all bills for a hostel"""
    return db.query(Bill).filter(Bill.hostel_id == hostel_id).all()


def get_bills_by_tenant(db: Session, tenant_id: int) -> List[Bill]:
    """Get all bills for a tenant"""
    return db.query(Bill).filter(Bill.tenant_id == tenant_id).all()


def get_bill(db: Session, bill_id: int) -> Optional[Bill]:
    """Get a specific bill by ID"""
    return db.query(Bill).filter(Bill.id == bill_id).first()


def create_bill(db: Session, bill: BillCreate) -> Bill:
    """Create a new bill"""
    db_bill = Bill(**bill.model_dump())
    db.add(db_bill)
    db.commit()
    db.refresh(db_bill)
    return db_bill


def update_bill(db: Session, bill_id: int, bill_update: BillUpdate) -> Optional[Bill]:
    """Update an existing bill"""
    db_bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not db_bill:
        return None
    
    update_data = bill_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_bill, field, value)
    
    db.commit()
    db.refresh(db_bill)
    return db_bill


def delete_bill(db: Session, bill_id: int) -> bool:
    """Delete a bill"""
    db_bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not db_bill:
        return False
    
    db.delete(db_bill)
    db.commit()
    return True


def get_transactions_by_bill(db: Session, bill_id: int) -> List[Transaction]:
    """Get all transactions for a bill"""
    return db.query(Transaction).filter(Transaction.bill_id == bill_id).all()


def get_transaction(db: Session, transaction_id: int) -> Optional[Transaction]:
    """Get a specific transaction by ID"""
    return db.query(Transaction).filter(Transaction.id == transaction_id).first()


def _reconcile_bill_status(db: Session, bill_id: int) -> None:
    """Recalculate bill status based on successful transactions and due date."""
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        return

    paid_amount = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.bill_id == bill_id,
        Transaction.status == "success"
    ).scalar() or 0

    if paid_amount >= bill.amount:
        bill.status = "paid"
    elif bill.due_date and bill.due_date < datetime.utcnow():
        bill.status = "overdue"
    else:
        bill.status = "pending"

    db.commit()
    db.refresh(bill)


def create_transaction(db: Session, transaction: TransactionCreate) -> Transaction:
    """Create a new transaction"""
    db_transaction = Transaction(**transaction.model_dump())
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)

    _reconcile_bill_status(db, db_transaction.bill_id)
    return db_transaction


def update_transaction(db: Session, transaction_id: int, transaction_update: TransactionUpdate) -> Optional[Transaction]:

    """Update an existing transaction"""
    db_transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not db_transaction:
        return None
    
    update_data = transaction_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_transaction, field, value)
    
    db.commit()
    db.refresh(db_transaction)

    _reconcile_bill_status(db, db_transaction.bill_id)
    return db_transaction


def delete_transaction(db: Session, transaction_id: int) -> bool:
    """Delete a transaction"""
    db_transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not db_transaction:
        return False
    
    db.delete(db_transaction)
    db.commit()
    return True


def get_overdue_bills(db: Session, hostel_id: Optional[int] = None) -> List[Bill]:
    """Get all overdue bills, optionally filtered by hostel"""
    query = db.query(Bill).filter(
        and_(
            Bill.status == "pending",
            Bill.due_date < datetime.utcnow()
        )
    )
    if hostel_id:
        query = query.filter(Bill.hostel_id == hostel_id)
    return query.all()


def get_pending_bills(db: Session, hostel_id: Optional[int] = None) -> List[Bill]:
    """Get all pending bills, optionally filtered by hostel"""
    query = db.query(Bill).filter(Bill.status == "pending")
    if hostel_id:
        query = query.filter(Bill.hostel_id == hostel_id)
    return query.all()