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


if __name__ == "__main__":
    pytest.main(["-v", __file__])