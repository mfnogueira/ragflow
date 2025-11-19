"""Inicia a API na porta 8001 sem auto-reload."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=8001,  # Porta 8001 para evitar conflitos
        reload=False,
        log_level="info",
    )
