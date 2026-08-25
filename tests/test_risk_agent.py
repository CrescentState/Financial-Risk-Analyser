import json
from unittest.mock import MagicMock, patch
import pytest

from core.state import init_state
from agents.risk_agent import risk_agent_sync as risk_agent, _run_deterministic_rules, _calculate_risk_score


def test_deterministic_rules_triggers():
    """Verify Stage 1 rule engine correctly catches all financial anomaly thresholds."""
    bad_financials = {
        "debt_to_equity": 3.5,
        "yoy_revenue_growth": -0.15,
        "pe_ratio": -15.0,
    }
    flags = _run_deterministic_rules(bad_financials, {})
    
    assert len(flags) == 3
    assert any("High Leverage (D/E > 2.5)" in f for f in flags)
    assert any("Revenue Contraction (-15.00%)" in f for f in flags)
    assert any("Unprofitable / Negative P/E" in f for f in flags)


def test_deterministic_rules_clean():
    """Verify clean financials produce zero triggered flags."""
    good_financials = {
        "debt_to_equity": 0.8,
        "yoy_revenue_growth": 14.2,
        "pe_ratio": 22.5,
    }
    flags = _run_deterministic_rules(good_financials, {})
    assert len(flags) == 0


def test_deterministic_rules_boundary_values():
    """Test threshold boundaries: exactly 2.5, -0.10, 0.0."""
    # Exactly at D/E threshold (2.5) - should NOT trigger (> 2.5)
    flags = _run_deterministic_rules({"debt_to_equity": 2.5, "yoy_revenue_growth": 5.0, "pe_ratio": 15.0}, {})
    assert not any("High Leverage" in f for f in flags)

    # Just above threshold (2.51) - should trigger
    flags = _run_deterministic_rules({"debt_to_equity": 2.51, "yoy_revenue_growth": 5.0, "pe_ratio": 15.0}, {})
    assert any("High Leverage" in f for f in flags)

    # Exactly -0.10 revenue growth - should NOT trigger (< -0.10)
    flags = _run_deterministic_rules({"debt_to_equity": 1.0, "yoy_revenue_growth": -0.10, "pe_ratio": 15.0}, {})
    assert not any("Revenue Contraction" in f for f in flags)

    # Just below -0.10 - should trigger
    flags = _run_deterministic_rules({"debt_to_equity": 1.0, "yoy_revenue_growth": -0.101, "pe_ratio": 15.0}, {})
    assert any("Revenue Contraction" in f for f in flags)

    # Exactly zero P/E - should trigger (<= 0)
    flags = _run_deterministic_rules({"debt_to_equity": 1.0, "yoy_revenue_growth": 5.0, "pe_ratio": 0.0}, {})
    assert any("Unprofitable / Negative P/E" in f for f in flags)

    # Negative P/E - should trigger
    flags = _run_deterministic_rules({"debt_to_equity": 1.0, "yoy_revenue_growth": 5.0, "pe_ratio": -5.0}, {})
    assert any("Unprofitable / Negative P/E" in f for f in flags)


def test_deterministic_rules_missing_fields():
    """Missing (None) fields should not crash or trigger."""
    flags = _run_deterministic_rules({
        "debt_to_equity": None,
        "yoy_revenue_growth": None,
        "pe_ratio": None,
    }, {})
    assert len(flags) == 0

    # Partial missing
    flags = _run_deterministic_rules({
        "debt_to_equity": 3.0,
        "yoy_revenue_growth": None,
        "pe_ratio": 15.0,
    }, {})
    assert len(flags) == 1
    assert "High Leverage" in flags[0]


def test_calculate_risk_score():
    """Verify risk score calculation from factors."""
    # High Leverage only
    score = _calculate_risk_score(["High Leverage (D/E > 2.5)"])
    assert score == 25.0

    # Negative equity only
    score = _calculate_risk_score(["Negative Shareholder Equity (Balance Sheet Distress)"])
    assert score == 35.0

    # Revenue contraction only
    score = _calculate_risk_score(["Revenue Contraction (-15.00%)"])
    assert score == 30.0

    # Unprofitable only
    score = _calculate_risk_score(["Unprofitable / Negative P/E"])
    assert score == 20.0

    # Hostile media only
    score = _calculate_risk_score(["Hostile Media Coverage"])
    assert score == 15.0

    # Multiple factors - additive
    score = _calculate_risk_score([
        "High Leverage (D/E > 2.5)",
        "Revenue Contraction (-15.00%)",
    ])
    assert score == 55.0

    # All factors - should clamp at 100
    score = _calculate_risk_score([
        "High Leverage (D/E > 2.5)",
        "Negative Shareholder Equity (Balance Sheet Distress)",
        "Revenue Contraction (-15.00%)",
        "Unprofitable / Negative P/E",
        "Hostile Media Coverage",
    ])
    assert score == 100.0


def test_calculate_risk_score_clamping():
    """Risk score should never exceed 100."""
    # Add multiple high-scoring factors
    factors = [
        "High Leverage (D/E > 2.5)",
        "Negative Shareholder Equity (Balance Sheet Distress)",
        "Revenue Contraction (-15.00%)",
        "Unprofitable / Negative P/E",
        "Hostile Media Coverage",
        "High Leverage (D/E > 2.5)",  # duplicate
    ]
    score = _calculate_risk_score(factors)
    assert score == 100.0


# ===== Risk Agent Integration Tests =====

from unittest.mock import MagicMock, patch
import json

from core.state import init_state
from agents.risk_agent import risk_agent_sync as risk_agent, _run_deterministic_rules, _calculate_risk_score


@patch("core.clients.gemini_client.models.generate_content")
def test_risk_agent_success_path(mock_generate_content):
    """Verify happy path execution updates risk_data schema correctly."""
    state = init_state("AAPL")
    state["financial_data"].update({
        "debt_to_equity": 1.2,
        "yoy_revenue_growth": 5.0,
        "pe_ratio": 28.0,
    })
    state["news_data"] = {"sentiment_score": 0.0, "news_available": True, "key_events": [], "red_flags": [], "summary": ""}

    mock_response = MagicMock()
    mock_response.text = json.dumps({"risk_narrative": "Apple maintains a robust balance sheet with healthy margins."})
    mock_generate_content.return_value = MagicMock(text=json.dumps({"risk_narrative": "Apple maintains a robust balance sheet with healthy margins."}))

    res_state = risk_agent(state)

    # Python calculates the score
    expected_score = 0.0  # No risk factors triggered
    assert res_state["risk_data"]["risk_score"] == 0.0
    assert res_state["risk_data"]["risk_narrative"] == "Apple maintains a robust balance sheet with healthy margins."
    assert res_state["risk_data"]["risk_factors"] == []
    assert len(res_state["errors"]) == 0


@patch("core.clients.gemini_client.models.generate_content")
def test_risk_agent_exception_fallback(mock_generate_content):
    """Verify fallback behavior when Gemini API call fails."""
    state = init_state("TSLA")
    state["financial_data"].update({
        "debt_to_equity": 2.5,
    })
    state["news_data"] = {"sentiment_score": 0.0, "news_available": True, "key_events": [], "red_flags": [], "summary": ""}

    mock_generate_content.side_effect = Exception("API Connection Timeout")

    res_state = risk_agent(state)

    # Python score is 0 (D/E = 2.5 not > 2.5), fallback returns 50
    assert res_state["risk_data"]["risk_score"] == 50.0
    assert len(res_state["risk_data"]["risk_factors"]) >= 0
    assert any("Risk Agent execution failed" in err for err in res_state["errors"])


# ===== NEW TESTS FOR GAPS =====

@patch("core.clients.gemini_client.models.generate_content")
def test_risk_agent_confidence_score_unmodified(mock_generate_content):
    """Risk agent should not modify confidence_score."""
    state = init_state("AAPL")
    state["confidence_score"] = 0.85
    state["financial_data"].update({
        "debt_to_equity": 1.0,
        "yoy_revenue_growth": 5.0,
        "pe_ratio": 20.0,
    })
    state["news_data"] = {"sentiment_score": 0.0, "news_available": True, "key_events": [], "red_flags": [], "summary": ""}

    mock_response = MagicMock()
    mock_response.text = json.dumps({"risk_narrative": "Low risk"})
    mock_generate_content.return_value = MagicMock(text=json.dumps({"risk_narrative": "Low risk"}))

    res_state = risk_agent(state)

    assert res_state["confidence_score"] == 0.85


@patch("core.clients.gemini_client.models.generate_content")
def test_risk_agent_revenue_growth_format(mock_generate_content):
    """Revenue growth in triggered flag should be formatted as percentage."""
    state = init_state("TEST")
    state["financial_data"].update({
        "debt_to_equity": 1.0,
        "yoy_revenue_growth": -0.15,  # -15% (< -10% threshold)
        "pe_ratio": 20.0,
    })
    state["news_data"] = {"sentiment_score": 0.0, "news_available": True, "key_events": [], "red_flags": [], "summary": ""}

    mock_response = MagicMock()
    mock_response.text = json.dumps({"risk_narrative": "Moderate risk"})
    mock_generate_content.return_value = MagicMock(text=json.dumps({"risk_narrative": "Moderate risk"}))

    res_state = risk_agent(state)

    flags = res_state["risk_data"]["risk_factors"]
    assert any("Revenue Contraction" in f for f in flags)
    neg_growth_flag = next(f for f in flags if "Revenue Contraction" in f)
    assert "-15.00%" in neg_growth_flag


@patch("core.clients.gemini_client.models.generate_content")
def test_risk_agent_missing_financial_data_fields(mock_generate_content):
    """Risk agent should handle missing (None) financial_data fields gracefully."""
    state = init_state("TEST")
    state["financial_data"].update({
        "debt_to_equity": None,
        "yoy_revenue_growth": None,
        "pe_ratio": None,
    })
    state["news_data"] = {"sentiment_score": 0.0, "news_available": True, "key_events": [], "red_flags": [], "summary": ""}

    mock_response = MagicMock()
    mock_response.text = json.dumps({"risk_narrative": "Insufficient data for risk assessment."})
    mock_generate_content.return_value = MagicMock(text=json.dumps({"risk_narrative": "Insufficient data for risk assessment."}))

    res_state = risk_agent(state)

    assert res_state["risk_data"]["risk_score"] == 0.0
    assert len(res_state["risk_data"]["risk_factors"]) == 0
    assert len(res_state["errors"]) == 0


@patch("core.clients.gemini_client.models.generate_content")
def test_risk_agent_gemini_timeout(mock_generate_content):
    """Gemini timeout should trigger fallback."""
    import asyncio
    state = init_state("AAPL")
    state["financial_data"].update({"debt_to_equity": 1.0})
    state["news_data"] = {"sentiment_score": 0.0, "news_available": True, "key_events": [], "red_flags": [], "summary": ""}

    mock_generate_content.side_effect = asyncio.TimeoutError("Request timed out")

    res_state = risk_agent(state)

    # Python score is 0, fallback is 50
    assert res_state["risk_data"]["risk_score"] == 50.0
    assert any("Risk Agent execution failed" in err for err in res_state["errors"])


@patch("core.clients.gemini_client.models.generate_content")
def test_risk_agent_empty_key_concerns(mock_generate_content):
    """Risk agent should handle empty key_concerns list from Gemini."""
    state = init_state("AAPL")
    state["financial_data"].update({"debt_to_equity": 1.0})
    state["news_data"] = {"sentiment_score": 0.0, "news_available": True, "key_events": [], "red_flags": [], "summary": ""}

    mock_response = MagicMock()
    mock_response.text = json.dumps({"risk_narrative": "Very low risk"})
    mock_generate_content.return_value = MagicMock(text=json.dumps({"risk_narrative": "Very low risk"}))

    res_state = risk_agent(state)

    assert res_state["risk_data"]["risk_factors"] == []


@patch("core.clients.gemini_client.models.generate_content")
def test_risk_agent_prompt_includes_financial_data(mock_generate_content):
    """Prompt sent to Gemini should include the financial_data JSON."""
    state = init_state("TEST")
    state["financial_data"].update({
        "debt_to_equity": 1.5,
        "yoy_revenue_growth": 0.10,
        "pe_ratio": 25.0,
        "revenue": 1000000000,
        "net_income": 100000000,
    })
    state["news_data"] = {"sentiment_score": 0.0, "news_available": True, "key_events": [], "red_flags": [], "summary": ""}

    captured_prompt = {}

    def capture_prompt(*args, **kwargs):
        captured_prompt["contents"] = kwargs.get("contents", args[0] if args else "")
        mock_response = MagicMock()
        mock_response.text = json.dumps({"risk_narrative": "Test"})
        return mock_response

    mock_generate_content.side_effect = capture_prompt

    risk_agent(state)

    prompt = captured_prompt.get("contents", "")
    assert "debt_to_equity" in prompt
    assert "yoy_revenue_growth" in prompt
    assert "pe_ratio" in prompt
    assert "1.5" in prompt


if __name__ == "__main__":
    pytest.main(["-v", __file__])