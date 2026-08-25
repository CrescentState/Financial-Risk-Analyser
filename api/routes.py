from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import re

from core.orchestrator import run_pipeline_async
from core.state import SystemState


router = APIRouter(prefix="/api/v1", tags=["analysis"])


class AnalysisResponse(BaseModel):
    ticker: str
    company_name: str
    confidence_score: float
    errors: list[str]
    financial_data: dict
    news_data: dict
    risk_data: dict
    synthesis_report: dict


class HealthCheckResponse(BaseModel):
    status: str
    service: str


TICKER_PATTERN = re.compile(r"^[A-Z0-9]{1,10}(?:\.[A-Z]{1,2})?$")


def validate_ticker(ticker: str) -> str:
    """Clean and validate ticker format - allows test tickers like ZZZINVALID."""
    clean = ticker.strip().upper()
    if not clean:
        raise HTTPException(status_code=400, detail="Ticker is required")
    if not TICKER_PATTERN.match(clean):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid ticker format: '{ticker}'. Expected format: AAPL, BRK.B, etc."
        )
    return clean


@router.post("/analyze/{ticker}", response_model=AnalysisResponse)
async def analyze_ticker(ticker: str):
    """
    Run the full financial risk analysis pipeline for a given ticker.
    
    Executes 4 agents in sequence:
    1. Financial Data Agent - fetches fundamentals from Alpha Vantage
    2. News & Sentiment Agent - fetches news from Google News RSS + Gemini sentiment
    3. Risk Analysis Agent - computes deterministic risk score + narrative
    4. Synthesis Agent - generates 6-section investment brief with recommendation
    """
    clean_ticker = validate_ticker(ticker)
    
    try:
        result = await run_pipeline_async(clean_ticker)
        
        return AnalysisResponse(
            ticker=result["ticker"],
            company_name=result["company_name"],
            confidence_score=result["confidence_score"],
            errors=result["errors"],
            financial_data=result["financial_data"],
            news_data=result["news_data"],
            risk_data=result["risk_data"],
            synthesis_report=result["synthesis_report"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint for container probes."""
    return {"status": "healthy", "service": "financial-risk-analyser"}


@router.get("/analyze/{ticker}", response_model=AnalysisResponse)
async def analyze_ticker_get(ticker: str):
    """GET endpoint for analysis (convenience for browser testing)."""
    return await analyze_ticker(ticker)