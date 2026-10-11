import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
import jwt
from app.config import settings

# Argon2id hasher with recommended security parameters (64MB memory, 3 iterations, 4 lanes)
ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16
)


def hash_password(password_or_pin: str) -> str:
    """
    Hash a password or numeric PIN using Argon2id with unique cryptographic salt.
    Plaintext is NEVER stored or logged.
    """
    return ph.hash(password_or_pin)


def verify_password(plain_password_or_pin: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password or numeric PIN against its Argon2id hash.
    Constant-time comparison prevents timing attacks.
    """
    try:
        return ph.verify(hashed_password, plain_password_or_pin)
    except (VerifyMismatchError, InvalidHashError):
        return False
    except Exception:
        return False


def normalize_phone(phone: str, default_country_code: str = "+91") -> str:
    """
    Normalize any phone input to E.164 standard (e.g., '+919876543210').
    Strips whitespace, dashes, brackets, and leading 0s.
    """
    if not phone:
        raise ValueError("Phone number cannot be empty")

    cleaned = re.sub(r"[\s\-\(\)\.]", "", phone.strip())

    if cleaned.startswith("+"):
        digits_only = cleaned[1:]
        if not digits_only.isdigit() or len(digits_only) < 7 or len(digits_only) > 15:
            raise ValueError(f"Invalid international phone number: {phone}")
        return cleaned

    # Strip leading 0
    if cleaned.startswith("0"):
        cleaned = cleaned[1:]

    if not cleaned.isdigit():
        raise ValueError(f"Phone number contains non-digit characters: {phone}")

    # If standard 10-digit Indian number, prepend default country code (+91)
    if len(cleaned) == 10:
        return f"{default_country_code}{cleaned}"
    elif len(cleaned) >= 7 and len(cleaned) <= 15:
        return f"{default_country_code}{cleaned}"
    else:
        raise ValueError(f"Invalid phone number length ({len(cleaned)} digits): {phone}")


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a short-lived signed JWT access token.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "jti": secrets.token_hex(16)
    })
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token() -> str:
    """
    Generate a high-entropy cryptographically random opaque refresh token (256-bit).
    """
    return secrets.token_urlsafe(32)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a signed JWT access token.
    Returns payload dictionary or None if invalid/expired.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
