"""Health check and metrics endpoints."""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.lib.config import settings
from src.lib.database import get_db
from src.lib.logger import get_logger
from src.lib.queue import get_rabbitmq_channel

logger = get_logger(__name__)
router = APIRouter()


@router.get("", status_code=status.HTTP_200_OK)
@router.get("/", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.

    Returns service status and timestamp.
    """
    return {
        "status": "healthy",
        "service": "ragFlow API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Readiness probe for Kubernetes/Docker.

    Checks if service is ready to accept traffic by verifying:
    - Database connectivity
    - RabbitMQ connectivity
    """
    checks = {
        "database": False,
        "rabbitmq": False,
    }

    # Check database
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    # Check RabbitMQ
    try:
        channel = get_rabbitmq_channel()
        channel.close()
        checks["rabbitmq"] = True
    except Exception as e:
        logger.error(f"RabbitMQ health check failed: {e}")

    all_healthy = all(checks.values())

    return {
        "ready": all_healthy,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness probe for Kubernetes/Docker.

    Simple check to verify the process is alive.
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/metrics", status_code=status.HTTP_200_OK)
async def metrics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Prometheus-compatible metrics endpoint.

    Returns basic metrics about the service:
    - Database statistics
    - Service configuration
    """
    metrics_data = {
        "service": {
            "name": "ragflow",
            "version": "1.0.0",
            "environment": settings.environment,
        },
        "database": {},
        "configuration": {
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
            "max_chunks_per_query": settings.max_chunks_per_query,
            "confidence_threshold": settings.confidence_threshold,
        },
    }

    # Get database statistics
    try:
        # Count documents
        result = db.execute(text("SELECT COUNT(*) FROM documents"))
        metrics_data["database"]["total_documents"] = result.scalar()

        # Count chunks
        result = db.execute(text("SELECT COUNT(*) FROM chunks"))
        metrics_data["database"]["total_chunks"] = result.scalar()

        # Count queries
        result = db.execute(text("SELECT COUNT(*) FROM queries"))
        metrics_data["database"]["total_queries"] = result.scalar()

        # Count collections
        result = db.execute(text("SELECT COUNT(*) FROM collections"))
        metrics_data["database"]["total_collections"] = result.scalar()

    except Exception as e:
        logger.error(f"Failed to collect database metrics: {e}")
        metrics_data["database"]["error"] = str(e)

    return metrics_data
