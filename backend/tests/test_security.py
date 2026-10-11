import pytest
from decimal import Decimal
from app.utils.security import normalize_phone, hash_password, verify_password
from app.utils.currency import to_decimal, round_banker, round_cash_tender, format_currency
from app.services.rate_limiter import DualKeyRateLimiter


def test_phone_normalization():
    # Standard 10-digit Indian numbers
    assert normalize_phone("9876543210") == "+919876543210"
    assert normalize_phone(" 98765 43210 ") == "+919876543210"
    assert normalize_phone("9876-543-210") == "+919876543210"
    assert normalize_phone("09876543210") == "+919876543210"

    # Already formatted E.164
    assert normalize_phone("+919876543210") == "+919876543210"
    assert normalize_phone("+14155552671") == "+14155552671"

    # Invalid phone numbers
    with pytest.raises(ValueError):
        normalize_phone("123")  # too short
    with pytest.raises(ValueError):
        normalize_phone("abcdefghij")  # non-digits


def test_argon2id_hashing():
    pin = "8520"
    hashed = hash_password(pin)

    # Hash should never be equal to plaintext
    assert hashed != pin
    assert "$argon2id$" in hashed

    # Valid verification
    assert verify_password(pin, hashed) is True

    # Invalid verification
    assert verify_password("9999", hashed) is False
    assert verify_password("8521", hashed) is False


def test_rate_limiter_lockout():
    limiter = DualKeyRateLimiter()
    ip = "192.168.1.50"
    phone = "+919876543210"

    # 4 failed attempts should not lock out
    for _ in range(4):
        failures, is_locked, _ = limiter.record_failure(ip, phone)
        assert is_locked is False

    # 5th attempt must lock out
    failures, is_locked, remaining = limiter.record_failure(ip, phone)
    assert is_locked is True
    assert remaining > 0

    # check_lockout should now report locked
    locked, rem = limiter.check_lockout(ip, phone)
    assert locked is True
    assert rem > 0

    # Reset on success
    limiter.reset_failures(ip, phone)
    locked_after, _ = limiter.check_lockout(ip, phone)
    assert locked_after is False


def test_currency_banker_rounding():
    # 2.5 rounded to even integer is 2, 3.5 rounded to even integer is 4
    # With 2 decimals:
    # 1.005 -> 1.00 (half to even)
    # 1.015 -> 1.02 (half to even)
    assert round_banker(Decimal("1.005"), places=2) == Decimal("1.00")
    assert round_banker(Decimal("1.015"), places=2) == Decimal("1.02")
    assert round_banker(Decimal("1.025"), places=2) == Decimal("1.02")
    assert round_banker(Decimal("1.035"), places=2) == Decimal("1.04")


def test_currency_formatting():
    assert format_currency(Decimal("1250.50"), symbol="₹") == "₹1,250.50"
    assert format_currency(Decimal("500000.00"), symbol="₹") == "₹500,000.00"
    assert round_cash_tender(Decimal("149.80"), round_to_nearest_integer=True) == Decimal("150")
