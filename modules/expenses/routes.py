from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from modules.owner.security import get_current_owner
from modules.owner.models import Hostel

from . import services
from .schema import ExpenseCreate, ExpenseUpdate, ExpenseOut

router = APIRouter(prefix="/expenses", tags=["Expenses"])


# ============================================================================
# Expense Management Endpoints
# ============================================================================

@router.get("/", response_model=List[ExpenseOut], tags=["Expenses"])
def get_hostel_expenses(
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Get all expenses for the owner's hostels"""
    # Get all hostels owned by the current owner
    hostels = db.query(Hostel).filter(Hostel.owner_id == current_owner["id"]).all()
    hostel_ids = [hostel.id for hostel in hostels]

    if not hostel_ids:
        return []

    expenses = []
    for hostel_id in hostel_ids:
        expenses.extend(services.get_expenses_by_hostel(db, hostel_id))

    return expenses


@router.get("/hostel/{hostel_id}", response_model=List[ExpenseOut], tags=["Expenses"])
def get_expenses_by_hostel(
    hostel_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Get all expenses for a specific hostel"""
    # Verify ownership
    hostel = db.query(Hostel).filter(Hostel.id == hostel_id, Hostel.owner_id == current_owner["id"]).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Hostel not found or access denied")

    return services.get_expenses_by_hostel(db, hostel_id)


@router.get("/{expense_id}", response_model=ExpenseOut, tags=["Expenses"])
def get_expense(
    expense_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Get a specific expense by ID"""
    expense = services.get_expense(db, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    # Verify ownership through hostel
    hostel = db.query(Hostel).filter(Hostel.id == expense.hostel_id, Hostel.owner_id == current_owner["id"]).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Expense not found or access denied")

    return expense


@router.post("/", response_model=ExpenseOut, tags=["Expenses"])
def create_expense(
    expense: ExpenseCreate,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Create a new expense"""
    # Verify ownership of the hostel
    hostel = db.query(Hostel).filter(Hostel.id == expense.hostel_id, Hostel.owner_id == current_owner["id"]).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Hostel not found or access denied")

    # Set created_by to current owner
    expense.created_by = current_owner["id"]

    return services.create_expense(db, expense)


@router.put("/{expense_id}", response_model=ExpenseOut, tags=["Expenses"])
def update_expense(
    expense_id: int,
    expense_update: ExpenseUpdate,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Update an existing expense"""
    expense = services.get_expense(db, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    # Verify ownership through hostel
    hostel = db.query(Hostel).filter(Hostel.id == expense.hostel_id, Hostel.owner_id == current_owner["id"]).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Expense not found or access denied")

    updated_expense = services.update_expense(db, expense_id, expense_update)
    if not updated_expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    return updated_expense


@router.delete("/{expense_id}", tags=["Expenses"])
def delete_expense(
    expense_id: int,
    current_owner: dict = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Delete an expense"""
    expense = services.get_expense(db, expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    # Verify ownership through hostel
    hostel = db.query(Hostel).filter(Hostel.id == expense.hostel_id, Hostel.owner_id == current_owner["id"]).first()
    if not hostel:
        raise HTTPException(status_code=404, detail="Expense not found or access denied")

    if not services.delete_expense(db, expense_id):
        raise HTTPException(status_code=404, detail="Expense not found")

    return {"message": "Expense deleted successfully"}