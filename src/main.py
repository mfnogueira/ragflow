"""Entry point for running the FastAPI application."""

import uvicorn

from src.lib.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "src.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "development",
        log_level="info",
    )
