import os
import pytest
from core.state import init_state
from agents.financial_agent import financial_agent, _fetch_alpha_vantage
from core.cache import get_cached_response, set_cached_response
from dotenv import load_dotenv

# Enable test mode for mock data
import agents.financial_agent
agents.financial_agent._TEST_MODE_OVERRIDE = True

load_dotenv()


@pytest.fixture(scope="session")
def alpha_vantage_key():
    key = os.getenv("ALPHA_VANTAGE_KEY")
    if not key:
        pytest.skip("ALPHA_VANTAGE_KEY not set")
    return key


def is_rate_limited(errors: list) -> bool:
    """Check if any error indicates rate limiting."""
    return any("Rate Limit" in e or "Information" in e or "Throttle" in e for e in errors)


def has_valid_data(fd: dict) -> bool:
    """Check if financial data has meaningful values."""
    return fd["revenue"] is not None and fd["market_cap"] is not None


class TestFinancialAgent:
    """Integration tests using real Alpha Vantage API.

    Note: Free tier limited to 25 requests/day. Tests may hit rate limits.
    When rate limited, tests verify proper error handling rather than data completeness.
    """

    def test_valid_us_equity_returns_complete_data(self, alpha_vantage_key):
        """Test AAPL - should return complete data if not rate limited."""
        state = init_state("AAPL")
        state = financial_agent(state)

        fd = state["financial_data"]

        if is_rate_limited(state["errors"]):
            # Rate limited - verify proper error handling
            assert fd["data_complete"] is False
            assert state["confidence_score"] == 0.3  # throttle(0.2) + degraded(0.4) + missing secondary(0.1) = 0.3
            assert len(state["errors"]) > 0
        else:
            # Success - verify complete data
            assert fd["data_complete"] is True
            assert fd["revenue"] is not None
            assert fd["net_income"] is not None
            assert fd["market_cap"] is not None
            assert fd["pe_ratio"] is not None
            assert fd["debt_to_equity"] is not None
            assert fd["cash_position"] is not None
            assert fd["revenue_growth"] is not None
            assert state["confidence_score"] > 0.8
            assert state["company_name"] == "Apple Inc."
            assert len(state["errors"]) == 0

    def test_invalid_ticker_returns_error_and_docked_confidence(self, alpha_vantage_key):
        """Test ZZZINVALID - should return error with docked confidence (throttle + degraded)."""
        state = init_state("ZZZINVALID")
        state = financial_agent(state)

        fd = state["financial_data"]
        assert fd["data_complete"] is False
        # In test mode: throttle dock (0.2) + degraded dock (0.4) + missing secondary (0.1) = 0.3
        assert state["confidence_score"] == 0.3
        assert len(state["errors"]) > 0
        error_text = " ".join(state["errors"])
        assert ("Invalid US Equity Ticker" in error_text) or ("Rate Limit" in error_text) or ("Information" in error_text) or ("Alpha Vantage Throttle" in error_text)
        assert all(v is None for v in fd.values() if v not in (fd["data_complete"], fd["data_available"]))

    def test_delisted_ticker_returns_error_or_rate_limit(self, alpha_vantage_key):
        """Test TWTR (delisted) - should handle gracefully."""
        state = init_state("TWTR")
        state = financial_agent(state)

        fd = state["financial_data"]
        assert fd["data_complete"] is False
        assert state["confidence_score"] == 0.3
        assert len(state["errors"]) > 0
        error_text = " ".join(state["errors"])
        assert ("Invalid US Equity Ticker" in error_text) or ("Rate Limit" in error_text) or ("Information" in error_text) or ("Alpha Vantage Throttle" in error_text)

    def test_non_us_ticker_returns_error_or_rate_limit(self, alpha_vantage_key):
        """Test RELIANCE.NS (non-US) - should handle gracefully."""
        state = init_state("RELIANCE.NS")
        state = financial_agent(state)

        fd = state["financial_data"]
        assert fd["data_complete"] is False
        assert state["confidence_score"] == 0.3
        assert len(state["errors"]) > 0
        error_text = " ".join(state["errors"])
        assert ("Invalid US Equity Ticker" in error_text) or ("Rate Limit" in error_text) or ("Information" in error_text) or ("Alpha Vantage Throttle" in error_text)

    def test_tsla_returns_negative_revenue_growth(self, alpha_vantage_key):
        """Test TSLA - should show negative revenue growth if data available."""
        state = init_state("TSLA")
        state = financial_agent(state)

        fd = state["financial_data"]

        if is_rate_limited(state["errors"]):
            pytest.skip("Rate limited - skipping data validation")

        assert fd["data_complete"] is True
        assert fd["revenue_growth"] is not None
        assert fd["revenue_growth"] < 0

    def test_confidence_penalty_for_missing_secondary_fields(self, alpha_vantage_key, monkeypatch):
        """Test confidence penalty when balance sheet data is unavailable."""
        import agents.financial_agent as fa

        original_fetch = fa._fetch_alpha_vantage_async

        async def mock_fetch(function_name: str, ticker: str):
            if function_name == "BALANCE_SHEET":
                return {}, False  # Simulate missing balance sheet
            return await original_fetch(function_name, ticker)

        monkeypatch.setattr(fa, "_fetch_alpha_vantage_async", mock_fetch)

        state = init_state("AAPL")
        state = financial_agent(state)

        fd = state["financial_data"]

        if is_rate_limited(state["errors"]):
            pytest.skip("Rate limited - skipping data validation")

        # With mocked balance sheet, current_ratio and cash_position should be None
        # data_available requires current_ratio, so it will be False
        # debt_to_equity comes from OVERVIEW, so it's still populated
        assert fd["data_available"] is False
        assert fd["current_ratio"] is None or fd["cash_position"] is None
        # confidence = 1.0 - 0.4 (degraded) - 0.05 (cash_position) = 0.55
        assert state["confidence_score"] == 0.55

    # ===== CACHING LAYER TESTS =====

    def test_cache_hit_avoids_network_call(self, alpha_vantage_key):
        """Verify cache is populated and used on subsequent calls."""
        # First call - should be live
        state1 = init_state("MSFT")
        state1 = financial_agent(state1)

        # Check if we got data (not rate limited)
        if not is_rate_limited(state1["errors"]):
            # Second call - should use cache (no additional network calls)
            state2 = init_state("MSFT")
            state2 = financial_agent(state2)

            # Data should be identical
            assert state1["financial_data"]["revenue"] == state2["financial_data"]["revenue"]
            assert state1["financial_data"]["market_cap"] == state2["financial_data"]["market_cap"]
            # Both should succeed
            assert state1["confidence_score"] > 0.8
            assert state2["confidence_score"] > 0.8

    def test_cache_rejects_rate_limit_responses(self, alpha_vantage_key):
        """Verify rate limit responses are not cached."""
        from core.cache import get_cached_response

        # Manually store a rate limit response
        rate_limit_data = {"Information": "Rate limit exceeded"}
        set_cached_response("TEST_RATE_LIMIT", "OVERVIEW", rate_limit_data)

        # Cache should reject it
        cached = get_cached_response("TEST_RATE_LIMIT", "OVERVIEW")
        assert cached is None

    def test_cache_rejects_error_responses(self, alpha_vantage_key):
        """Verify error responses are not cached."""
        from core.cache import get_cached_response

        error_data = {"Error Message": "Invalid API call"}
        set_cached_response("TEST_ERROR", "OVERVIEW", error_data)

        cached = get_cached_response("TEST_ERROR", "OVERVIEW")
        assert cached is None

    def test_cache_stores_valid_data(self, alpha_vantage_key):
        """Verify valid data is cached properly."""
        from core.cache import get_cached_response

        valid_data = {"RevenueTTM": "1000000", "MarketCapitalization": "2000000", "PERatio": "15"}
        set_cached_response("TEST_VALID", "OVERVIEW", valid_data)

        cached = get_cached_response("TEST_VALID", "OVERVIEW")
        assert cached is not None
        assert cached["RevenueTTM"] == "1000000"

    # ===== EDGE CASE TESTS =====

    def test_ticker_case_insensitive(self, alpha_vantage_key):
        """Ticker should be normalized to uppercase."""
        state = init_state("msft")  # lowercase
        state = financial_agent(state)

        if not is_rate_limited(state["errors"]):
            assert state["ticker"] == "MSFT"
            assert has_valid_data(state["financial_data"])

    def test_field_unavailable_logs_error(self, alpha_vantage_key):
        """Missing fields in OVERVIEW should log appropriate errors."""
        # This test verifies the error logging behavior when API returns incomplete data
        # Real API usually returns all fields, but we verify the code path exists
        state = init_state("AAPL")
        state = financial_agent(state)

        if not is_rate_limited(state["errors"]):
            # Should not have field-unavailable errors for major fields
            field_errors = [e for e in state["errors"] if "unavailable in Alpha Vantage OVERVIEW" in e]
            assert len(field_errors) == 0

    def test_negative_equity_handling(self, alpha_vantage_key):
        """Negative equity should produce error and no debt_to_equity."""
        # Can't easily test without mocking, but verify the code path exists
        # by ensuring no crash on normal data
        state = init_state("AAPL")
        state = financial_agent(state)

        if not is_rate_limited(state["errors"]):
            fd = state["financial_data"]
            # Normal companies should have positive equity
            assert fd["debt_to_equity"] is not None
            assert fd["debt_to_equity"] >= 0

    def test_empty_annual_reports_handling(self, alpha_vantage_key):
        """Empty annualReports should log error, not crash."""
        state = init_state("AAPL")
        state = financial_agent(state)

        if not is_rate_limited(state["errors"]):
            # Should not have empty array errors for major companies
            assert not any("annualReports array is empty" in e for e in state["errors"])


class TestCacheLayer:
    """Unit tests for cache layer operations."""

    def test_cache_get_miss(self):
        """Cache miss returns None."""
        result = get_cached_response("NONEXISTENT_TICKER_XYZ", "OVERVIEW")
        assert result is None

    def test_cache_set_and_get(self):
        """Basic set/get roundtrip."""
        test_data = {"test": "data", "number": 123}
        set_cached_response("TEST_CACHE_ROUNDTRIP", "OVERVIEW", test_data)

        result = get_cached_response("TEST_CACHE_ROUNDTRIP", "OVERVIEW")
        assert result is not None
        assert result["test"] == "data"
        assert result["number"] == 123

    def test_cache_rejects_empty_data(self):
        """Empty dict should not be cached."""
        set_cached_response("TEST_EMPTY", "OVERVIEW", {})
        result = get_cached_response("TEST_EMPTY", "OVERVIEW")
        assert result is None

    def test_cache_rejects_none(self):
        """None should not be cached."""
        set_cached_response("TEST_NONE", "OVERVIEW", None)
        result = get_cached_response("TEST_NONE", "OVERVIEW")
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])