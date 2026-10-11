import uuid
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from app.utils.security import normalize_phone


class RegisterOwnerRequest(BaseModel):
    phone: str = Field(..., description="Phone number in local or E.164 format")
    pin_or_password: str = Field(..., min_length=4, max_length=128, description="4-6 digit numeric PIN or password")
    full_name: str = Field(..., min_length=2, max_length=255, description="Full name of owner")
    business_name: str = Field(..., min_length=2, max_length=255, description="Name of business")
    category: Optional[str] = Field(None, description="Business category (e.g. Grocery, Fruits, Hardware)")
    currency_code: str = Field("INR", max_length=10, description="ISO Currency code")
    currency_symbol: str = Field("₹", max_length=5, description="Currency symbol")
    default_language: str = Field("ta", max_length=10, description="Preferred UI language (ta, tanglish, en)")

    @field_validator("phone")
    @classmethod
    def validate_and_normalize_phone(cls, v: str) -> str:
        try:
            return normalize_phone(v)
        except ValueError as e:
            raise ValueError(str(e))

    @field_validator("pin_or_password")
    @classmethod
    def validate_pin_entropy(cls, v: str) -> str:
        # Check against trivial repetitive pins if purely digits
        if v.isdigit():
            if len(v) < 4:
                raise ValueError("PIN must be at least 4 digits")
            if len(set(v)) == 1:
                raise ValueError("PIN cannot be repetitive digits (e.g., 0000, 1111)")
            if v in ["1234", "4321", "12345", "123456"]:
                raise ValueError("PIN is too simple; avoid sequential numbers")
        return v


class LoginRequest(BaseModel):
    phone: str = Field(..., description="Registered phone number")
    pin_or_password: str = Field(..., description="PIN or password")

    @field_validator("phone")
    @classmethod
    def validate_and_normalize_phone(cls, v: str) -> str:
        try:
            return normalize_phone(v)
        except ValueError as e:
            raise ValueError(str(e))


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    refresh_token: Optional[str] = None


class UserProfile(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    phone: str
    full_name: str
    role: str
    preferred_language: str
    is_active: bool

    class Config:
        from_attributes = True


class BusinessProfile(BaseModel):
    id: uuid.UUID
    name: str
    category: Optional[str] = None
    tier: str
    recommended_tier: Optional[str] = None
    currency_code: str
    currency_symbol: str
    default_language: str
    onboarding_completed: bool = False
    onboarding_step: int = 1
    enabled_modules: list[str] = []
    is_active: bool

    class Config:
        from_attributes = True


class AuthMeResponse(BaseModel):
    user: UserProfile
    business: BusinessProfile
