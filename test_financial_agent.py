import os
import time
from core.state import State

# 1. ENSURE LIVE NETWORK OPERATION IS ACTIVE
os.environ["USE_MOCK_DATA"] = "False"
# Ensure your key is accessible in your environment variables
# os.environ["ALPHA_VANTAGE_KEY"] = "YOUR_ACTUAL_KEY"

from agents.financial_agent import financial_agent


def execute_live_pipeline_test(ticker_symbol: str):
    print("\n" + "=" * 80)
    print(f"🚀 LIVE DEPLOYMENT PIPELINE RUNNER FOR: {ticker_symbol}")
    print("=" * 80)

    # Setup initial clean test state
    initial_state: State = {
        "ticker": ticker_symbol.strip().upper(),
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
            "data_complete": False,
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

    # Process the state through the financial agent
    updated_state = financial_agent(initial_state)

    # 2. DUMP THE DATA EXTRACTION PAYLOAD
    print("📊 EXTRACTION DATA CONTRACT RESULTS:")
    fd = updated_state.get("financial_data", {})
    if fd:
        for metric, value in fd.items():
            print(f"   • {metric.ljust(18)}: {value}")
    else:
        print("   🔴 Critical: No financial_data block was written to state.")

    # 3. DUMP EVERY ENCOUNTERED ERROR TRACE
    print("\n📝 SYSTEM ERROR LOG TRACE:")
    errors = updated_state.get("errors", [])
    if errors:
        for i, error_msg in enumerate(errors, 1):
            print(f"   {i}. ❌ {error_msg}")
    else:
        print("   🟢 Zero anomalies recorded in the execution pipeline.")

    print("=" * 80 + "\n")


if __name__ == "__main__":
    # Test a live asset
    execute_live_pipeline_test("AAPL")

    # IF YOU TEST MULTIPLE ASSETS, UNCOMMENT THIS SLEEP LAYER:
    # Alpha Vantage limits free tier keys to 5 requests per minute.
    print("⏳ Cooling down network socket for 15s to preserve API threshold limits...")
    time.sleep(15)
    execute_live_pipeline_test("RELIANCE.NS")
    print("⏳ Cooling down network socket for 15s to preserve API threshold limits...")
    time.sleep(15)
    execute_live_pipeline_test("TSLA")
    print("⏳ Cooling down network socket for 15s to preserve API threshold limits...")
    time.sleep(15)
    execute_live_pipeline_test("ZZZINVALID")
    print("⏳ Cooling down network socket for 15s to preserve API threshold limits...")
    time.sleep(15)
    execute_live_pipeline_test("TWTR")
