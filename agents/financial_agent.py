import asyncio
import os
import sys
import yfinance as yf

from typing import Optional
from core.state import SystemState, FinancialData
from core.cache import get_cached_response, set_cached_response
from core.config import settings
from core.clients import async_http_client


def _is_test_mode() -> bool:
    """Check if test mode is enabled (checks at call time for test overrides)."""
    return getattr(sys.modules.get(__name__, {}), '_TEST_MODE_OVERRIDE', False)


def clean_float(val) -> Optional[float]:
    """Normalize 'None', 'N/A', '', None, 0.0 strings to float or None."""
    if val is None:
        return None
    if isinstance(val, str):
        v = val.strip()
        if v in ("", "None", "N/A", "null", "NaN"):
            return None
        try:
            return float(v)
        except ValueError:
            return None
    if isinstance(val, (int, float)):
        return float(val)
    return None


def normalize_debt_to_equity(raw_val: Optional[float]) -> Optional[float]:
    """Normalize D/E: yfinance often gives percentage (150) vs ratio (1.5)."""
    if raw_val is None:
        return None
    return raw_val / 100.0 if raw_val > 10 else raw_val


MOCK_DATA = {
    "AAPL": {
        "OVERVIEW": {
            "Name": "Apple Inc.",
            "RevenueTTM": "466822988000",
            "MarketCapitalization": "4514709504000",
            "PERatio": "35.48",
            "DebtToEquity": "1.57",
        },
        "INCOME_STATEMENT": {
            "annualReports": [
                {"netIncome": "112010000000", "totalRevenue": "466822988000"},
                {"netIncome": "99803000000", "totalRevenue": "394328000000"},
            ]
        },
        "BALANCE_SHEET": {
            "annualReports": [
                {
                    "cashAndCashEquivalentsAtCarryingValue": "35934000000",
                    "cash": "35934000000",
                    "shortTermDebt": "10000000000",
                    "longTermDebt": "100000000000",
                    "totalShareholderEquity": "70000000000",
                    "totalCurrentAssets": "150000000000",
                    "totalCurrentLiabilities": "120000000000",
                }
            ]
        },
    },
    "TSLA": {
        "OVERVIEW": {
            "Name": "Tesla Inc",
            "RevenueTTM": "103619002000",
            "MarketCapitalization": "1433132728000",
            "PERatio": "332.9",
            "DebtToEquity": "0.15",
        },
        "INCOME_STATEMENT": {
            "annualReports": [
                {"netIncome": "3794000000", "totalRevenue": "103619002000"},
                {"netIncome": "5519000000", "totalRevenue": "106606000000"},
            ]
        },
        "BALANCE_SHEET": {
            "annualReports": [
                {
                    "cashAndCashEquivalentsAtCarryingValue": "16513000000",
                    "cash": "16513000000",
                    "shortTermDebt": "1000000000",
                    "longTermDebt": "2000000000",
                    "totalShareholderEquity": "50000000000",
                    "totalCurrentAssets": "80000000000",
                    "totalCurrentLiabilities": "60000000000",
                }
            ]
        },
    },
    "ZZZINVALID": {
        "OVERVIEW": {"Information": "Invalid ticker"},
        "INCOME_STATEMENT": {"Information": "Invalid ticker"},
        "BALANCE_SHEET": {"Information": "Invalid ticker"},
    },
    "TWTR": {
        "OVERVIEW": {"Information": "Delisted ticker"},
        "INCOME_STATEMENT": {"Information": "Delisted ticker"},
        "BALANCE_SHEET": {"Information": "Delisted ticker"},
    },
    "RELIANCE.NS": {
        "OVERVIEW": {"Information": "Rate limit"},
        "INCOME_STATEMENT": {"Information": "Rate limit"},
        "BALANCE_SHEET": {"Information": "Rate limit"},
    },
    "MSFT": {
        "OVERVIEW": {
            "Name": "Microsoft Corporation",
            "RevenueTTM": "200000000000",
            "MarketCapitalization": "3000000000000",
            "PERatio": "30.0",
            "DebtToEquity": "0.5",
        },
        "INCOME_STATEMENT": {
            "annualReports": [
                {"netIncome": "70000000000", "totalRevenue": "200000000000"},
                {"netIncome": "60000000000", "totalRevenue": "180000000000"},
            ]
        },
        "BALANCE_SHEET": {
            "annualReports": [
                {
                    "cashAndCashEquivalentsAtCarryingValue": "50000000000",
                    "cash": "50000000000",
                    "shortTermDebt": "5000000000",
                    "longTermDebt": "50000000000",
                    "totalShareholderEquity": "100000000000",
                    "totalCurrentAssets": "180000000000",
                    "totalCurrentLiabilities": "90000000000",
                }
            ]
        },
    },
}


async def _fetch_alpha_vantage_async(function_name: str, ticker: str) -> tuple[dict, bool]:
    """Fetch data from Alpha Vantage asynchronously with validation and error reporting.
    
    Implements three-stage caching strategy:
    1. Retrieval (Get): Check local cache first - return cached data if valid and fresh
    2. Storage (Store): On successful API response, persist to cache with timestamp
    3. Expiration (Refresh): TTL-based eviction - stale data triggers fresh API call
    
    In test mode, returns mock data immediately without checking cache.
    """
    ticker_clean = ticker.strip().upper()

    # TEST MODE: Return mock data immediately, bypassing cache and network
    if _is_test_mode():
        mock_ticker = MOCK_DATA.get(ticker_clean, MOCK_DATA["ZZZINVALID"])
        mock_response = mock_ticker.get(function_name, {"Information": "Rate limit"})
        return mock_response, True

    # STAGE 1: RETRIEVAL (GET)
    # Check local cache for non-expired data before any network call
    cached_data = get_cached_response(ticker_clean, function_name)
    if cached_data and isinstance(cached_data, dict) and len(cached_data) > 0:
        return cached_data, False  # Cache hit - no network call made

    # STAGE 2: LIVE FETCH (on cache miss or stale data)
    api_key = settings.ALPHA_VANTAGE_API_KEY
    if not api_key:
        return {"error": "ALPHA_VANTAGE_KEY is unconfigured or empty."}, False

    url = "https://www.alphavantage.co/query"
    params = {"function": function_name, "symbol": ticker_clean, "apikey": api_key}

    try:
        # Use shared HTTP client with connection pooling and 5s timeout
        response = await async_http_client.get(url, params=params, timeout=5.0)
        response.raise_for_status()
        data = response.json()

        # Check for API-level errors (rate limits, invalid ticker, etc.)
        if any(k in data for k in ("Note", "Information", "Error Message")):
            return data, True  # Return error payload, don't cache

        # STAGE 3: STORAGE (STORE)
        # Only cache successful, valid responses
        if data and isinstance(data, dict) and len(data) > 0:
            set_cached_response(ticker_clean, function_name, data)

        return data, True

    except Exception as exc:
        return {"error": f"HTTP/Network error for {function_name}: {str(exc)}"}, False


def _fetch_alpha_vantage(function_name: str, ticker: str) -> tuple[dict, bool]:
    """Synchronous wrapper for backward compatibility with tests."""
    return asyncio.run(_fetch_alpha_vantage_async(function_name, ticker))


async def _fetch_yfinance(ticker: str) -> dict:
    """yfinance fallback with 3s timeout."""
    try:
        def _sync_yfinance():
            tk = yf.Ticker(ticker, session=None)
            return tk.info
        loop = asyncio.get_event_loop()
        info = await asyncio.wait_for(loop.run_in_executor(None, _sync_yfinance), timeout=3.0)
        return info or {}
    except Exception:
        return {}


async def financial_agent_async(state: dict) -> dict:
    """Async Financial Risk Agent node with full Alpha Vantage integration + yfinance fallback."""
    ticker = state.get("ticker", "").strip().upper()
    errors = list(state.get("errors", []))
    confidence = 1.0

    fd = {
        "data_available": False,
        "data_complete": False,  # backward compat for tests
        "debt_to_equity": None,
        "pe_ratio": None,
        "yoy_revenue_growth": None,
        "revenue_growth": None,  # backward compat for tests
        "current_ratio": None,
        "market_cap": None,
        "revenue": None,
        "net_income": None,  # backward compat for tests
        "cash_position": None,  # backward compat for tests
    }

    # 1. Try Alpha Vantage OVERVIEW
    overview_data, overview_was_live = await _fetch_alpha_vantage_async("OVERVIEW", ticker)

    # Check for rate limit / throttle - trigger yfinance fallback
    overview_failed = False
    if "error" in overview_data:
        errors.append(overview_data["error"])
        overview_failed = True
    elif "Note" in overview_data or "Information" in overview_data:
        errors.append("Alpha Vantage Throttle")
        confidence -= 0.2
        overview_failed = True
    elif not overview_data or "Error Message" in overview_data:
        errors.append(f"Invalid US Equity Ticker or empty profile for {ticker}.")
        overview_failed = True

    # Extract with clean_float and normalization (if overview succeeded)
    company_name = ticker
    if not overview_failed:
        raw_revenue = overview_data.get("RevenueTTM") or overview_data.get("totalRevenue")
        raw_market_cap = overview_data.get("MarketCapitalization") or overview_data.get("marketCap")
        raw_pe = overview_data.get("PERatio") or overview_data.get("trailingPE")
        raw_de = overview_data.get("DebtToEquity") or overview_data.get("debtToEquity")

        fd["market_cap"] = clean_float(raw_market_cap)
        fd["pe_ratio"] = clean_float(raw_pe)
        fd["debt_to_equity"] = normalize_debt_to_equity(clean_float(raw_de))

        # Revenue from overview (TTM)
        fd["revenue"] = clean_float(raw_revenue)

        # Company name
        company_name = overview_data.get("Name") or overview_data.get("longName") or ticker

    # yfinance fallback if overview failed (only in production mode)
    if overview_failed and not _is_test_mode():
        yf_data = await _fetch_yfinance(ticker)
        if yf_data:
            fd["market_cap"] = clean_float(yf_data.get("marketCap"))
            fd["pe_ratio"] = clean_float(yf_data.get("trailingPE"))
            fd["debt_to_equity"] = normalize_debt_to_equity(clean_float(yf_data.get("debtToEquity")))
            fd["revenue"] = clean_float(yf_data.get("totalRevenue"))
            fd["current_ratio"] = clean_float(yf_data.get("currentRatio"))
            fd["cash_position"] = clean_float(yf_data.get("totalCash"))
            company_name = yf_data.get("longName") or yf_data.get("shortName") or ticker

    # INCOME STATEMENT for yoy_revenue_growth (only if not using yfinance fallback)
    if not overview_failed:
        income_data, income_was_live = await _fetch_alpha_vantage_async("INCOME_STATEMENT", ticker)
        if "Note" not in income_data and "Information" not in income_data and "error" not in income_data:
            annual_reports = income_data.get("annualReports", [])
            if annual_reports:
                raw_ni = annual_reports[0].get("netIncome")
                if raw_ni and raw_ni != "None":
                    try:
                        fd["net_income"] = clean_float(raw_ni)
                    except ValueError:
                        pass

                if len(annual_reports) >= 2:
                    rev_curr = clean_float(annual_reports[0].get("totalRevenue"))
                    rev_prev = clean_float(annual_reports[1].get("totalRevenue"))
                    if rev_curr and rev_prev and rev_prev > 0:
                        fd["yoy_revenue_growth"] = (rev_curr - rev_prev) / rev_prev
                        fd["revenue_growth"] = fd["yoy_revenue_growth"]  # backward compat

    # BALANCE SHEET for current_ratio and cash_position (only if not using yfinance fallback)
    if not overview_failed:
        balance_data, balance_was_live = await _fetch_alpha_vantage_async("BALANCE_SHEET", ticker)
        if "Note" not in balance_data and "Information" not in balance_data and "error" not in balance_data:
            annual_bal = balance_data.get("annualReports", [])
            if annual_bal:
                latest = annual_bal[0]
                ca = clean_float(latest.get("totalCurrentAssets"))
                cl = clean_float(latest.get("totalCurrentLiabilities"))
                if ca and cl and cl > 0:
                    fd["current_ratio"] = ca / cl
                raw_cash = latest.get("cashAndCashEquivalentsAtCarryingValue") or latest.get("cash")
                fd["cash_position"] = clean_float(raw_cash)

    # COMPLETENESS ASSESSMENT - include current_ratio per contract
    required = [fd.get("revenue"), fd.get("market_cap"), fd.get("debt_to_equity"), fd.get("yoy_revenue_growth"), fd.get("current_ratio")]
    fd["data_available"] = all(v is not None for v in required)
    fd["data_complete"] = fd["data_available"]  # backward compat for tests

    # Confidence scoring
    if not fd["data_available"]:
        confidence -= 0.4  # flat 0.4 dock per spec for terminal degradation
    # Penalty for missing secondary fields
    if fd["debt_to_equity"] is None:
        confidence -= 0.05
    if fd["cash_position"] is None:
        confidence -= 0.05

    return {
        "ticker": ticker,
        "company_name": company_name,
        "financial_data": fd,
        "errors": errors,
        "confidence_score": max(0.0, round(confidence, 2)),
    }


def financial_agent(state: dict) -> dict:
    """Synchronous wrapper for LangGraph sync node compatibility.
    
    In test mode (_TEST_MODE_OVERRIDE=True), uses asyncio.run() directly
    since the mock data path is synchronous and doesn't need special handling.
    """
    # Check if we're in test mode (mock data path is synchronous)
    if getattr(sys.modules.get(__name__, {}), '_TEST_MODE_OVERRIDE', False):
        # In test mode, the mock data path is synchronous (no await points)
        # so asyncio.run() should work fine without event loop conflicts
        return asyncio.run(financial_agent_async(state))
    
    # Production mode: use thread pool to avoid event loop conflicts
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, financial_agent_async(state))
        return future.result()