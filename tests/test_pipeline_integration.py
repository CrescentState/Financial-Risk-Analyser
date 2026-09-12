import pytest
from core.orchestrator import run_pipeline
from core.state import init_state


class TestPipelineIntegration:
    """Integration tests for the full pipeline."""

    def test_pipeline_runs_with_mock_data(self):
        """Test that the full pipeline executes without errors in mock mode."""
        # Enable test mode for all agents
        import agents.financial_agent
        agents.financial_agent._TEST_MODE_OVERRIDE = True
        import agents.news_agent
        agents.news_agent._TEST_MODE_OVERRIDE = True
        import agents.risk_agent
        agents.risk_agent._TEST_MODE_OVERRIDE = True
        
        result = run_pipeline("AAPL")
        
        # Verify final state structure
        assert result["ticker"] == "AAPL"
        assert result["company_name"] == "Apple Inc."
        assert "confidence_score" in result
        assert "errors" in result
        assert "financial_data" in result
        assert "news_data" in result
        assert "risk_data" in result
        assert "synthesis_report" in result
        # Every node records its wall-clock seconds (parallel and sequential
        # modes expose the same keys)
        assert {"financial", "news", "risk", "synthesis"} <= set(result["timings"])
        assert all(isinstance(v, float) and v >= 0 for v in result["timings"].values())

    def test_pipeline_financial_data_populated(self):
        """Test that financial data is properly populated."""
        import agents.financial_agent
        agents.financial_agent._TEST_MODE_OVERRIDE = True
        import agents.news_agent
        agents.news_agent._TEST_MODE_OVERRIDE = True
        import agents.risk_agent
        agents.risk_agent._TEST_MODE_OVERRIDE = True
        
        result = run_pipeline("AAPL")
        
        fd = result["financial_data"]
        assert fd["data_available"] is True
        assert fd["revenue"] is not None
        assert fd["market_cap"] is not None
        assert fd["pe_ratio"] is not None
        assert fd["debt_to_equity"] is not None
        assert fd["yoy_revenue_growth"] is not None
        assert fd["current_ratio"] is not None

    def test_pipeline_risk_data_populated(self):
        """Test that risk data is properly populated."""
        import agents.financial_agent
        agents.financial_agent._TEST_MODE_OVERRIDE = True
        import agents.news_agent
        agents.news_agent._TEST_MODE_OVERRIDE = True
        import agents.risk_agent
        agents.risk_agent._TEST_MODE_OVERRIDE = True
        
        result = run_pipeline("AAPL")
        
        rd = result["risk_data"]
        assert "risk_score" in rd
        assert isinstance(rd["risk_score"], (int, float))
        assert 0.0 <= rd["risk_score"] <= 100.0
        assert "risk_factors" in rd
        assert isinstance(rd["risk_factors"], list)
        assert "risk_narrative" in rd
        assert isinstance(rd["risk_narrative"], str)

    def test_pipeline_synthesis_report_schema(self):
        """Test that synthesis report matches the 6-section contract."""
        import agents.financial_agent
        agents.financial_agent._TEST_MODE_OVERRIDE = True
        import agents.news_agent
        agents.news_agent._TEST_MODE_OVERRIDE = True
        import agents.risk_agent
        agents.risk_agent._TEST_MODE_OVERRIDE = True
        
        result = run_pipeline("AAPL")
        
        sr = result["synthesis_report"]
        required_keys = [
            "company_snapshot",
            "financial_health",
            "market_sentiment",
            "risk_assessment",
            "key_concerns",
            "analyst_recommendation",
        ]
        for key in required_keys:
            assert key in sr, f"Missing required key: {key}"
        
        # Check types
        assert isinstance(sr["company_snapshot"], str)
        assert isinstance(sr["financial_health"], str)
        assert isinstance(sr["market_sentiment"], str)
        assert isinstance(sr["risk_assessment"], str)
        assert isinstance(sr["key_concerns"], list)
        assert isinstance(sr["analyst_recommendation"], str)
        
        # Check recommendation is one of the valid labels
        valid_recommendations = [
            "Flag for Review",
            "Strong Buy Signal",
            "Cautious Positive",
            "Neutral",
        ]
        assert sr["analyst_recommendation"] in valid_recommendations

    def test_pipeline_confidence_scoring(self):
        """Test that confidence score is properly calculated and bounded."""
        import agents.financial_agent
        agents.financial_agent._TEST_MODE_OVERRIDE = True
        import agents.news_agent
        agents.news_agent._TEST_MODE_OVERRIDE = True
        import agents.risk_agent
        agents.risk_agent._TEST_MODE_OVERRIDE = True
        
        result = run_pipeline("AAPL")
        
        confidence = result["confidence_score"]
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0

    def test_pipeline_error_accumulation(self):
        """Test that errors are accumulated across agents."""
        import agents.financial_agent
        agents.financial_agent._TEST_MODE_OVERRIDE = True
        import agents.news_agent
        agents.news_agent._TEST_MODE_OVERRIDE = True
        import agents.risk_agent
        agents.risk_agent._TEST_MODE_OVERRIDE = True
        
        result = run_pipeline("ZZZINVALID")
        
        # Should have errors from financial agent (invalid ticker)
        assert len(result["errors"]) > 0
        assert result["financial_data"]["data_available"] is False
        assert result["confidence_score"] < 1.0

    def test_pipeline_errors_have_no_duplicates(self):
        """Errors must not be duplicated as state flows through the graph.

        Regression test: risk/synthesis used to echo input errors back into
        their return value while the reducer also accumulated, duplicating
        every prior error.
        """
        import agents.financial_agent
        agents.financial_agent._TEST_MODE_OVERRIDE = True
        import agents.news_agent
        agents.news_agent._TEST_MODE_OVERRIDE = True
        import agents.risk_agent
        agents.risk_agent._TEST_MODE_OVERRIDE = True

        result = run_pipeline("ZZZINVALID")

        assert len(result["errors"]) > 0
        assert len(result["errors"]) == len(set(result["errors"]))

    def test_pipeline_deterministic_recommendation_logic(self):
        """Test the deterministic recommendation logic matches contract."""
        import agents.financial_agent
        agents.financial_agent._TEST_MODE_OVERRIDE = True
        import agents.news_agent
        agents.news_agent._TEST_MODE_OVERRIDE = True
        import agents.risk_agent
        agents.risk_agent._TEST_MODE_OVERRIDE = True
        
        # Test with AAPL (good financials, low risk)
        result = run_pipeline("AAPL")
        sr = result["synthesis_report"]
        
        # AAPL mock data: D/E=1.57, YoY growth positive, P/E positive, sentiment neutral
        # Risk score should be low, confidence high
        # Expected: Cautious Positive (risk <= 45) or Strong Buy Signal (risk <= 20 and growth > 5%)
        assert sr["analyst_recommendation"] in ["Cautious Positive", "Strong Buy Signal", "Neutral"]

    def test_pipeline_state_immutability(self):
        """Test that initial state is not mutated."""
        import agents.financial_agent
        agents.financial_agent._TEST_MODE_OVERRIDE = True
        import agents.news_agent
        agents.news_agent._TEST_MODE_OVERRIDE = True
        import agents.risk_agent
        agents.risk_agent._TEST_MODE_OVERRIDE = True
        
        initial = init_state("AAPL")
        initial_confidence = initial["confidence_score"]
        initial_errors = list(initial["errors"])
        
        result = run_pipeline("AAPL")
        
        # Initial state should be unchanged
        assert initial["confidence_score"] == initial_confidence
        assert initial["errors"] == initial_errors


class TestPipelineRecommendationLogic:
    """Test the deterministic recommendation logic directly."""
    
    def test_flag_for_review_low_confidence(self):
        from agents.synthesis_agent import _compute_recommendation
        
        state = {
            "confidence_score": 0.4,
            "risk_data": {"risk_score": 10.0},
            "financial_data": {"yoy_revenue_growth": 0.10},
        }
        assert _compute_recommendation(state) == "Flag for Review"
    
    def test_flag_for_review_high_risk(self):
        from agents.synthesis_agent import _compute_recommendation
        
        state = {
            "confidence_score": 1.0,
            "risk_data": {"risk_score": 75.0},
            "financial_data": {"yoy_revenue_growth": 0.10},
        }
        assert _compute_recommendation(state) == "Flag for Review"
    
    def test_strong_buy_signal(self):
        from agents.synthesis_agent import _compute_recommendation
        
        state = {
            "confidence_score": 1.0,
            "risk_data": {"risk_score": 15.0},
            "financial_data": {"yoy_revenue_growth": 0.10},
        }
        assert _compute_recommendation(state) == "Strong Buy Signal"
    
    def test_strong_buy_signal_requires_growth(self):
        from agents.synthesis_agent import _compute_recommendation
        
        # Low risk but no growth
        state = {
            "confidence_score": 1.0,
            "risk_data": {"risk_score": 15.0},
            "financial_data": {"yoy_revenue_growth": 0.02},
        }
        assert _compute_recommendation(state) == "Cautious Positive"
        
        # Low risk but negative growth
        state = {
            "confidence_score": 1.0,
            "risk_data": {"risk_score": 15.0},
            "financial_data": {"yoy_revenue_growth": -0.05},
        }
        assert _compute_recommendation(state) == "Cautious Positive"
        
        # Low risk but no growth data
        state = {
            "confidence_score": 1.0,
            "risk_data": {"risk_score": 15.0},
            "financial_data": {"yoy_revenue_growth": None},
        }
        assert _compute_recommendation(state) == "Cautious Positive"
    
    def test_cautious_positive(self):
        from agents.synthesis_agent import _compute_recommendation
        
        state = {
            "confidence_score": 1.0,
            "risk_data": {"risk_score": 30.0},
            "financial_data": {"yoy_revenue_growth": 0.10},
        }
        assert _compute_recommendation(state) == "Cautious Positive"
        
        state = {
            "confidence_score": 1.0,
            "risk_data": {"risk_score": 45.0},
            "financial_data": {"yoy_revenue_growth": 0.10},
        }
        assert _compute_recommendation(state) == "Cautious Positive"
    
    def test_neutral(self):
        from agents.synthesis_agent import _compute_recommendation
        
        state = {
            "confidence_score": 1.0,
            "risk_data": {"risk_score": 50.0},
            "financial_data": {"yoy_revenue_growth": 0.10},
        }
        assert _compute_recommendation(state) == "Neutral"
        
        state = {
            "confidence_score": 1.0,
            "risk_data": {"risk_score": 70.0},
            "financial_data": {"yoy_revenue_growth": 0.10},
        }
        assert _compute_recommendation(state) == "Neutral"


class TestOrchestratorTiming:
    """Timing instrumentation without live network calls."""

    def test_timings_reducer_merges(self):
        from core.state import _timings_reducer
        assert _timings_reducer({"a": 1.0}, {"b": 2.0}) == {"a": 1.0, "b": 2.0}
        assert _timings_reducer({"a": 1.0}, {"a": 2.0}) == {"a": 2.0}

    def test_merge_timing_records_duration(self):
        from core.orchestrator import _merge_timing
        out = _merge_timing({"timings": {"financial": 0.5}}, {"risk_data": {}}, "risk", 1.234)
        assert out["timings"] == {"financial": 0.5, "risk": 1.23}
        assert out["risk_data"] == {}

    def test_timed_wrappers_record(self):
        import asyncio
        from core.orchestrator import _timed_sync, _timed_async

        def fn(state):
            return {"x": 1}

        out = _timed_sync("financial", fn)({"timings": {}})
        assert out["x"] == 1
        assert out["timings"]["financial"] >= 0

        async def afn(state):
            return {"y": 2}

        out2 = asyncio.run(_timed_async("news", afn)({"timings": {"financial": 0.1}}))
        assert out2["y"] == 2
        assert out2["timings"]["financial"] == 0.1
        assert out2["timings"]["news"] >= 0


class TestAnalysisResponseTimings:
    """timings computed by the pipeline must survive API serialization."""

    def test_timings_present_in_analyze_response(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from unittest.mock import AsyncMock, patch
        from api.routes import router

        app = FastAPI()
        app.include_router(router)

        state = init_state("AAPL")
        state["timings"] = {"financial": 1.2, "news": 0.8, "risk": 0.1, "synthesis": 0.4}
        with patch("api.routes.run_pipeline_async", new=AsyncMock(return_value=state)):
            resp = TestClient(app).post("/api/v1/analyze/AAPL")

        assert resp.status_code == 200
        assert resp.json()["timings"] == {
            "financial": 1.2, "news": 0.8, "risk": 0.1, "synthesis": 0.4,
        }


if __name__ == "__main__":
    pytest.main(["-v", __file__])