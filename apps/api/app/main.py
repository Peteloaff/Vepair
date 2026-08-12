import logging
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import get_settings
from app.database import SessionLocal
from app.logging_config import configure_logging
from app.routers import auth as auth_router
from app.routers import baseline as baseline_router
from app.routers import checkins as checkins_router
from app.routers import exercises as exercises_router
from app.routers import profile as profile_router
from app.routers import recordings as recordings_router
from app.routers import recovery_score as recovery_score_router
from app.routers import share_progress as share_progress_router
from app.routers import training_consistency as training_consistency_router
from app.routers import vocal_plan as vocal_plan_router
from app.routers import vocal_range as vocal_range_router
from app.schemas import ErrorDetail, ErrorResponse, HealthResponse

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("vepair.api")

app = FastAPI(title="VepAIr API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "code" in exc.detail and "message" in exc.detail:
        error = exc.detail
    else:
        error = {"code": "http_error", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content={"error": error})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error=ErrorDetail(code="validation_error", message=str(exc.errors()))
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "Unhandled exception on %s %s", request.method, request.url.path,
        exc_info=exc,
        extra={"request_id": request_id},
    )
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=ErrorDetail(code="internal_error", message="An unexpected error occurred.")
        ).model_dump(),
    )


app.include_router(auth_router.router)
app.include_router(profile_router.router)
app.include_router(checkins_router.router)
app.include_router(recordings_router.router)
app.include_router(baseline_router.router)
app.include_router(recovery_score_router.router)
app.include_router(exercises_router.router)
app.include_router(vocal_range_router.router)
app.include_router(vocal_plan_router.router)
app.include_router(share_progress_router.router)
app.include_router(training_consistency_router.router)


@app.get("/api/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    db_status = "unknown"
    session = SessionLocal()
    try:
        session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:  # noqa: BLE001 — health check must never raise
        logger.exception("Database health check failed")
        db_status = "unreachable"
    finally:
        session.close()

    return HealthResponse(status="ok", database=db_status, app_env=settings.app_env)
