"""FastAPI application setup and configuration."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.lib.config import settings
from src.lib.database import get_db
from src.lib.logger import get_logger
from src.lib.queue import get_rabbitmq_channel

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting up ragFlow API server", extra={
        "environment": settings.environment,
        "api_port": settings.api_port,
    })

    # Test database connection
    try:
        db = next(get_db())
        logger.info("Database connection successful")
        db.close()
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

    # Test RabbitMQ connection
    try:
        channel = get_rabbitmq_channel()
        logger.info("RabbitMQ connection successful")
        channel.close()
    except Exception as e:
        logger.error(f"RabbitMQ connection failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down ragFlow API server")


# Create FastAPI application
app = FastAPI(
    title="ragFlow API",
    description="RAG-based Question Answering System for Olist Order Reviews",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(
        "Unhandled exception",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error": str(exc),
        },
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.debug else "An unexpected error occurred",
        },
    )


# Import and register routers
from src.api.routes import health, query, documents, collections

app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(query.router, prefix="/api/v1", tags=["Query"])
app.include_router(documents.router, prefix="/api/v1", tags=["Documents"])
app.include_router(collections.router, prefix="/api/v1", tags=["Collections"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "ragFlow API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.environment != "production" else "disabled",
    }
