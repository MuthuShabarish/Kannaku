import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import engine, Base
from app.routers import health, auth, onboarding
from app.schemas.common import ApiResponse, ApiErrorDetail

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("kanakku.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-initialize database tables on startup (especially for local development & testing)
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully.")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Adaptive, Multilingual, AI-Assisted Business Management Platform API",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        code = detail.get("code", "HTTP_ERROR")
        message = detail.get("message", str(detail))
        field = detail.get("field")
        details = detail.get("details") or detail
    else:
        code = f"HTTP_{exc.status_code}"
        message = str(detail)
        field = None
        details = None

    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse(
            success=False,
            error=ApiErrorDetail(code=code, message=message, field=field, details=details)
        ).model_dump()
    )


from fastapi.encoders import jsonable_encoder


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    loc = first_error.get("loc", [])
    field_name = ".".join(str(x) for x in loc[1:]) if len(loc) > 1 else str(loc[0]) if loc else None
    msg = first_error.get("msg", "Validation error")
    safe_errors = jsonable_encoder(errors)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ApiResponse(
            success=False,
            error=ApiErrorDetail(
                code="VALIDATION_ERROR",
                message=f"Invalid field '{field_name}': {msg}",
                field=field_name,
                details=safe_errors
            )
        ).model_dump()
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled server exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ApiResponse(
            success=False,
            error=ApiErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected server error occurred. Please try again later."
            )
        ).model_dump()
    )


# Mount Routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(onboarding.router)
