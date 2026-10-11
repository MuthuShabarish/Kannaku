import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class OnboardingAnswers(BaseModel):
    business_name: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    workforce_count: int = Field(1, ge=1, le=10000)
    app_users_count: int = Field(1, ge=1, le=1000)
    branch_count: int = Field(1, ge=1, le=500)
    warehouse_count: int = Field(1, ge=0, le=500)
    operations: List[str] = Field(default_factory=lambda: ["retail"])
    tracks_inventory: bool = True
    purchase_orders: bool = False
    has_manufacturing: bool = False
    raw_materials: bool = False
    production_batches: bool = False
    scrap_wastage: bool = False
    track_customer_credit: bool = False
    track_supplier_payments: bool = False
    need_staff_permissions: bool = False
    need_approval_workflows: bool = False
    preferred_language: str = Field("ta", pattern="^(ta|tanglish|en)$")
    accessibility: Dict[str, Any] = Field(
        default_factory=lambda: {
            "high_contrast": False,
            "large_font": False,
            "simplified_ui": True
        }
    )

    @field_validator("operations")
    @classmethod
    def validate_operations(cls, v: List[str]) -> List[str]:
        valid = {"retail", "wholesale", "services", "manufacturing"}
        cleaned = [op.lower().strip() for op in v if op.lower().strip() in valid]
        return cleaned or ["retail"]


class SaveDraftRequest(BaseModel):
    step: int = Field(1, ge=1, le=11)
    answers: OnboardingAnswers


class RecommendationReason(BaseModel):
    code: str
    title_en: str
    title_ta: str
    title_tanglish: str
    desc_en: str
    desc_ta: str
    desc_tanglish: str


class ModuleInfo(BaseModel):
    id: str
    name_en: str
    name_ta: str
    name_tanglish: str
    description_en: str
    description_ta: str
    description_tanglish: str
    category: str
    tier: str


class RecommendationResponse(BaseModel):
    recommended_tier: str = Field(pattern="^(simple|growth|enterprise)$")
    complexity_score: int
    reasons: List[RecommendationReason]
    recommended_modules: List[str]
    available_modules: List[ModuleInfo]


class CompleteOnboardingRequest(BaseModel):
    selected_tier: str = Field(pattern="^(simple|growth|enterprise)$")
    enabled_modules: List[str] = Field(default_factory=list)
    answers: Optional[OnboardingAnswers] = None


class OnboardingStateResponse(BaseModel):
    business_id: uuid.UUID
    business_name: str
    onboarding_completed: bool
    current_step: int
    answers: OnboardingAnswers
    recommended_tier: Optional[str] = None
    selected_tier: str
    enabled_modules: List[str]
    reasons: List[RecommendationReason] = Field(default_factory=list)


class BusinessProfileResponse(BaseModel):
    id: uuid.UUID
    name: str
    category: Optional[str] = None
    tier: str
    recommended_tier: Optional[str] = None
    currency_code: str
    currency_symbol: str
    default_language: str
    onboarding_completed: bool
    workforce_count: int
    app_users_count: int
    branch_count: int
    warehouse_count: int
    operations: List[str]
    enabled_modules: List[str]
    accessibility_settings: Dict[str, Any]
    is_active: bool

    class Config:
        from_attributes = True


class UpdatePreferencesRequest(BaseModel):
    category: Optional[str] = Field(None, max_length=100)
    tier: Optional[str] = Field(None, pattern="^(simple|growth|enterprise)$")
    default_language: Optional[str] = Field(None, pattern="^(ta|tanglish|en)$")
    enabled_modules: Optional[List[str]] = None
    accessibility_settings: Optional[Dict[str, Any]] = None
