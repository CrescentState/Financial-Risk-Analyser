"""Mock data for testing - only loaded when USE_MOCK_DATA=true.
This mirrors the Alpha Vantage API response format."""
MOCK_DATA = {
    "AAPL": {
        "OVERVIEW": {
            "Symbol": "AAPL",
            "Name": "Apple Inc.",
            "MarketCapitalization": "4514709504000",
            "PERatio": "35.48",
            "DebtToEquity": "1.57",
            "RevenueTTM": "466822988000",
            "NetIncome": "112010000000",
            "CurrentRatio": "1.25",
            "CashPosition": "35934000000",
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
                    "totalCurrentAssets": "150000000000",
                    "totalCurrentLiabilities": "120000000000",
                    "cashAndCashEquivalentsAtCarryingValue": "35934000000",
                    "shortTermDebt": "10000000000",
                    "longTermDebt": "100000000000",
                    "totalShareholderEquity": "70000000000",
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
                {"totalRevenue": "103619002000", "netIncome": "3794000000"},
                {"totalRevenue": "106606000000", "netIncome": "5519000000"},
            ]
        },
        "BALANCE_SHEET": {
            "annualReports": [
                {
                    "totalCurrentAssets": "80000000000",
                    "totalCurrentLiabilities": "60000000000",
                    "cashAndCashEquivalentsAtCarryingValue": "16513000000",
                    "shortTermDebt": "1000000000",
                    "longTermDebt": "2000000000",
                    "totalShareholderEquity": "50000000000",
                    "cashPerSharePerShareAnnual": "1.2345",
                    "cashPerSharePerShareQuarterly": "1.5678"
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
                    "cashPerSharePerShareAnnual": "0.9876",
                    "cashPerSharePerShareQuarterly": "1.1234"
                }
            ]
        },
    },
}


def get_mock_data(ticker: str, function_name: str):
    """Get mock data for a ticker and function in Alpha Vantage format."""
    ticker_clean = ticker.strip().upper()
    mock_ticker = MOCK_DATA.get(ticker_clean, MOCK_DATA["ZZZINVALID"])
    return mock_ticker.get(function_name, {"Information": "Rate limit"}), True


def get_mock_yfinance_data(ticker: str):
    """Get mock data for a ticker in yfinance/Finnhub format."""
    ticker_clean = ticker.strip().upper()
    mock_ticker = MOCK_DATA.get(ticker_clean, MOCK_DATA["ZZZINVALID"])
    overview = mock_ticker.get("OVERVIEW", {})
    income = mock_ticker.get("INCOME_STATEMENT", {})
    balance = mock_ticker.get("BALANCE_SHEET", {})

    # Build financials for revenue growth
    financials = {}
    annual_reports = income.get("annualReports", [])
    if len(annual_reports) >= 2:
        rev_curr = annual_reports[0].get("totalRevenue")
        rev_prev = annual_reports[1].get("totalRevenue")
        if rev_curr and rev_prev:
            financials = {"total revenue": [float(rev_curr), float(rev_prev)]}

    # Build balance sheet dict
    balance_sheet = {}
    annual_bal = balance.get("annualReports", [])
    if annual_bal:
        latest = annual_bal[0]
        balance_sheet = {
            "Total Current Assets": float(latest.get("totalCurrentAssets", 0)) if latest.get("totalCurrentAssets") else None,
            "Total Current Liabilities": float(latest.get("totalCurrentLiabilities", 0)) if latest.get("totalCurrentLiabilities") else None,
            "Cash And Cash Equivalents": float(latest.get("cashAndCashEquivalentsAtCarryingValue", 0)) if latest.get("cashAndCashEquivalentsAtCarryingValue") else None,
            "Short Term Debt": float(latest.get("shortTermDebt", 0)) if latest.get("shortTermDebt") else None,
            "Long Term Debt": float(latest.get("longTermDebt", 0)) if latest.get("longTermDebt") else None,
            "Total Stockholder Equity": float(latest.get("totalShareholderEquity", 0)) if latest.get("totalShareholderEquity") else None,
        }

    # Build info dict
    info = {
        "marketCap": float(overview.get("MarketCapitalization", 0)) if overview.get("MarketCapitalization") else None,
        "trailingPE": float(overview.get("PERatio", 0)) if overview.get("PERatio") else None,
        "totalRevenue": float(overview.get("RevenueTTM", 0)) if overview.get("RevenueTTM") else None,
        "netIncomeToCommon": float(overview.get("NetIncome", 0)) if overview.get("NetIncome") else None,
        "currentRatio": float(overview.get("CurrentRatio", 0)) if overview.get("CurrentRatio") else None,
        "totalCash": float(overview.get("CashPosition", 0)) if overview.get("CashPosition") else None,
        "debtToEquity": float(overview.get("DebtToEquity", 0)) if overview.get("DebtToEquity") else None,
        "longName": overview.get("Name"),
        "shortName": overview.get("Symbol"),
    }

    return {
        "info": info,
        "financials": financials,
        "balance_sheet": balance_sheet,
    }