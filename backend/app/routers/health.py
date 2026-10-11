from fastapi import APIRouter
from app.config import settings
from app.database import check_db_health
from app.schemas.common import ApiResponse

router = APIRouter(tags=["Health"])


@router.get("/health")
@router.get("/api/v1/health")
def get_health() -> ApiResponse[dict]:
    """
    Application health check endpoint returning API status, environment,
    database connectivity details, and currency defaults.
    """
    db_health = check_db_health()
    is_healthy = db_health.get("status") == "healthy"

    return ApiResponse(
        success=is_healthy,
        data={
            "app_name": settings.APP_NAME,
            "environment": settings.ENVIRONMENT,
            "status": "online" if is_healthy else "degraded",
            "database": db_health,
            "default_currency": settings.DEFAULT_CURRENCY,
            "default_currency_symbol": settings.DEFAULT_CURRENCY_SYMBOL
        }
    )
