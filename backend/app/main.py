"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db
from .logging_config import configure_logging, get_logger
from .routers import ingestion, features, recommendations, dashboard

configure_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting %s v%s", settings.app_name, settings.app_version)
    init_db()
    log.info("Database initialized at %s", settings.database_url)
    yield
    log.info("Shutting down.")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Non-diagnostic treatment-support API for Type 2 Diabetes. "
        "Ingests CGM exports, computes daily features, and produces "
        "rule-based recommendations."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingestion.router)
app.include_router(features.router)
app.include_router(recommendations.router)
app.include_router(dashboard.router)


@app.get("/", tags=["root"])
def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "disclaimer": (
            "This system is NON-DIAGNOSTIC. It does not diagnose, prescribe, or "
            "replace professional medical care. Always consult your care team."
        ),
    }


@app.get("/health", tags=["root"])
def health():
    return {"status": "ok"}
