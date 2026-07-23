import requests
import yfinance as yf


def test_yfinance_connection():
    print("=" * 50)
    print("YFINANCE SANITY CHECK RUNNER")
    print("=" * 50)

    ticker_str = "AAPL"
    print(f"[*] Instantiating Ticker object for: {ticker_str}")
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    )
    ticker = yf.Ticker(ticker_str, session=session)

    # 1. Test .info fetching (Network API call)
    try:
        print("[*] Attempting to fetch '.info' dictionary...")
        info = ticker.info
        if isinstance(info, dict) and len(info) > 0:
            print("  🟢 SUCCESS: Info dictionary retrieved.")
            print(f"  🏢 Company Name: {info.get('longName')}")
            print(f"  💰 Market Cap  : {info.get('marketCap')}")
        else:
            print(
                "  🔴 FAILURE: .info returned an empty dictionary (Silent Failure Mode)."
            )
    except Exception as e:
        print(f"  🔴 EXCEPTION: Failed to read .info attribute. Error: {e}")

    print("-" * 50)

    # 2. Test Historical Dataframe fetching (Pandas parsing check)
    try:
        print("[*] Attempting to fetch '.quarterly_financials'...")
        q_fin = ticker.quarterly_financials
        if q_fin is not None and not q_fin.empty:
            print("  🟢 SUCCESS: Quarterly financials dataframe retrieved.")
            print(f"  📊 Shape of DataFrame: {q_fin.shape}")
            print(f"  📑 Available Row Labels:\n{list(q_fin.index[:5])}...")
        else:
            print("  🔴 FAILURE: quarterly_financials returned an empty DataFrame.")
    except Exception as e:
        print(f"  🔴 EXCEPTION: Failed to read quarterly_financials. Error: {e}")

    print("=" * 50)


if __name__ == "__main__":
    test_yfinance_connection()
