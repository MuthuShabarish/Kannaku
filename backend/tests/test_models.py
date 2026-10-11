import uuid
import pytest
from sqlalchemy.exc import IntegrityError
from app.models.business import Business, Branch, Warehouse
from app.models.user import User


def test_business_and_relationships(db):
    biz = Business(
        name="Kanakku Test Store",
        category="Retail",
        currency_code="INR",
        currency_symbol="₹"
    )
    db.add(biz)
    db.commit()

    branch = Branch(business_id=biz.id, name="Main Counter", code="BR-01")
    db.add(branch)
    db.commit()

    warehouse = Warehouse(business_id=biz.id, branch_id=branch.id, name="Main Store")
    db.add(warehouse)
    db.commit()

    user = User(
        business_id=biz.id,
        phone="+919876543210",
        full_name="Murugan",
        password_hash="test_hash",
        role="owner"
    )
    db.add(user)
    db.commit()

    # Verify relationships
    assert len(biz.branches) == 1
    assert len(biz.warehouses) == 1
    assert len(biz.users) == 1
    assert biz.branches[0].name == "Main Counter"


def test_unique_phone_constraint(db):
    biz = Business(name="Biz A")
    db.add(biz)
    db.commit()

    user1 = User(
        business_id=biz.id,
        phone="+919000000001",
        full_name="User 1",
        password_hash="hash1"
    )
    db.add(user1)
    db.commit()

    user2 = User(
        business_id=biz.id,
        phone="+919000000001",  # Same phone
        full_name="User 2",
        password_hash="hash2"
    )
    db.add(user2)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
