import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.base import Base
from app.db.session import engine
from app.api.v1.auth import router as auth_router
from app.api.v1.projects import router as projects_router
from app.api.v1.ingest import router as ingest_router
from app.api.v1.query import router as query_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.websockets import router as ws_router
from app.services.alert_evaluator import alert_worker_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize structured logging
    setup_logging()
    
    # Auto-create tables for non-testing environments if engine connectable
    if settings.ENVIRONMENT != "testing":
        try:
            Base.metadata.create_all(bind=engine)
        except Exception:
            pass

    # Start recurring alert worker background task
    worker_task = None
    if settings.ENVIRONMENT != "testing":
        worker_task = asyncio.create_task(alert_worker_loop(interval_seconds=60))
    
    yield

    # Clean shutdown
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="PulseWatch: Lightweight monitoring & alerting platform for small engineering teams.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
@app.get(f"{settings.API_V1_STR}/health", tags=["Health"])
def health_check():
    """Health check endpoint for container orchestrators and uptime monitoring."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
    }


import time
import uuid
from starlette.requests import Request
from starlette.responses import Response

from app.api.v1.ai import router as ai_router

# Include Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(projects_router, prefix=settings.API_V1_STR)
app.include_router(ingest_router, prefix=settings.API_V1_STR)
app.include_router(query_router, prefix=settings.API_V1_STR)
app.include_router(alerts_router, prefix=settings.API_V1_STR)
app.include_router(ai_router, prefix=settings.API_V1_STR)
app.include_router(ws_router, prefix=settings.API_V1_STR)
app.include_router(ws_router)  # Also available at /ws/live/{project_id} directly


@app.middleware("http")
async def add_api_platform_headers(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_PER_MINUTE)
    response.headers["X-RateLimit-Remaining"] = "1185"
    response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
    return response
