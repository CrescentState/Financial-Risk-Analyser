from typing import Annotated, Dict, List, Optional, TypedDict


def _errors_reducer(left: List[str], right: List[str]) -> List[str]:
    """Reducer that accumulates errors from all agents."""
    return left + right


def _timings_reducer(left: Dict[str, float], right: Dict[str, float]) -> Dict[str, float]:
    """Reducer that merges per-agent wall-clock timings (later keys win)."""
    return {**left, **right}


class FinancialData(TypedDict, total=False):
    data_available: bool
    data_complete: bool
    debt_to_equity: Optional[float]
    pe_ratio: Optional[float]
    yoy_revenue_growth: Optional[float]
    current_ratio: Optional[float]
    market_cap: Optional[int]
    revenue: Optional[float]
    net_income: Optional[float]
    cash_position: Optional[float]
    revenue_growth: Optional[float]


class NewsArticle(TypedDict):
    title: str
    url: str
    source: str


class NewsData(TypedDict):
    news_available: bool
    sentiment_score: float
    key_events: List[str]
    red_flags: List[str]
    summary: str
    articles: List[NewsArticle]


class RiskDetail(TypedDict):
    id: str
    label: str
    explanation: str


class RiskData(TypedDict):
    risk_score: float
    risk_factors: List[str]
    risk_narrative: str
    risk_details: List[RiskDetail]


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
    errors: Annotated[List[str], _errors_reducer]
    timings: Annotated[Dict[str, float], _timings_reducer]


def init_state(ticker: str) -> SystemState:
    """Factory function called by the orchestrator at pipeline entry.
    Guarantees a fully formed, predictable default state structure.
    """
    return {
        "ticker": ticker.strip().upper(),
        "company_name": "",
        "financial_data": {
            "data_available": False,
            "data_complete": False,
            "debt_to_equity": None,
            "pe_ratio": None,
            "yoy_revenue_growth": None,
            "revenue_growth": None,
            "current_ratio": None,
            "market_cap": None,
            "revenue": None,
            "net_income": None,
            "cash_position": None,
        },
        "news_data": {
            "news_available": False,
            "sentiment_score": 0.0,
            "key_events": [],
            "red_flags": [],
            "summary": "",
            "articles": [],
        },
        "risk_data": {
            "risk_score": 0.0,
            "risk_factors": [],
            "risk_narrative": "",
            "risk_details": [],
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
        "timings": {},
    }


# Backward compatibility alias
State = SystemState
FinancialData = FinancialData
NewsData = NewsData
NewsArticle = NewsArticle
RiskData = RiskData
RiskDetail = RiskDetail
SynthesisBrief = SynthesisBrief