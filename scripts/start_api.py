"""Inicia a API sem auto-reload para evitar problemas."""
import uvicorn
from src.lib.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "src.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,  # SEM auto-reload
        log_level="info",
    )
