import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_business, get_current_user
from app.models.business import Business
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.onboarding import (
    OnboardingAnswers,
    SaveDraftRequest,
    RecommendationResponse,
    CompleteOnboardingRequest,
    OnboardingStateResponse,
    BusinessProfileResponse,
    UpdatePreferencesRequest,
)
from app.services.recommendation import calculate_recommendation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Onboarding & Business Profile"])


@router.get("/onboarding", response_model=ApiResponse[OnboardingStateResponse])
def get_onboarding_state(
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves current onboarding progress, draft answers, and recommendation
    for the authenticated business tenant.
    """
    raw_answers = current_business.onboarding_answers or {}
    # Populate sensible defaults from business record if not in draft
    if "business_name" not in raw_answers:
        raw_answers["business_name"] = current_business.name
    if "category" not in raw_answers and current_business.category:
        raw_answers["category"] = current_business.category
    if "preferred_language" not in raw_answers:
        raw_answers["preferred_language"] = current_business.default_language or "ta"

    try:
        answers = OnboardingAnswers(**raw_answers)
    except Exception:
        answers = OnboardingAnswers(business_name=current_business.name)

    state = OnboardingStateResponse(
        business_id=current_business.id,
        business_name=current_business.name,
        onboarding_completed=current_business.onboarding_completed,
        current_step=current_business.onboarding_step,
        answers=answers,
        recommended_tier=current_business.recommended_tier,
        selected_tier=current_business.tier,
        enabled_modules=current_business.enabled_modules or [],
        reasons=current_business.recommendation_reasons or [],
    )
    return ApiResponse(data=state)


@router.put("/onboarding/draft", response_model=ApiResponse[OnboardingStateResponse])
def save_onboarding_draft(
    req: SaveDraftRequest,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
):
    """
    Persists step-by-step draft answers so users can pause, refresh, or resume
    the questionnaire without losing data.
    """
    answers_dict = req.answers.model_dump()
    current_business.onboarding_answers = answers_dict
    current_business.onboarding_step = req.step

    if req.answers.business_name and req.answers.business_name.strip():
        current_business.name = req.answers.business_name.strip()
    if req.answers.category:
        current_business.category = req.answers.category
    if req.answers.preferred_language:
        current_business.default_language = req.answers.preferred_language

    db.add(current_business)
    db.commit()
    db.refresh(current_business)

    state = OnboardingStateResponse(
        business_id=current_business.id,
        business_name=current_business.name,
        onboarding_completed=current_business.onboarding_completed,
        current_step=current_business.onboarding_step,
        answers=req.answers,
        recommended_tier=current_business.recommended_tier,
        selected_tier=current_business.tier,
        enabled_modules=current_business.enabled_modules or [],
        reasons=current_business.recommendation_reasons or [],
    )
    return ApiResponse(data=state)


@router.post("/onboarding/recommend", response_model=ApiResponse[RecommendationResponse])
def get_recommendation(
    answers: OnboardingAnswers,
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
):
    """
    Calculates a deterministic and explainable recommendation based on
    the provided questionnaire answers.
    """
    rec_result = calculate_recommendation(answers.model_dump())
    return ApiResponse(data=RecommendationResponse(**rec_result))


@router.post("/onboarding/complete", response_model=ApiResponse[BusinessProfileResponse])
def complete_onboarding(
    req: CompleteOnboardingRequest,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
):
    """
    Finalizes onboarding for the business. Applies the owner's selected tier
    (or recommendation), enables approved modules, updates operational counts,
    and sets onboarding_completed to True inside an atomic database transaction.
    """
    # Use submitted answers or fall back to saved draft
    answers_dict = (
        req.answers.model_dump()
        if req.answers
        else (current_business.onboarding_answers or {})
    )

    # Calculate deterministic recommendation for record-keeping
    rec_result = calculate_recommendation(answers_dict)

    # Validate selected modules against available list or default to recommendation
    final_modules = req.enabled_modules or rec_result["recommended_modules"]

    try:
        current_business.tier = req.selected_tier
        current_business.recommended_tier = rec_result["recommended_tier"]
        current_business.recommendation_reasons = rec_result["reasons"]
        current_business.enabled_modules = final_modules
        current_business.onboarding_completed = True
        current_business.onboarding_step = 11  # Completed
        current_business.onboarding_answers = answers_dict

        if req.answers:
            if req.answers.business_name and req.answers.business_name.strip():
                current_business.name = req.answers.business_name.strip()
            if req.answers.category:
                current_business.category = req.answers.category
            current_business.workforce_count = req.answers.workforce_count
            current_business.app_users_count = req.answers.app_users_count
            current_business.branch_count = req.answers.branch_count
            current_business.warehouse_count = req.answers.warehouse_count
            current_business.operations = req.answers.operations
            current_business.default_language = req.answers.preferred_language
            current_business.accessibility_settings = req.answers.accessibility

        db.add(current_business)
        db.commit()
        db.refresh(current_business)
    except Exception as e:
        db.rollback()
        logger.exception(f"Error completing onboarding for business {current_business.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "ONBOARDING_COMPLETION_FAILED", "message": f"Failed to complete onboarding: {str(e)}"},
        )

    profile = BusinessProfileResponse.model_validate(current_business)
    return ApiResponse(data=profile)


@router.get("/business/profile", response_model=ApiResponse[BusinessProfileResponse])
def get_business_profile(
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves the full profile and configured experience for the authenticated tenant.
    """
    profile = BusinessProfileResponse.model_validate(current_business)
    return ApiResponse(data=profile)


@router.put("/business/preferences", response_model=ApiResponse[BusinessProfileResponse])
def update_business_preferences(
    req: UpdatePreferencesRequest,
    db: Session = Depends(get_db),
    current_business: Business = Depends(get_current_business),
    current_user: User = Depends(get_current_user),
):
    """
    Allows the owner to revisit and update operational preferences, tier,
    language, enabled modules, and accessibility settings.
    """
    try:
        if req.category is not None:
            current_business.category = req.category
        if req.tier is not None:
            current_business.tier = req.tier
        if req.default_language is not None:
            current_business.default_language = req.default_language
        if req.enabled_modules is not None:
            current_business.enabled_modules = req.enabled_modules
        if req.accessibility_settings is not None:
            current_business.accessibility_settings = req.accessibility_settings

        db.add(current_business)
        db.commit()
        db.refresh(current_business)
    except Exception as e:
        db.rollback()
        logger.exception(f"Error updating preferences for business {current_business.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "PREFERENCES_UPDATE_FAILED", "message": str(e)},
        )

    profile = BusinessProfileResponse.model_validate(current_business)
    return ApiResponse(data=profile)
