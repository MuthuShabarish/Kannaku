import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.business import Business, Branch, Warehouse
from app.models.user import User, RefreshToken
from app.schemas.auth import RegisterOwnerRequest
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token
)
from app.services.rate_limiter import login_rate_limiter
from app.config import settings


def register_owner(db: Session, req: RegisterOwnerRequest):
    """
    Registers a new business owner, the primary business tenant,
    default branch, default warehouse, and emergency recovery key.
    """
    # 1. Check if phone is already registered
    existing_user = db.query(User).filter(User.phone == req.phone).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "PHONE_ALREADY_REGISTERED",
                "message": f"Phone number {req.phone} is already registered. Please log in.",
                "field": "phone"
            }
        )

    # 2. Generate Emergency Recovery Key (16 hex chars)
    raw_recovery_key = secrets.token_hex(8).upper()
    recovery_key_hash = hash_password(raw_recovery_key)

    # 3. Create Business Entity
    business = Business(
        name=req.business_name.strip(),
        category=req.category.strip() if req.category else None,
        tier="simple",
        currency_code=req.currency_code.strip().upper(),
        currency_symbol=req.currency_symbol.strip(),
        default_language=req.default_language.strip(),
        emergency_recovery_key_hash=recovery_key_hash,
        settings={
            "onboarding_completed": False,
            "created_via": "stage1_foundation"
        }
    )
    db.add(business)
    db.flush()  # Generate business.id

    # 4. Create Main Branch
    branch = Branch(
        business_id=business.id,
        name="Main Store",
        code="BR-01",
        is_main=True,
        is_active=True
    )
    db.add(branch)
    db.flush()

    # 5. Create Default Warehouse
    warehouse = Warehouse(
        business_id=business.id,
        branch_id=branch.id,
        name="Main Counter",
        is_default=True,
        is_active=True
    )
    db.add(warehouse)

    # 6. Create Owner User
    hashed_pwd = hash_password(req.pin_or_password)
    user = User(
        business_id=business.id,
        phone=req.phone,
        full_name=req.full_name.strip(),
        password_hash=hashed_pwd,
        role="owner",
        preferred_language=req.default_language.strip(),
        is_active=True
    )
    db.add(user)
    db.flush()

    # 7. Generate Session Tokens
    access_token = create_access_token({
        "sub": str(user.id),
        "biz": str(business.id),
        "phone": user.phone,
        "role": user.role
    })
    raw_refresh_token = create_refresh_token()
    refresh_hash = hashlib.sha256(raw_refresh_token.encode()).hexdigest()

    refresh_entity = RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(refresh_entity)

    db.commit()
    db.refresh(user)
    db.refresh(business)

    return user, business, access_token, raw_refresh_token, raw_recovery_key


def login_user(db: Session, phone: str, pin_or_password: str, client_ip: str):
    """
    Authenticates a user via phone and PIN/password with dual-key rate limiting.
    """
    # 1. Check rate limiter lockout
    is_locked, remaining_seconds = login_rate_limiter.check_lockout(client_ip, phone)
    if is_locked:
        minutes = (remaining_seconds // 60) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "ACCOUNT_TEMPORARILY_LOCKED",
                "message": f"Too many failed attempts. Try again in {minutes} minutes.",
                "remaining_seconds": remaining_seconds
            }
        )

    # 2. Look up user by normalized phone
    user = db.query(User).filter(User.phone == phone).first()
    if not user or not user.is_active:
        failures, now_locked, remaining = login_rate_limiter.record_failure(client_ip, phone)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Invalid phone number or PIN"
            }
        )

    # 3. Verify Argon2id password hash
    if not verify_password(pin_or_password, user.password_hash):
        failures, now_locked, remaining = login_rate_limiter.record_failure(client_ip, phone)
        if now_locked:
            minutes = (remaining // 60) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "ACCOUNT_TEMPORARILY_LOCKED",
                    "message": f"Too many failed attempts. Account locked for {minutes} minutes.",
                    "remaining_seconds": remaining
                }
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Invalid phone number or PIN"
            }
        )

    # 4. Success: Reset rate limiter failures
    login_rate_limiter.reset_failures(client_ip, phone)

    # 5. Fetch associated business
    business = db.query(Business).filter(Business.id == user.business_id).first()
    if not business or not business.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "BUSINESS_INACTIVE",
                "message": "Business account is inactive"
            }
        )

    # 6. Issue Tokens
    access_token = create_access_token({
        "sub": str(user.id),
        "biz": str(business.id),
        "phone": user.phone,
        "role": user.role
    })
    raw_refresh_token = create_refresh_token()
    refresh_hash = hashlib.sha256(raw_refresh_token.encode()).hexdigest()

    refresh_entity = RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(refresh_entity)
    db.commit()

    return user, business, access_token, raw_refresh_token
