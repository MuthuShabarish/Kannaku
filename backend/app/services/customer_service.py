import uuid
from decimal import Decimal, ROUND_HALF_EVEN
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, desc, asc
from fastapi import HTTPException, status

from app.models.customer import Customer, CustomerLedgerEntry
from app.models.sales import Payment
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerPaymentCreate

TWO_PLACES = Decimal("0.01")
FOUR_PLACES = Decimal("0.0001")


def create_customer(db: Session, business_id: uuid.UUID, req: CustomerCreate) -> Customer:
    """Creates a new customer scoped to the tenant business. Enforces unique phone per business."""
    clean_phone = req.phone.strip().replace(" ", "").replace("-", "")
    existing = (
        db.query(Customer)
        .filter(Customer.business_id == business_id, Customer.phone == clean_phone)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CUSTOMER_PHONE_EXISTS",
                "message": f"Customer with phone number '{clean_phone}' already exists in your business.",
                "field": "phone"
            }
        )

    customer = Customer(
        business_id=business_id,
        name=req.name.strip(),
        phone=clean_phone,
        email=req.email.strip().lower() if req.email else None,
        address=req.address.strip() if req.address else None,
        credit_limit=req.credit_limit.quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN),
        current_balance=Decimal("0.0000"),
        is_active=True
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def list_customers(
    db: Session,
    business_id: uuid.UUID,
    search: Optional[str] = None,
    with_balance_only: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0
) -> Tuple[List[Customer], int]:
    """Lists customers for a business with optional search and debt filtering."""
    query = db.query(Customer).filter(Customer.business_id == business_id)

    if search:
        s = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(Customer.name).ilike(s),
                Customer.phone.ilike(s),
                func.lower(Customer.email).ilike(s)
            )
        )

    if with_balance_only:
        query = query.filter(Customer.current_balance > Decimal("0.0000"))

    total_count = query.count()
    items = query.order_by(Customer.name.asc()).offset(offset).limit(limit).all()
    return items, total_count


def get_customer_detail(
    db: Session,
    business_id: uuid.UUID,
    customer_id: uuid.UUID
) -> dict:
    """Returns detailed customer profile with recent Khata ledger transactions."""
    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.business_id == business_id)
        .first()
    )
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CUSTOMER_NOT_FOUND", "message": "Customer not found."}
        )

    entries = (
        db.query(CustomerLedgerEntry)
        .filter(CustomerLedgerEntry.customer_id == customer_id, CustomerLedgerEntry.business_id == business_id)
        .order_by(CustomerLedgerEntry.created_at.desc())
        .limit(50)
        .all()
    )

    return {
        "id": customer.id,
        "business_id": customer.business_id,
        "name": customer.name,
        "phone": customer.phone,
        "email": customer.email,
        "address": customer.address,
        "credit_limit": customer.credit_limit,
        "current_balance": customer.current_balance,
        "is_active": customer.is_active,
        "created_at": customer.created_at,
        "updated_at": customer.updated_at,
        "recent_entries": entries
    }


def update_customer(
    db: Session,
    business_id: uuid.UUID,
    customer_id: uuid.UUID,
    req: CustomerUpdate
) -> Customer:
    """Updates customer details, checking unique phone within business."""
    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.business_id == business_id)
        .first()
    )
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CUSTOMER_NOT_FOUND", "message": "Customer not found."}
        )

    if req.phone is not None:
        clean_phone = req.phone.strip().replace(" ", "").replace("-", "")
        existing = (
            db.query(Customer)
            .filter(
                Customer.business_id == business_id,
                Customer.id != customer_id,
                Customer.phone == clean_phone
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "CUSTOMER_PHONE_EXISTS",
                    "message": f"Customer with phone number '{clean_phone}' already exists.",
                    "field": "phone"
                }
            )
        customer.phone = clean_phone

    if req.name is not None:
        customer.name = req.name.strip()
    if req.email is not None:
        customer.email = req.email.strip().lower() if req.email else None
    if req.address is not None:
        customer.address = req.address.strip() if req.address else None
    if req.credit_limit is not None:
        customer.credit_limit = req.credit_limit.quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
    if req.is_active is not None:
        customer.is_active = req.is_active

    db.commit()
    db.refresh(customer)
    return customer


def record_customer_payment(
    db: Session,
    business_id: uuid.UUID,
    customer_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    req: CustomerPaymentCreate
) -> Tuple[Customer, CustomerLedgerEntry]:
    """
    Records a payment against customer's outstanding balance (Khata settlement).
    Uses pessimistic row-locking on Customer to guarantee exact balance tracking without race conditions.
    """
    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.business_id == business_id)
        .with_for_update()
        .first()
    )
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CUSTOMER_NOT_FOUND", "message": "Customer not found."}
        )

    if not customer.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "CUSTOMER_INACTIVE", "message": "Cannot record payment for an inactive customer."}
        )

    payment_amount = req.amount.quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
    if payment_amount <= Decimal("0.0000"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_AMOUNT", "message": "Payment amount must be greater than zero."}
        )

    if customer.current_balance <= Decimal("0.0000"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "NO_OUTSTANDING_BALANCE",
                "message": f"Customer '{customer.name}' has no outstanding credit balance to settle.",
                "current_balance": str(customer.current_balance)
            }
        )

    if payment_amount > customer.current_balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "SETTLEMENT_EXCEEDS_BALANCE",
                "message": f"Payment amount {payment_amount} exceeds customer's outstanding balance of {customer.current_balance}.",
                "current_balance": str(customer.current_balance),
                "payment_amount": str(payment_amount)
            }
        )

    try:
        # Calculate new balance: payment decreases debt
        new_balance = (customer.current_balance - payment_amount).quantize(FOUR_PLACES, rounding=ROUND_HALF_EVEN)
        customer.current_balance = new_balance

        # Record Payment inflow
        payment = Payment(
            business_id=business_id,
            sale_id=None,
            customer_id=customer_id,
            payment_direction="inflow",
            payment_mode=req.payment_mode,
            amount=payment_amount,
            notes=req.notes.strip() if req.notes else "Khata balance payment",
            created_by_user_id=user_id
        )
        db.add(payment)
        db.flush()

        # Record Customer Ledger Entry
        entry = CustomerLedgerEntry(
            business_id=business_id,
            customer_id=customer_id,
            entry_type="payment_received",
            reference_id=payment.id,
            amount=payment_amount,
            balance_after=new_balance,
            notes=req.notes.strip() if req.notes else f"Payment received via {req.payment_mode.upper()}",
            created_by_user_id=user_id
        )
        db.add(entry)

        db.commit()
        db.refresh(customer)
        db.refresh(entry)
        return customer, entry
    except Exception:
        db.rollback()
        raise

