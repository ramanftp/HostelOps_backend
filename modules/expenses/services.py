from typing import List, Optional
from sqlalchemy.orm import Session

from .models import Expense
from .schema import ExpenseCreate, ExpenseUpdate


def get_expenses_by_hostel(db: Session, hostel_id: int) -> List[Expense]:
    """Get all expenses for a hostel"""
    return db.query(Expense).filter(Expense.hostel_id == hostel_id).all()


def get_expense(db: Session, expense_id: int) -> Optional[Expense]:
    """Get a specific expense by ID"""
    return db.query(Expense).filter(Expense.id == expense_id).first()


def create_expense(db: Session, expense: ExpenseCreate) -> Expense:
    """Create a new expense"""
    db_expense = Expense(**expense.model_dump())
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense


def update_expense(db: Session, expense_id: int, expense_update: ExpenseUpdate) -> Optional[Expense]:
    """Update an existing expense"""
    db_expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not db_expense:
        return None

    update_data = expense_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_expense, field, value)

    db.commit()
    db.refresh(db_expense)
    return db_expense


def delete_expense(db: Session, expense_id: int) -> bool:
    """Delete an expense"""
    db_expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not db_expense:
        return False

    db.delete(db_expense)
    db.commit()
    return True