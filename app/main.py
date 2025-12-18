"""
FastAPI application factory with production-grade middleware and configuration
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlmodel import SQLModel
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os
import logging

from app.api.v1 import health, items, convert, convert_advanced, convert_advanced_extended, metadata
from app.db.session import engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app startup and shutdown"""
    # Startup
    logger.info("=== Kits API Starting Up ===")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    SQLModel.metadata.create_all(engine)
    logger.info("Database initialized successfully")
    logger.info("=== Kits API Ready ===")
    
    yield
    
    # Shutdown
    logger.info("=== Kits API Shutting Down ===")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="Kits API",
        version="1.0.0",
        description="Production-grade file conversion API with 86+ endpoints",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )

    # Security middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*"]  # Configure for production
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        max_age=600,
    )
    
    # Compression middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Register routers
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(items.router, prefix="/api/v1", tags=["Items"])
    app.include_router(convert.router, prefix="/api/v1", tags=["Conversions"])
    app.include_router(convert_advanced.router, prefix="/api/v1", tags=["Advanced"])
    app.include_router(convert_advanced_extended.router, prefix="/api/v1", tags=["Extended"])
    app.include_router(metadata.router, prefix="/api/v1", tags=["API Info"])

    # Mount static files
    static_path = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_path):
        app.mount("/static", StaticFiles(directory=static_path), name="static")

    # Serve index.html at root route
    templates_path = os.path.join(os.path.dirname(__file__), "templates")
    index_path = os.path.join(templates_path, "index.html")
    
    @app.get("/")
    async def root():
        """Serve the interactive API testing dashboard"""
        if os.path.exists(index_path):
            return FileResponse(index_path, media_type="text/html")
        return {"message": "Kits API - Interactive Testing Dashboard at /"}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
