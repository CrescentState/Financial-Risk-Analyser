from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import re

from core.orchestrator import run_pipeline_async
from core.resolver import search_companies
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


class SearchCandidate(BaseModel):
    symbol: str
    name: str
    type: str = ""
    region: str = ""
    freeTierSupported: bool = True


TICKER_PATTERN = re.compile(r"^[A-Z0-9]{1,10}(?:\.[A-Z]{1,2})?$")

# Company-name search: letters/digits plus common name punctuation
# (length bounds enforced in validate_query, not in the pattern)
QUERY_PATTERN = re.compile(r"^[A-Za-z0-9 .&'\-,()]+$")


def validate_query(query: str) -> str:
    """Clean and validate a company-name search query."""
    clean = query.strip()
    if len(clean) < 2:
        raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")
    if len(clean) > 50:
        raise HTTPException(status_code=400, detail="Search query must be at most 50 characters")
    if not QUERY_PATTERN.match(clean):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid search query: '{query}'. Use letters, numbers, spaces and . & ' - , ( )",
        )
    return clean


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


@router.get("/search/{query}", response_model=list[SearchCandidate])
async def search_symbols(query: str):
    """
    Resolve a company name or keyword to ranked ticker candidates.

    Powers the frontend autocomplete dropdown. Returns [] when nothing matches.
    """
    clean_query = validate_query(query)

    try:
        candidates = await search_companies(clean_query)
        return [SearchCandidate(**c) for c in candidates]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Symbol search failed: {str(e)}")


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