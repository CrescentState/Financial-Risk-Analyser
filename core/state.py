from typing import Annotated, List, Optional, TypedDict
import operator


class FinancialData(TypedDict):
    data_available: bool
    debt_to_equity: Optional[float]
    pe_ratio: Optional[float]
    yoy_revenue_growth: Optional[float]
    current_ratio: Optional[float]
    market_cap: Optional[int]


class NewsData(TypedDict):
    news_available: bool
    sentiment_score: float
    key_events: List[str]
    red_flags: List[str]
    summary: str


class RiskData(TypedDict):
    risk_score: float
    risk_factors: List[str]
    risk_narrative: str


class SynthesisBrief(TypedDict):
    company_snapshot: str
    financial_health: str
    market_sentiment: str
    risk_assessment: str
    key_concerns: List[str]
    analyst_recommendation: str


class SystemState(TypedDict):
    ticker: str
    company_name: str
    financial_data: FinancialData
    news_data: NewsData
    risk_data: RiskData
    synthesis_report: SynthesisBrief
    confidence_score: float
    errors: Annotated[List[str], operator.add]


def init_state(ticker: str) -> SystemState:
    """Factory function called by the orchestrator at pipeline entry.
    Guarantees a fully formed, predictable default state structure.
    """
    return {
        "ticker": ticker.strip().upper(),
        "company_name": "",
        "financial_data": {
            "data_available": False,
            "debt_to_equity": None,
            "pe_ratio": None,
            "yoy_revenue_growth": None,
            "current_ratio": None,
            "market_cap": None,
        },
        "news_data": {
            "news_available": False,
            "sentiment_score": 0.0,
            "key_events": [],
            "red_flags": [],
            "summary": "",
        },
        "risk_data": {
            "risk_score": 0.0,
            "risk_factors": [],
            "risk_narrative": "",
        },
        "synthesis_report": {
            "company_snapshot": "",
            "financial_health": "",
            "market_sentiment": "",
            "risk_assessment": "",
            "key_concerns": [],
            "analyst_recommendation": "Neutral",
        },
        "confidence_score": 1.0,
        "errors": [],
    }


# Backward compatibility alias
State = SystemState
FinancialData = FinancialData
NewsData = NewsData
RiskData = RiskData
SynthesisBrief = SynthesisBrief