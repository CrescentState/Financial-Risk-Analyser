from typing import Annotated, List, Optional, TypedDict


class FinancialData(TypedDict):
    revenue: Optional[float]
    net_income: Optional[float]
    debt_to_equity: Optional[float]
    pe_ratio: Optional[float]
    cash_position: Optional[float]
    market_cap: Optional[float]
    revenue_growth: Optional[float]
    data_complete: bool


class NewsData(TypedDict):
    sentiment_score: Optional[float]
    key_events: List[str]
    red_flags: List[str]
    news_available: bool
    summary: Optional[str]


class RiskData(TypedDict):
    pass


class FinalBrief(TypedDict):
    pass


def append_error(current_errors: List[str], new_errors: List[str]) -> List[str]:
    return current_errors + new_errors


class State(TypedDict):
    ticker: str
    company_name: str
    confidence_score: float
    errors: Annotated[List[str], append_error]
    financial_data: FinancialData
    news_data: NewsData
    risk_data: RiskData
    final_brief: FinalBrief


def init_state(ticker: str) -> State:
    """
    Factory function called by the orchestrator at pipeline entry.
    Guarantees a fully formed, predictable default state structure.
    """
    return {
        "ticker": ticker.strip().upper(),
        "company_name": "",
        "confidence_score": 1.0,
        "errors": [],
        "financial_data": {
            "revenue": None,
            "net_income": None,
            "debt_to_equity": None,
            "pe_ratio": None,
            "cash_position": None,
            "market_cap": None,
            "revenue_growth": None,
            "data_complete": True,
        },
        "news_data": {
            "sentiment_score": None,
            "key_events": [],
            "red_flags": [],
            "news_available": True,
            "summary": None,
        },
        "risk_data": {},
        "final_brief": {},
    }
