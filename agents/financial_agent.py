import os
import time
import requests
from core.state import State, FinancialData
from core.cache import get_cached_response, set_cached_response
from dotenv import load_dotenv

load_dotenv()


def _fetch_alpha_vantage(function_name: str, ticker: str) -> tuple[dict, bool]:
    """
    Fetches Alpha Vantage payload data using a defensive cache-first lookup.
    Returns a tuple: (data_dictionary, was_fetched_from_live_network)
    """
    ticker_clean = ticker.strip().upper()

    # 1. Attempt local cache extraction
    cached_data = get_cached_response(ticker_clean, function_name)
    if cached_data is not None:
        return cached_data, False  # Data found in cache, NO live network call made

    # 2. Live API Network Call on Cache Miss
    api_key = os.getenv("ALPHA_VANTAGE_KEY")
    if not api_key:
        return {}, False

    url = "https://www.alphavantage.co/query"
    params = {"function": function_name, "symbol": ticker_clean, "apikey": api_key}

    try:
        # Use a clean, isolated request that drops its connection immediately after completion
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()

            # Catch Alpha Vantage tier exhaustion signals before caching
            if "Note" in data or "Information" in data or "Error Message" in data:
                return data, True

            # Populate cache for future test runs
            set_cached_response(ticker_clean, function_name, data)
            return data, True  # Live network call was successful
    except Exception:
        pass
    return {}, False

def financial_agent(state: State) -> State:
    """
    Agent 1: Revised US Equities Financial Extraction Engine.
    Uses Alpha Vantage exclusively backed by a local caching layer.
    Sequentially extracts OVERVIEW, INCOME_STATEMENT, and BALANCE_SHEET.
    """
    ticker = state.get("ticker", "").strip().upper()

    if "errors" not in state:
        state["errors"] = []

    fd: FinancialData = {
        "revenue": None,
        "net_income": None,
        "debt_to_equity": None,
        "pe_ratio": None,
        "cash_position": None,
        "market_cap": None,
        "revenue_growth": None,
        "data_complete": True
    }

    # =====================================================================
    # STAGE 1 & 2: OVERVIEW EXTRACTION & ERROR VALIDATION
    # =====================================================================
    overview_data, overview_was_live = _fetch_alpha_vantage("OVERVIEW", ticker)

    if "Note" in overview_data or "Information" in overview_data:
        state["errors"].append(f"Alpha Vantage API Rate Limit Exceeded for {ticker} (OVERVIEW).")
        fd["data_complete"] = False
        state["confidence_score"] = 0.0
        state["financial_data"] = fd
        return state

    if not overview_data or "Error Message" in overview_data:
        state["errors"].append(f"Invalid US Equity Ticker or empty payload profile for {ticker}.")
        fd["data_complete"] = False
        state["confidence_score"] = 0.0
        state["financial_data"] = fd
        return state

    # Extract corporate metadata name for Downstream Agents
    state["company_name"] = overview_data.get("Name", ticker)

    # =====================================================================
    # STAGE 3: OVERVIEW DATA FIELD MAPPING (Restricted to actual Overview fields)
    # =====================================================================
    av_mapping = {
        "revenue": "RevenueTTM",
        "market_cap": "MarketCapitalization",
        "pe_ratio": "PERatio"
    }

    for target_key, av_key in av_mapping.items():
        val = overview_data.get(av_key)
        if val is not None and val != "None":
            try:
                fd[target_key] = float(val)
            except ValueError:
                state["errors"].append(f"Parsing conversion error for field '{target_key}' on ticker {ticker}.")
        else:
            state["errors"].append(f"Field '{target_key}' unavailable in Alpha Vantage OVERVIEW payload.")

    if overview_was_live:
        print("⏳ Budgeting API credits: Cooling down network socket for 15 seconds (Post-Overview)...")
        time.sleep(15)

    # =====================================================================
    # STAGE 4: INCOME STATEMENT EXTRACTION (Net Income & Revenue Growth)
    # =====================================================================
    income_data, income_was_live = _fetch_alpha_vantage("INCOME_STATEMENT", ticker)

    if "Note" in income_data or "Information" in income_data:
         state["errors"].append(f"Alpha Vantage API Rate Limit Exceeded for {ticker} (INCOME_STATEMENT).")
    else:
        annual_reports_income = income_data.get("annualReports", [])

        if len(annual_reports_income) >= 1:
            # 4a. Extract Net Income
            raw_ni = annual_reports_income[0].get("netIncome")
            if raw_ni and raw_ni != "None":
                try:
                    fd["net_income"] = float(raw_ni)
                except ValueError:
                    state["errors"].append(f"Parsing error for 'net_income' on {ticker}.")
            else:
                state["errors"].append("Field 'net_income' unavailable in INCOME_STATEMENT payload.")

            # 4b. YoY Revenue Growth
            if len(annual_reports_income) >= 2:
                try:
                    current_rev_str = annual_reports_income[0].get("totalRevenue")
                    prior_rev_str = annual_reports_income[1].get("totalRevenue")

                    if current_rev_str and prior_rev_str and current_rev_str != "None" and prior_rev_str != "None":
                        current_annual_rev = float(current_rev_str)
                        prior_annual_rev = float(prior_rev_str)

                        if prior_annual_rev > 0:
                            fd["revenue_growth"] = (current_annual_rev - prior_annual_rev) / prior_annual_rev
                        else:
                            state["errors"].append("Annual revenue growth calculation blocked: Prior year revenue is zero.")
                    else:
                        state["errors"].append("Annual revenue fields contain invalid string data tags.")
                except (ValueError, TypeError):
                    state["errors"].append("Failed to convert annual revenue text tokens to numeric floats.")
            else:
                state["errors"].append("Insufficient annual report intervals available to compute revenue growth.")

    if income_was_live:
        print("⏳ Budgeting API credits: Cooling down network socket for 15 seconds (Post-Income)...")
        time.sleep(15)

    # =====================================================================
    # STAGE 5: BALANCE SHEET EXTRACTION (Cash Position & Debt-to-Equity)
    # =====================================================================
    balance_data, balance_was_live = _fetch_alpha_vantage("BALANCE_SHEET", ticker)

    if "Note" in balance_data or "Information" in balance_data:
         state["errors"].append(f"Alpha Vantage API Rate Limit Exceeded for {ticker} (BALANCE_SHEET).")
    else:
        annual_reports_bal = balance_data.get("annualReports", [])

        if len(annual_reports_bal) >= 1:
            latest_bal = annual_reports_bal[0]

            # 5a. Extract Cash Position
            raw_cash = latest_bal.get("cashAndCashEquivalentsAtCarryingValue")
            if raw_cash and raw_cash != "None":
                try:
                    fd["cash_position"] = float(raw_cash)
                except ValueError:
                    state["errors"].append(f"Parsing error for 'cash_position' on {ticker}.")
            else:
                state["errors"].append("Field 'cash_position' unavailable in BALANCE_SHEET payload.")

            # 5b. Calculate Debt to Equity
            st_debt = latest_bal.get("shortTermDebt")
            lt_debt = latest_bal.get("longTermDebt")
            equity = latest_bal.get("totalShareholderEquity")

            try:
                st_val = float(st_debt) if st_debt and st_debt != "None" else 0.0
                lt_val = float(lt_debt) if lt_debt and lt_debt != "None" else 0.0
                eq_val = float(equity) if equity and equity != "None" else 0.0

                if eq_val > 0:
                    fd["debt_to_equity"] = round((st_val + lt_val) / eq_val, 4)
                elif eq_val < 0:
                    state["errors"].append("Company has negative equity; standard debt_to_equity ratio is inapplicable.")
                else:
                    state["errors"].append("Cannot calculate debt_to_equity: Shareholder equity is zero.")
            except ValueError:
                state["errors"].append(f"Parsing error calculating 'debt_to_equity' on {ticker}.")
        else:
             state["errors"].append("BALANCE_SHEET annualReports array is empty.")

    # =====================================================================
    # STAGE 6 & 7: COMPLETENESS ASSESSMENT & BALANCED TIER GRADING
    # =====================================================================
    critical_fields = ["revenue", "net_income", "market_cap"]
    missing_critical = sum(1 for field in critical_fields if fd[field] is None)

    if "confidence_score" not in state:
        state["confidence_score"] = 1.0
    current_confidence = state["confidence_score"]

    if missing_critical >= 2:
        fd["data_complete"] = False
        current_confidence -= 0.3
    elif missing_critical == 1:
        # Note: Your original code marked data_complete = True here. Leaving as requested,
        # but technically missing a critical field should probably trigger False.
        fd["data_complete"] = True
        current_confidence -= 0.1
    else:
        fd["data_complete"] = True

    # Also check if secondary targets (debt, cash) failed and dock slight confidence
    if fd["debt_to_equity"] is None or fd["cash_position"] is None:
        current_confidence -= 0.05

    state["confidence_score"] = max(0.0, round(current_confidence, 2))
    state["financial_data"] = fd

    return state
