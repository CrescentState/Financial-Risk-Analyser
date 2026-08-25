from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router

app = FastAPI(
    title="Financial Risk Analyser",
    description="Multi-agent AI pipeline for autonomous financial due-diligence",
    version="0.1.0",
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Health check also at root level for container probes
@app.get("/health")
async def health_root():
    return {"status": "healthy", "service": "financial-risk-analyser"}


@app.get("/")
async def root():
    return {
        "service": "Financial Risk Analyser",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }