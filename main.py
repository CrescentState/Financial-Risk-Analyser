import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
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

    # Health check endpoints (MUST be before catch-all)
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

    # Serve React static files (built from frontend/)
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir):
        # Mount /assets for Vite's default output
        app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")
        # Mount /static for any other static files
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        
        # SPA catch-all: serve index.html for non-API routes
        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            # Don't interfere with API routes, health endpoints, or static assets
            if full_path.startswith("api/") or full_path.startswith("health") or full_path.startswith("assets/") or full_path.startswith("static/"):
                return JSONResponse(status_code=404, content={"detail": "Not found"})
            
            index_path = os.path.join(static_dir, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            return JSONResponse(
                status_code=404, 
                content={"detail": "Frontend not built. Run 'npm run build' in frontend/"}
            )

    @app.get("/", tags=["Root"])
    async def root():
        # Serve frontend if available, otherwise return API info
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
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