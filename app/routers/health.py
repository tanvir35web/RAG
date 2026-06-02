from datetime import datetime, timezone

from fastapi import APIRouter

from app.models.responses import HealthResponse

router = APIRouter(tags=["Health"])

_VERSION = "1.0.0"


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=_VERSION,
        timestamp=datetime.now(timezone.utc),
        services={"api": "ok"},
    )
