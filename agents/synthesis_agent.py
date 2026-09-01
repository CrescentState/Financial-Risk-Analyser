import json
import asyncio
from typing import Literal
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from core.state import State, SynthesisBrief
from core.config import settings

_genai_client = genai.Client(api_key=settings.GEMINI_API_KEY)

class SynthesisBriefResponse(BaseModel):
    company_snapshot: str = Field(
        ...,
        description="2-3 sentence overview of the company, its business, and market position."
    )
    financial_health: str = Field(
        ...,
        description="Analysis of financial metrics: revenue, profitability, leverage, liquidity."
    )
    market_sentiment: str = Field(
        ...,
        description="Summary of news sentiment, key events, and red flags from media coverage."
    )
    risk_assessment: str = Field(
        ...,
        description="Synthesis of risk factors, risk score, and risk narrative."
    )
    key_concerns: list[str] = Field(
        ...,
        description="List of specific concerns identified across all agents."
    )


def _compute_recommendation(state: dict) -> str:
    """Compute investment recommendation deterministically in Python per contract."""
    confidence_score = state.get("confidence_score", 1.0)
    risk_data = state.get("risk_data", {})
    financial_data = state.get("financial_data", {})
    
    risk_score = risk_data.get("risk_score", 0.0)
    yoy_revenue_growth = financial_data.get("yoy_revenue_growth")
    
    if confidence_score < 0.5 or risk_score > 70.0:
        return "Flag for Review"
    elif risk_score <= 20.0 and yoy_revenue_growth is not None and yoy_revenue_growth > 0.05:
        return "Strong Buy Signal"
    elif risk_score <= 45.0:
        return "Cautious Positive"
    else:
        return "Neutral"


async def synthesis_agent_async(state: dict) -> dict:
    """Agent 4: Synthesis Agent.
    
    Consolidates financial metrics, market sentiment, and risk evaluation into a unified,
    actionable investment brief per the 6-section SynthesisBrief contract.
    """
    new_errors = list(state.get("errors", []))  # Accumulate: read input errors + add new
    ticker = state.get("ticker", "UNKNOWN").strip().upper()
    company_name = state.get("company_name", ticker)
    confidence_score = float(state.get("confidence_score", 1.0))

    financial_data = state.get("financial_data", {})
    news_data = state.get("news_data", {})
    risk_data = state.get("risk_data", {})

    # 1. Compute deterministic recommendation in Python (contract requirement)
    recommendation = _compute_recommendation(state)

    # 2. Build context for LLM synthesis (6 sections only, no recommendation)
    prompt = f"""
You are the Chief Investment Officer synthesizing a due-diligence report for {company_name} ({ticker}).

Context & Prior Agent Data:
---------------------------
Financial Fundamentals:
{json.dumps(financial_data, indent=2)}

News & Market Sentiment:
{json.dumps(news_data, indent=2)}

Risk Analysis Engine Output:
{json.dumps(risk_data, indent=2)}

Audit Trail / Identified Pipeline Errors:
{json.dumps(state.get("errors", []), indent=2)}

Calculated Confidence Score: {confidence_score:.2f} / 1.00
Deterministic Recommendation (DO NOT CHANGE): {recommendation}

Instructions:
Synthesize all prior outputs into a structured investment brief with EXACTLY these 6 fields:
1. "company_snapshot" (string): 2-3 sentence overview of the company, its business, and market position.
2. "financial_health" (string): Analysis of financial metrics: revenue, profitability, leverage, liquidity.
3. "market_sentiment" (string): Summary of news sentiment, key events, and red flags from media coverage.
4. "risk_assessment" (string): Synthesis of risk factors, risk score, and risk narrative.
5. "key_concerns" (list of strings): List of specific concerns identified across all agents.
6. "analyst_recommendation" (string): Will be programmatically overwritten with "{recommendation}".

Return ONLY a JSON object with these 6 fields. Do not include any other fields.
"""

    gen_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=SynthesisBriefResponse,
        temperature=0.1,
    )

    client = _genai_client

    # Fallback brief structure matching SynthesisBrief contract
    synthesis_brief: SynthesisBrief = {
        "company_snapshot": "Synthesis failed due to system exception.",
        "financial_health": "Unable to assess financial health.",
        "market_sentiment": "Unable to assess market sentiment.",
        "risk_assessment": "Unable to assess risk.",
        "key_concerns": ["LLM synthesis pipeline error encountered."],
        "analyst_recommendation": recommendation,
    }

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=gen_config,
        )

        # Extract parsed response
        parsed = None
        if hasattr(response, "parsed") and response.parsed is not None:
            parsed_cls = type(response.parsed)
            if hasattr(parsed_cls, "__pydantic_fields__") or hasattr(parsed_cls, "model_fields"):
                parsed = response.parsed

        if parsed is None:
            parsed = json.loads(response.text)

        if isinstance(parsed, dict):
            synthesis_brief = {
                "company_snapshot": parsed.get("company_snapshot", ""),
                "financial_health": parsed.get("financial_health", ""),
                "market_sentiment": parsed.get("market_sentiment", ""),
                "risk_assessment": parsed.get("risk_assessment", ""),
                "key_concerns": parsed.get("key_concerns", []),
                "analyst_recommendation": recommendation,  # PROGRAMMATIC OVERRIDE per contract
            }
        else:
            synthesis_brief = {
                "company_snapshot": parsed.company_snapshot,
                "financial_health": parsed.financial_health,
                "market_sentiment": parsed.market_sentiment,
                "risk_assessment": parsed.risk_assessment,
                "key_concerns": parsed.key_concerns,
                "analyst_recommendation": recommendation,  # PROGRAMMATIC OVERRIDE per contract
            }

    except Exception as e:
        new_errors.append(f"Synthesis Agent execution failed: {str(e)}")
        synthesis_brief["key_concerns"].append(f"System Exception: {str(e)}")

    # Return state with synthesis_report key (per contract) and updated confidence/errors
    return {
        **state,
        "synthesis_report": synthesis_brief,
        "confidence_score": confidence_score,
        "errors": new_errors,
    }


def synthesis_agent_sync(state: dict) -> dict:
    """Synchronous wrapper for LangGraph sync node compatibility."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        future = asyncio.run_coroutine_threadsafe(synthesis_agent_async(state), loop)
        return future.result()
    else:
        return asyncio.run(synthesis_agent_async(state))