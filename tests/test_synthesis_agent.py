"""Unit tests for the Synthesis Agent (agents/synthesis_agent.py).

Covers deterministic recommendation rules, boundary conditions, state
preservation, schema integrity, and LLM fallback handling.
"""

from unittest.mock import MagicMock, patch
import pytest

# Import the actual exported function name from agents/synthesis_agent.py
from agents.synthesis_agent import synthesis_agent_sync as run_synthesis_agent


@pytest.fixture
def base_state():
  """Provides a clean base ChrimatosState dictionary for testing."""
  return {
      "ticker": "AAPL",
      "company_name": "Apple Inc.",
      "confidence_score": 1.0,
      "errors": [],
      "financial_data": {
          "data_available": True,
          "debt_to_equity": 1.2,
          "pe_ratio": 28.5,
          "yoy_revenue_growth": 0.08,
          "current_ratio": 1.1,
          "market_cap": 3000000000000,
      },
      "news_data": {
          "news_available": True,
          "sentiment_score": 0.35,
          "key_events": ["Strong iPhone Sales"],
          "red_flags": [],
          "summary": "Positive earnings outlook.",
      },
      "risk_data": {
          "risk_score": 15.0,
          "risk_factors": [],
          "risk_narrative": "Low operational risk.",
      },
  }


# --------------------------------------------------------------------------
# 1. Strict Boundary Condition Tests
# --------------------------------------------------------------------------


def test_boundary_confidence_thresholds(base_state):
  """Confidence < 0.5 triggers 'Flag for Review'; 0.5 does not."""
  base_state["risk_data"]["risk_score"] = 10.0

  with patch("agents.synthesis_agent.genai.Client"):
    # Exactly 0.49 -> Flag for Review
    base_state["confidence_score"] = 0.49
    res_low = run_synthesis_agent(base_state)
    assert (
        res_low["synthesis_report"]["analyst_recommendation"]
        == "Flag for Review"
    )

    # Exactly 0.50 -> Strong Buy Signal (with risk=10.0, growth=0.08)
    base_state["confidence_score"] = 0.50
    res_edge = run_synthesis_agent(base_state)
    assert (
        res_edge["synthesis_report"]["analyst_recommendation"]
        == "Strong Buy Signal"
    )


def test_boundary_risk_score_thresholds(base_state):
  """Tests exact boundaries at 20.0, 45.0, and 70.0."""
  with patch("agents.synthesis_agent.genai.Client"):
    # Exactly 20.0 with growth 0.08 -> Strong Buy Signal
    base_state["risk_data"]["risk_score"] = 20.0
    assert (
        run_synthesis_agent(base_state)["synthesis_report"][
            "analyst_recommendation"
        ]
        == "Strong Buy Signal"
    )

    # Exactly 20.1 -> Cautious Positive
    base_state["risk_data"]["risk_score"] = 20.1
    assert (
        run_synthesis_agent(base_state)["synthesis_report"][
            "analyst_recommendation"
        ]
        == "Cautious Positive"
    )

    # Exactly 45.0 -> Cautious Positive
    base_state["risk_data"]["risk_score"] = 45.0
    assert (
        run_synthesis_agent(base_state)["synthesis_report"][
            "analyst_recommendation"
        ]
        == "Cautious Positive"
    )

    # Exactly 45.1 -> Neutral
    base_state["risk_data"]["risk_score"] = 45.1
    assert (
        run_synthesis_agent(base_state)["synthesis_report"][
            "analyst_recommendation"
        ]
        == "Neutral"
    )

    # Exactly 70.0 -> Neutral
    base_state["risk_data"]["risk_score"] = 70.0
    assert (
        run_synthesis_agent(base_state)["synthesis_report"][
            "analyst_recommendation"
        ]
        == "Neutral"
    )

    # Exactly 70.1 -> Flag for Review
    base_state["risk_data"]["risk_score"] = 70.1
    assert (
        run_synthesis_agent(base_state)["synthesis_report"][
            "analyst_recommendation"
        ]
        == "Flag for Review"
    )


def test_boundary_growth_thresholds(base_state):
  """Growth > 0.05 required for Strong Buy Signal when risk <= 20.0."""
  base_state["risk_data"]["risk_score"] = 15.0

  with patch("agents.synthesis_agent.genai.Client"):
    # Exactly 0.05 -> Falls back to Cautious Positive
    base_state["financial_data"]["yoy_revenue_growth"] = 0.05
    assert (
        run_synthesis_agent(base_state)["synthesis_report"][
            "analyst_recommendation"
        ]
        == "Cautious Positive"
    )

    # Exactly 0.051 -> Strong Buy Signal
    base_state["financial_data"]["yoy_revenue_growth"] = 0.051
    assert (
        run_synthesis_agent(base_state)["synthesis_report"][
            "analyst_recommendation"
        ]
        == "Strong Buy Signal"
    )


# --------------------------------------------------------------------------
# 2. Missing/Negative Financial Data Handling
# --------------------------------------------------------------------------


def test_growth_none_or_negative_prevents_strong_buy(base_state):
  """yoy_revenue_growth = None or negative growth prevents Strong Buy Signal."""
  base_state["risk_data"]["risk_score"] = 15.0

  with patch("agents.synthesis_agent.genai.Client"):
    # None growth -> Cautious Positive
    base_state["financial_data"]["yoy_revenue_growth"] = None
    assert (
        run_synthesis_agent(base_state)["synthesis_report"][
            "analyst_recommendation"
        ]
        == "Cautious Positive"
    )

    # Negative growth -> Cautious Positive
    base_state["financial_data"]["yoy_revenue_growth"] = -0.02
    assert (
        run_synthesis_agent(base_state)["synthesis_report"][
            "analyst_recommendation"
        ]
        == "Cautious Positive"
    )


# --------------------------------------------------------------------------
# 3. State Preservation & Resilience Tests
# --------------------------------------------------------------------------


def test_state_preservation_and_error_accumulation(base_state):
  """Verifies previous errors are preserved and confidence passes through."""
  base_state["errors"] = ["Financial Agent: yfinance fallback used"]

  with patch("agents.synthesis_agent._genai_client") as mock_client:
    mock_client.models.generate_content.side_effect = Exception("LLM Error")

    res = run_synthesis_agent(base_state)

  # Check original error retained, new error appended
  assert "Financial Agent: yfinance fallback used" in res["errors"]
  assert any("Synthesis Agent execution failed" in err for err in res["errors"])
  assert res["confidence_score"] == 1.0


def test_malformed_json_llm_response_fallback(base_state):
  """Malformed JSON from LLM must trigger fallback brief gracefully."""
  mock_genai_response = MagicMock()
  mock_genai_response.text = "NOT_VALID_JSON_STRING"

  with patch("agents.synthesis_agent._genai_client") as mock_client:
    mock_client.models.generate_content.return_value = mock_genai_response

    res = run_synthesis_agent(base_state)

  assert any("Synthesis Agent execution failed" in err for err in res["errors"])
  assert res["synthesis_report"]["analyst_recommendation"] == "Strong Buy Signal"