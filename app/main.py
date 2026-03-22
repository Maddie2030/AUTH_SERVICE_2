import uuid
import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from prometheus_client import make_asgi_app, Counter, Histogram, Gauge
import time

from app.core.config import settings
from app.exceptions import register_exception_handlers
from app.api.v1 import auth, session, user, admin, health
from app.core.redis import close_redis

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
)
logger = logging.getLogger(__name__)

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency", ["method", "endpoint"])
LOGIN_SUCCESS = Counter("auth_login_success_total", "Successful logins")
LOGIN_FAILED = Counter("auth_login_failed_total", "Failed logins")
ACTIVE_SESSIONS = Gauge("auth_active_sessions", "Active sessions")
ACTIVE_EXAM_SESSIONS = Gauge("auth_active_exam_sessions", "Active exam sessions")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting MockTest Auth Service v%s", settings.VERSION)
    yield
    logger.info("Shutting down MockTest Auth Service")
    await close_redis()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Authentication and session management service for MockTest platform",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    endpoint = request.url.path
    REQUEST_COUNT.labels(method=request.method, endpoint=endpoint, status=response.status_code).inc()
    REQUEST_LATENCY.labels(method=request.method, endpoint=endpoint).observe(duration)
    return response


register_exception_handlers(app)

app.include_router(health.router)
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(session.router, prefix=settings.API_V1_STR)
app.include_router(user.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/", tags=["Root"])
async def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health/live",
    }
