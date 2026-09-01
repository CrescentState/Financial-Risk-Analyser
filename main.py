import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.routes import router
from core.config import settings


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting Financial Risk Analyser...")
    yield
    logger.info("Shutting down Financial Risk Analyser...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    # Determine allowed origins from environment
    cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
    
    app = FastAPI(
        title="Financial Risk Analyser",
        description="Multi-agent AI pipeline for autonomous financial due-diligence",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if os.getenv("ENABLE_DOCS", "true").lower() == "true" else None,
        redoc_url="/redoc" if os.getenv("ENABLE_DOCS", "true").lower() == "true" else None,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        logger.info(f"{request.method} {request.url.path}")
        response = await call_next(request)
        return response

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled error: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    app.include_router(router)

    # Health check endpoints
    @app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status": "healthy",
            "service": "financial-risk-analyser",
            "version": "0.1.0",
        }

    @app.get("/health/live", tags=["Health"])
    async def liveness():
        return {"status": "alive"}

    @app.get("/health/ready", tags=["Health"])
    async def readiness():
        return {"status": "ready"}

    @app.get("/", tags=["Root"])
    async def root():
        return {
            "service": "Financial Risk Analyser",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("RELOAD", "false").lower() == "true",
    )