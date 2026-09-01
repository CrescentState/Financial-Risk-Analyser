import asyncio
import json
import sys
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from core.state import SystemState
from core.config import settings
from core.clients import gemini_client


class RiskAgentResponse(BaseModel):
    risk_narrative: str = Field(..., description="2-3 sentence narrative explaining the risk triggers.")


def _run_deterministic_rules(financial_data: dict, news_data: dict) -> list[str]:
    """Stage 1: Execute rule-based threshold checks on raw financial metrics.
    Returns list of triggered risk factors (strings)."""
    factors = []

    de_ratio = financial_data.get("debt_to_equity")
    if de_ratio is not None:
        if de_ratio > 2.5:
            factors.append("High Leverage (D/E > 2.5)")
        elif de_ratio < 0.0:
            factors.append("Negative Shareholder Equity (Balance Sheet Distress)")

    rev_growth = financial_data.get("yoy_revenue_growth")
    if rev_growth is not None and rev_growth < -0.10:
        factors.append(f"Revenue Contraction ({rev_growth:.2%})")

    pe_ratio = financial_data.get("pe_ratio")
    if pe_ratio is not None and pe_ratio <= 0.0:
        factors.append("Unprofitable / Negative P/E")

    # Sentiment risk: safe access with default 0.0
    sentiment = news_data.get("sentiment_score", 0.0) or 0.0
    if sentiment < -0.4:
        factors.append("Hostile Media Coverage")

    return factors


def _calculate_risk_score(factors: list[str]) -> float:
    """Calculate risk score from factors."""
    score = 0.0
    for factor in factors:
        if "High Leverage" in factor:
            score += 25.0
        elif "Negative Shareholder Equity" in factor:
            score += 35.0
        elif "Revenue Contraction" in factor:
            score += 30.0
        elif "Unprofitable" in factor:
            score += 20.0
        elif "Hostile Media" in factor:
            score += 15.0
    return min(100.0, score)


async def risk_agent_async(state: dict) -> dict:
    """Agent 3: Hybrid Risk Agent combining rule engine with LLM synthesis."""
    new_errors = list(state.get("errors", []))  # Accumulate: read input errors + add new

    financial_data = state.get("financial_data", {})
    news_data = state.get("news_data", {})
    ticker = state.get("ticker", "UNKNOWN")

    # Stage 1: Deterministic Rule Check (Python-calculated)
    risk_factors = _run_deterministic_rules(
        state.get("financial_data", {}),
        state.get("news_data", {})
    )
    risk_score = _calculate_risk_score(risk_factors)

    # Stage 2: LLM Narrative Synthesis (LLM only writes narrative)
    prompt = f"""
You are a senior financial risk management analyst. Analyze the following financial metrics for {ticker}.

Deterministic Risk Flags Triggered (Python-calculated, DO NOT RECOMPUTE):
{risk_factors if risk_factors else "None"}

Financial Payload:
{json.dumps(state.get("financial_data", {}), indent=2)}

News Sentiment Score: {state.get("news_data", {}).get("sentiment_score", 0.0)}

The Python engine calculated risk_score = {risk_score:.1f} based on the flags above.
Write a 2-3 sentence risk_narrative explaining these specific triggers.
Do NOT output scores or new factors.
"""

    gen_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=RiskAgentResponse,
        temperature=0.1,
    )

    risk_narrative = ""
    try:
        response = await asyncio.to_thread(
            gemini_client.models.generate_content,
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=gen_config,
        )
        # Handle both Pydantic-parsed response and raw text response
        if hasattr(response, "parsed") and response.parsed is not None:
            parsed_obj = response.parsed
            parsed_cls = type(parsed_obj)
            if hasattr(parsed_cls, "__pydantic_fields__") or hasattr(parsed_cls, "model_fields"):
                parsed = parsed_obj
            else:
                parsed = json.loads(response.text)
        else:
            parsed = json.loads(response.text)
        
        # Handle both Pydantic model and dict
        if isinstance(parsed, dict):
            risk_narrative = parsed.get("risk_narrative", "")
        else:
            risk_narrative = parsed.risk_narrative
    except Exception as e:
        new_errors.append(f"Risk Agent execution failed: {str(e)}")
        risk_narrative = ""

    # Build risk_data with Python-calculated score and LLM narrative
    risk_factors = _run_deterministic_rules(
        state.get("financial_data", {}),
        state.get("news_data", {})
    )
    risk_score = _calculate_risk_score(risk_factors)

    risk_data = {
        "risk_score": round(risk_score, 1),
        "risk_factors": risk_factors,
        "risk_narrative": risk_narrative,
    }

    # Fallback: only if LLM failed (error occurred), use fallback score of 50
    if not risk_narrative and new_errors:
        risk_data = {
            "risk_score": 50.0,
            "risk_factors": risk_factors,
            "risk_narrative": "Narrative unavailable due to system error.",
        }

    return {
        **state,
        "risk_data": risk_data,
        "errors": new_errors,
    }


def risk_agent_sync(state: dict) -> dict:
    """Synchronous wrapper for LangGraph sync node compatibility."""
    test_mode = getattr(sys.modules.get('agents.risk_agent', {}), '_TEST_MODE_OVERRIDE', False)
    
    if test_mode:
        return asyncio.run(risk_agent_async(state))
    
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, risk_agent_async(state))
        return future.result()