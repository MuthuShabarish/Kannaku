from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user, get_current_business, get_client_ip
from app.models.user import User
from app.models.business import Business
from app.schemas.auth import (
    RegisterOwnerRequest,
    LoginRequest,
    UserProfile,
    BusinessProfile,
    TokenResponse,
    AuthMeResponse
)
from app.schemas.common import ApiResponse
from app.services.auth_service import register_owner, login_user
from app.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    req: RegisterOwnerRequest,
    response: Response,
    db: Session = Depends(get_db)
) -> ApiResponse[dict]:
    """
    Register a new business account and owner user via phone number and PIN.
    Issues JWT access token and sets HTTP-Only secure refresh token cookie.
    Generates a one-time Emergency Recovery Key for account safety.
    """
    user, business, access_token, refresh_token, recovery_key = register_owner(db, req)

    # Set secure HTTP-only refresh cookie
    response.set_cookie(
        key="kanakku_refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth/refresh"
    )

    return ApiResponse(
        success=True,
        data={
            "user": UserProfile.model_validate(user),
            "business": BusinessProfile.model_validate(business),
            "tokens": TokenResponse(
                access_token=access_token,
                token_type="bearer",
                expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                refresh_token=refresh_token
            ),
            "emergency_recovery_key": recovery_key
        }
    )


@router.post("/login")
def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
) -> ApiResponse[dict]:
    """
    Authenticate via registered phone number and PIN.
    Enforces dual-key rate limiting (Client IP + Phone) to prevent brute forcing.
    """
    client_ip = get_client_ip(request)
    user, business, access_token, refresh_token = login_user(db, req.phone, req.pin_or_password, client_ip)

    # Set secure HTTP-only refresh cookie
    response.set_cookie(
        key="kanakku_refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth/refresh"
    )

    return ApiResponse(
        success=True,
        data={
            "user": UserProfile.model_validate(user),
            "business": BusinessProfile.model_validate(business),
            "tokens": TokenResponse(
                access_token=access_token,
                token_type="bearer",
                expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                refresh_token=refresh_token
            )
        }
    )


@router.get("/me")
def get_me(
    current_user: User = Depends(get_current_user),
    current_business: Business = Depends(get_current_business)
) -> ApiResponse[AuthMeResponse]:
    """
    Returns the currently authenticated user profile and business context.
    Guarantees tenant isolation on the backend.
    """
    return ApiResponse(
        success=True,
        data=AuthMeResponse(
            user=UserProfile.model_validate(current_user),
            business=BusinessProfile.model_validate(current_business)
        )
    )


@router.post("/logout")
def logout(response: Response) -> ApiResponse[dict]:
    """
    Clears the refresh token cookie upon logout.
    """
    response.delete_cookie(
        key="kanakku_refresh_token",
        path="/api/v1/auth/refresh"
    )
    return ApiResponse(
        success=True,
        data={"message": "Successfully logged out"}
    )
