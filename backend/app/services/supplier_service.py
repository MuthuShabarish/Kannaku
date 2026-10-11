import uuid
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, desc, asc
from fastapi import HTTPException, status

from app.models.supplier import Supplier, SupplierLedgerEntry
from app.models.sales import Payment
from app.models.user import User
from app.schemas.supplier import SupplierCreate, SupplierUpdate, SupplierPaymentCreate

FOUR_PLACES = Decimal("0.0001")


def create_supplier(db: Session, business_id: uuid.UUID, req: SupplierCreate) -> Supplier:
    """Creates a new supplier scoped to the business tenant. Enforces unique name per business."""
    clean_name = req.name.strip()
    existing = (
        db.query(Supplier)
        .filter(
            Supplier.business_id == business_id,
            func.lower(Supplier.name) == clean_name.lower()
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "SUPPLIER_NAME_EXISTS",
                "message": f"Supplier with name '{clean_name}' already exists in your business.",
                "field": "name"
            }
        )

    supplier = Supplier(
        business_id=business_id,
        name=clean_name,
        phone=req.phone.strip() if req.phone else None,
        email=req.email.strip().lower() if req.email else None,
        address=req.address.strip() if req.address else None,
        notes=req.notes.strip() if req.notes else None,
        current_balance=Decimal("0.0000"),
        is_active=True
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


def list_suppliers(
    db: Session,
    business_id: uuid.UUID,
    search: Optional[str] = None,
    with_balance_only: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0
) -> Tuple[List[Supplier], int]:
    """Lists suppliers for a business with optional search and dues filtering."""
    query = db.query(Supplier).filter(Supplier.business_id == business_id)

    if search:
        s = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(Supplier.name).ilike(s),
                Supplier.phone.ilike(s),
                func.lower(Supplier.email).ilike(s)
            )
        )

    if with_balance_only:
        query = query.filter(Supplier.current_balance > Decimal("0.0000"))

    total_count = query.count()
    items = query.order_by(Supplier.name.asc()).offset(offset).limit(limit).all()
    return items, total_count


def get_supplier_detail(
    db: Session,
    business_id: uuid.UUID,
    supplier_id: uuid.UUID
) -> dict:
    """Returns detailed supplier profile with recent ledger transactions."""
    supplier = (
        db.query(Supplier)
        .filter(Supplier.id == supplier_id, Supplier.business_id == business_id)
        .first()
    )
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SUPPLIER_NOT_FOUND", "message": "Supplier not found."}
        )

    entries = (
        db.query(SupplierLedgerEntry)
        .filter(
            SupplierLedgerEntry.supplier_id == supplier_id,
            SupplierLedgerEntry.business_id == business_id
        )
        .order_by(SupplierLedgerEntry.created_at.desc())
        .limit(50)
        .all()
    )

    return {
        "id": supplier.id,
        "business_id": supplier.business_id,
        "name": supplier.name,
        "phone": supplier.phone,
        "email": supplier.email,
        "address": supplier.address,
        "notes": supplier.notes,
        "current_balance": supplier.current_balance,
        "is_active": supplier.is_active,
        "created_at": supplier.created_at,
        "updated_at": supplier.updated_at,
        "recent_entries": entries
    }


def update_supplier(
    db: Session,
    business_id: uuid.UUID,
    supplier_id: uuid.UUID,
    req: SupplierUpdate
) -> Supplier:
    """Updates supplier details, checking unique name within business."""
    supplier = (
        db.query(Supplier)
        .filter(Supplier.id == supplier_id, Supplier.business_id == business_id)
        .first()
    )
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SUPPLIER_NOT_FOUND", "message": "Supplier not found."}
        )

    if req.name is not None:
        clean_name = req.name.strip()
        existing = (
            db.query(Supplier)
            .filter(
                Supplier.business_id == business_id,
                Supplier.id != supplier_id,
                func.lower(Supplier.name) == clean_name.lower()
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "SUPPLIER_NAME_EXISTS",
                    "message": f"Supplier with name '{clean_name}' already exists.",
                    "field": "name"
                }
            )
        supplier.name = clean_name

    if req.phone is not None:
        supplier.phone = req.phone.strip() if req.phone else None
    if req.email is not None:
        supplier.email = req.email.strip().lower() if req.email else None
    if req.address is not None:
        supplier.address = req.address.strip() if req.address else None
    if req.notes is not None:
        supplier.notes = req.notes.strip() if req.notes else None
    if req.is_active is not None:
        supplier.is_active = req.is_active

    db.commit()
    db.refresh(supplier)
    return supplier


def record_supplier_payment(
    db: Session,
    business_id: uuid.UUID,
    supplier_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    req: SupplierPaymentCreate
) -> Tuple[Supplier, SupplierLedgerEntry]:
    """
    Records a payment made against a supplier's outstanding balance (AP settlement).
    Uses pessimistic row-locking on Supplier to guarantee exact balance tracking without race conditions.
    """
    supplier = (
        db.query(Supplier)
        .filter(Supplier.id == supplier_id, Supplier.business_id == business_id)
        .with_for_update()
        .first()
    )
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SUPPLIER_NOT_FOUND", "message": "Supplier not found."}
        )

    if not supplier.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SUPPLIER_INACTIVE", "message": "Cannot record payment for an inactive supplier."}
        )

    payment_amount = req.amount.quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
    if payment_amount <= Decimal("0.0000"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_AMOUNT", "message": "Payment amount must be greater than zero."}
        )

    if supplier.current_balance <= Decimal("0.0000"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "NO_OUTSTANDING_BALANCE",
                "message": f"Supplier '{supplier.name}' has no outstanding payable balance to settle.",
                "current_balance": str(supplier.current_balance)
            }
        )

    if payment_amount > supplier.current_balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "SETTLEMENT_EXCEEDS_BALANCE",
                "message": f"Payment amount {payment_amount} exceeds supplier's outstanding payable balance of {supplier.current_balance}.",
                "current_balance": str(supplier.current_balance),
                "payment_amount": str(payment_amount)
            }
        )

    try:
        # Calculate new balance: payment decreases our debt to supplier
        new_balance = (supplier.current_balance - payment_amount).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
        supplier.current_balance = new_balance

        # Record Payment outflow
        payment = Payment(
            business_id=business_id,
            sale_id=None,
            customer_id=None,
            purchase_id=None,
            supplier_id=supplier_id,
            payment_direction="outflow",
            payment_mode=req.payment_mode,
            amount=payment_amount,
            notes=req.notes.strip() if req.notes else "Supplier dues payment",
            created_by_user_id=user_id
        )
        db.add(payment)
        db.flush()

        # Record Supplier Ledger Entry
        entry = SupplierLedgerEntry(
            business_id=business_id,
            supplier_id=supplier_id,
            entry_type="payment_made",
            reference_id=payment.id,
            amount=payment_amount,
            balance_after=new_balance,
            notes=req.notes.strip() if req.notes else f"Payment made via {req.payment_mode.upper()}",
            created_by_user_id=user_id
        )
        db.add(entry)

        db.commit()
        db.refresh(supplier)
        db.refresh(entry)
        return supplier, entry
    except Exception:
        db.rollback()
        raise


def get_supplier_ledger(
    db: Session,
    business_id: uuid.UUID,
    supplier_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0
) -> Tuple[List[SupplierLedgerEntry], int]:
    """Returns paginated ledger entries for a specific supplier."""
    supplier = (
        db.query(Supplier)
        .filter(Supplier.id == supplier_id, Supplier.business_id == business_id)
        .first()
    )
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SUPPLIER_NOT_FOUND", "message": "Supplier not found."}
        )

    query = (
        db.query(SupplierLedgerEntry)
        .filter(
            SupplierLedgerEntry.supplier_id == supplier_id,
            SupplierLedgerEntry.business_id == business_id
        )
    )
    total_count = query.count()
    items = query.order_by(SupplierLedgerEntry.created_at.desc()).offset(offset).limit(limit).all()
    return items, total_count
