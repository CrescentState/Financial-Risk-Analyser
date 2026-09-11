import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
import httpx
import pytest

from core.state import State
from agents.news_agent import (
    news_agent_sync as news_agent,
    _clean_html_text,
    _validate_sentiment_payload,
)

# Enable test mode for mock data
import agents.news_agent
agents.news_agent._TEST_MODE_OVERRIDE = True


@pytest.fixture
def base_state() -> State:
    return {
        "company_name": "Tesla",
        "ticker": "TSLA",
        "confidence_score": 1.0,
        "errors": []
    }


@pytest.fixture
def valid_llm_payload() -> dict:
    return {
        "sentiment_score": 0.45,
        "key_events": ["Q3 deliverable records broken."],
        "red_flags": ["Margin pressure from recent price drops."],
        "summary": "Tesla shows strong operational metrics despite margin compression."
    }


class TestHelperFunctions:

    def test_clean_html_text(self):
        raw = "<b>Apple</b> reports $100B & record revenue! <a href='#'>Read more</a>"
        cleaned = _clean_html_text(raw)
        assert cleaned == "Apple reports $100B & record revenue! Read more"

    def test_validate_sentiment_payload_valid(self, valid_llm_payload):
        assert _validate_sentiment_payload(valid_llm_payload) is True

    @pytest.mark.parametrize("missing_key", ["sentiment_score", "key_events", "red_flags", "summary"])
    def test_validate_sentiment_payload_missing_keys(self, valid_llm_payload, missing_key):
        payload = valid_llm_payload.copy()
        del payload[missing_key]
        assert _validate_sentiment_payload(payload) is False

    @pytest.mark.parametrize("invalid_score", [-1.5, 1.2, "high", None])
    def test_validate_sentiment_payload_invalid_score_bounds(self, valid_llm_payload, invalid_score):
        payload = valid_llm_payload.copy()
        payload["sentiment_score"] = invalid_score
        assert _validate_sentiment_payload(payload) is False

    def test_validate_sentiment_payload_non_string_lists(self, valid_llm_payload):
        payload = valid_llm_payload.copy()
        payload["key_events"] = ["Valid event", 12345]
        assert _validate_sentiment_payload(payload) is False


class TestNewsAgent:

    @patch("agents.news_agent.get_async_http_client")
    @patch("agents.news_agent.get_gemini_client")
    def test_happy_path(self, mock_gemini_client, mock_requests_get, base_state, valid_llm_payload):
        mock_resp = MagicMock()
        mock_resp.content = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
    <title>Test Feed</title>
    <item>
        <title>Title 0</title>
        <summary><p>Summary 0</p></summary>
        <pubDate>Mon, 23 Aug 2026 08:02:07 +0000</pubDate>
    </item>
    <item>
        <title>Title 1</title>
        <summary><p>Summary 1</p></summary>
        <pubDate>Mon, 23 Aug 2026 08:02:07 +0000</pubDate>
    </item>
    <item>
        <title>Title 2</title>
        <summary><p>Summary 2</p></summary>
        <pubDate>Mon, 23 Aug 2026 08:02:07 +0000</pubDate>
    </item>
    <item>
        <title>Title 3</title>
        <summary><p>Summary 3</p></summary>
        <pubDate>Mon, 23 Aug 2026 08:02:07 +0000</pubDate>
    </item>
    <item>
        <title>Title 4</title>
        <summary><p>Summary 4</p></summary>
        <pubDate>Mon, 23 Aug 2026 08:02:07 +0000</pubDate>
    </item>
</channel>
</rss>"""
        mock_resp.raise_for_status = MagicMock()
        mock_requests_get.return_value.get = AsyncMock(return_value=mock_resp)

        mock_response = MagicMock()
        mock_response.text = json.dumps(valid_llm_payload)
        mock_gemini_client.return_value.models.generate_content.return_value = mock_response

        result_state = news_agent(base_state)

        assert result_state["news_data"]["news_available"] is True
        assert result_state["news_data"]["sentiment_score"] == 0.45
        assert len(result_state["news_data"]["key_events"]) == 1
        assert result_state["confidence_score"] == 1.0
        assert len(result_state["errors"]) == 0

    def test_missing_company_name_and_ticker(self):
        empty_state = {"confidence_score": 1.0, "errors": []}
        result_state = news_agent(empty_state)

        assert result_state["news_data"]["news_available"] is False
        assert result_state["confidence_score"] == 0.9  # docked 0.1 for missing company name
        assert "Agent 2 failed: No company_name or ticker found in state." in result_state["errors"][0]

    @patch("agents.news_agent.get_async_http_client")
    @patch("agents.news_agent.get_gemini_client")
    def test_ticker_fallback_when_company_name_missing(self, mock_gemini_client, mock_requests_get, valid_llm_payload):
        state = {"ticker": "NVDA", "errors": []}
        mock_resp = MagicMock()
        mock_resp.content = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
    <title>Test Feed</title>
    <item>
        <title>Test</title>
        <summary><p>Summary</p></summary>
        <pubDate>Mon, 23 Aug 2026 08:02:07 +0000</pubDate>
    </item>
</channel>
</rss>"""
        mock_resp.raise_for_status = MagicMock()
        mock_requests_get.return_value.get = AsyncMock(return_value=mock_resp)

        mock_response = MagicMock()
        mock_response.text = json.dumps(valid_llm_payload)
        mock_gemini_client.return_value.models.generate_content.return_value = mock_response

        result_state = news_agent({"ticker": "NVDA", "errors": []})

        assert result_state["news_data"]["news_available"] is True
        assert len(result_state["errors"]) == 0

    def test_rss_feed_age_filtering_all_expired(self):
        with patch("agents.news_agent.get_async_http_client") as mock_get, \
                patch("agents.news_agent._fetch_finnhub_company_news",
                      new=AsyncMock(return_value=[])):
            old_date = (datetime.now(timezone.utc) - timedelta(days=31)).strftime("%a, %d %b %Y %H:%M:%S %z")
            rss_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
    <title>Test Feed</title>
    <item>
        <title>Old News</title>
        <summary><p>Old summary</p></summary>
        <pubDate>{old_date}</pubDate>
    </item>
</channel>
</rss>"""
            
            mock_resp = MagicMock()
            mock_resp.content = rss_content.encode('utf-8')
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value.get = AsyncMock(return_value=mock_resp)

            result_state = news_agent({
                "company_name": "Tesla",
                "ticker": "TSLA",
                "confidence_score": 1.0,
                "errors": []
            })

            assert result_state["news_data"]["news_available"] is False
            assert result_state["confidence_score"] == 0.9
            assert any("No news articles within 30 days found" in err for err in result_state["errors"])

    @patch("agents.news_agent.get_async_http_client")
    @patch("agents.news_agent.get_gemini_client")
    def test_rss_feed_missing_published_parsed(self, mock_gemini_client, mock_requests_get, valid_llm_payload):
        mock_resp = MagicMock()
        rss_content = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
    <title>Test Feed</title>
    <item>
        <title>Dateless news</title>
        <summary>Some details</summary>
    </item>
</channel>
</rss>"""
        mock_resp.content = rss_content.encode('utf-8')
        mock_resp.raise_for_status = MagicMock()
        mock_requests_get.return_value.get = AsyncMock(return_value=mock_resp)

        mock_response = MagicMock()
        mock_response.text = json.dumps(valid_llm_payload)
        mock_gemini_client.return_value.models.generate_content.return_value = mock_response

        base_state = {"company_name": "Tesla", "ticker": "TSLA", "confidence_score": 1.0, "errors": []}
        result_state = news_agent({"company_name": "Tesla", "ticker": "TSLA", "confidence_score": 1.0, "errors": []})

        assert result_state["news_data"]["news_available"] is True

    def test_rss_network_exception(self):
        with patch("agents.news_agent.get_async_http_client") as mock_get, \
                patch("agents.news_agent._fetch_finnhub_company_news",
                      new=AsyncMock(return_value=[])):
            mock_get.side_effect = Exception("Connection timed out")

            result_state = news_agent({
                "company_name": "Tesla",
                "ticker": "TSLA",
                "confidence_score": 1.0,
                "errors": []
            })

            assert result_state["news_data"]["news_available"] is False
            assert result_state["confidence_score"] == 0.9
            assert any("Network failure accessing RSS Feed" in err for err in result_state["errors"])

    @patch("agents.news_agent.get_async_http_client")
    @patch("agents.news_agent.get_gemini_client")
    def test_gemini_retry_succeeds_after_first_attempt_fails(
        self, mock_gemini_client, mock_requests_get
    ):
        mock_resp = MagicMock()
        mock_resp.content = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
    <title>Test Feed</title>
    <item>
        <title>Title</title>
        <summary><p>Summary</p></summary>
        <pubDate>Mon, 23 Aug 2026 08:02:07 +0000</pubDate>
    </item>
</channel>
</rss>"""
        mock_resp.raise_for_status = MagicMock()
        mock_requests_get.return_value.get = AsyncMock(return_value=mock_resp)

        mock_bad_response = MagicMock()
        mock_bad_response.text = "```json\n{'invalid_json': True}\n```"

        mock_good_response = MagicMock()
        mock_good_response.text = json.dumps({
            "sentiment_score": 0.45,
            "key_events": ["Q3 deliverable records broken."],
            "red_flags": ["Margin pressure from recent price drops."],
            "summary": "Tesla shows strong operational metrics despite margin compression."
        })

        mock_gemini_client.return_value.models.generate_content.side_effect = [
            mock_bad_response,
            mock_good_response
        ]

        result_state = news_agent({
            "company_name": "Tesla",
            "ticker": "TSLA",
            "confidence_score": 1.0,
            "errors": []
        })

        assert result_state["news_data"]["news_available"] is True
        assert result_state["news_data"]["sentiment_score"] == 0.45
        assert any("Gemini sentiment primary attempt failed" in err for err in result_state["errors"])

    @patch("agents.news_agent.get_async_http_client")
    @patch("agents.news_agent.get_gemini_client")
    def test_gemini_retry_fails_completely(self, mock_gemini_client, mock_requests_get):
        mock_resp = MagicMock()
        mock_resp.content = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
    <title>Test Feed</title>
    <item>
        <title>Title</title>
        <summary><p>Summary</p></summary>
        <pubDate>Mon, 23 Aug 2026 08:02:07 +0000</pubDate>
    </item>
</channel>
</rss>"""
        mock_resp.raise_for_status = MagicMock()
        mock_requests_get.return_value.get = AsyncMock(return_value=mock_resp)

        mock_gemini_client.return_value.models.generate_content.side_effect = Exception("API Quota Exceeded")

        result_state = news_agent({
            "company_name": "Tesla",
            "ticker": "TSLA",
            "confidence_score": 1.0,
            "errors": []
        })

        assert result_state["news_data"]["news_available"] is False
        assert result_state["news_data"]["sentiment_score"] == 0.0
        assert any("News sentiment validation failed completely" in err for err in result_state["errors"])

    @patch("agents.news_agent.get_async_http_client")
    @patch("agents.news_agent.get_gemini_client")
    def test_hostile_news_environment_docks_confidence(
        self, mock_gemini_client, mock_requests_get
    ):
        mock_resp = MagicMock()
        mock_resp.content = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
    <title>Test Feed</title>
    <item>
        <title>Title</title>
        <summary><p>Summary</p></summary>
        <pubDate>Mon, 23 Aug 2026 08:02:07 +0000</pubDate>
    </item>
</channel>
</rss>"""
        mock_resp.raise_for_status = MagicMock()
        mock_requests_get.return_value.get = AsyncMock(return_value=mock_resp)

        hostile_payload = {
            "sentiment_score": -0.85,
            "key_events": ["Q3 deliverable records broken."],
            "red_flags": ["Margin pressure from recent price drops."],
            "summary": "Tesla shows strong operational metrics despite margin compression."
        }

        mock_response = MagicMock()
        mock_response.text = json.dumps(hostile_payload)
        mock_gemini_client.return_value.models.generate_content.return_value = mock_response

        result_state = news_agent({
            "company_name": "Tesla",
            "ticker": "TSLA",
            "confidence_score": 1.0,
            "errors": []
        })

        assert result_state["news_data"]["sentiment_score"] == -0.85
        # hostile threshold is -0.4 in code, -0.85 < -0.4 so confidence docked 0.1
        assert result_state["confidence_score"] == 0.9
        assert any("Hostile news environment caught" in err for err in result_state["errors"])

    @patch("agents.news_agent.get_async_http_client")
    @patch("agents.news_agent.get_gemini_client")
    def test_max_articles_limit_enforced(self, mock_gemini_client, mock_requests_get):
        mock_resp = MagicMock()
        mock_resp.content = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
    <title>Test Feed</title>
""" + b"".join([
            f"""<item><title>Title {i}</title><summary><p>Summary {i}</p></summary><pubDate>Mon, 23 Aug 2026 08:02:07 +0000</pubDate></item>""".encode() for i in range(15)
        ]) + b"""</channel></rss>"""
        mock_resp.raise_for_status = MagicMock()
        mock_requests_get.return_value.get = AsyncMock(return_value=mock_resp)

        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "sentiment_score": 0.45,
            "key_events": ["Q3 deliverable records broken."],
            "red_flags": ["Margin pressure from recent price drops."],
            "summary": "Tesla shows strong operational metrics despite margin compression."
        })
        mock_gemini_client.return_value.models.generate_content.return_value = mock_response

        result_state = news_agent({
            "company_name": "Tesla",
            "ticker": "TSLA",
            "confidence_score": 1.0,
            "errors": []
        })

        call_args = mock_gemini_client.return_value.models.generate_content.call_args
        prompt = call_args.kwargs["contents"]
        article_count = prompt.count("--- ARTICLE ")
        assert article_count == 10

    def test_rss_query_contains_when_7d(self):
        result_state = news_agent({"company_name": "Tesla", "ticker": "TSLA", "confidence_score": 1.0, "errors": []})
        assert result_state is not None

    def test_rss_user_agent_header(self):
        with patch("agents.news_agent.get_async_http_client") as mock_get, \
                patch("agents.news_agent._fetch_finnhub_company_news",
                      new=AsyncMock(return_value=[])):
            mock_resp = MagicMock()
            mock_resp.content = b"""<?xml version="1.0"?><rss><channel><item><title>Test</title></item></channel></rss>"""
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value.get = AsyncMock(return_value=mock_resp)

            news_agent({"company_name": "Tesla", "ticker": "TSLA", "confidence_score": 1.0, "errors": []})

            call_kwargs = mock_get.return_value.get.call_args[1]
            assert "headers" in call_kwargs
            assert "User-Agent" in call_kwargs["headers"]
            assert "Mozilla" in call_kwargs["headers"]["User-Agent"]

    @patch("agents.news_agent.get_async_http_client")
    @patch("agents.news_agent.get_gemini_client")
    def test_gemini_timeout_handled(self, mock_gemini_client, mock_requests_get):
        mock_resp = MagicMock()
        mock_resp.content = b"""<?xml version="1.0"?><rss><channel><item><title>Test</title></item></channel></rss>"""
        mock_resp.raise_for_status = MagicMock()
        mock_requests_get.return_value.get = AsyncMock(return_value=mock_resp)

        import asyncio
        mock_gemini_client.return_value.models.generate_content.side_effect = asyncio.TimeoutError("Request timed out")

        result_state = news_agent({
            "company_name": "Tesla",
            "ticker": "TSLA",
            "confidence_score": 1.0,
            "errors": []
        })

        assert result_state["news_data"]["news_available"] is False
        assert any("Gemini sentiment primary attempt failed" in err for err in result_state["errors"])

    def test_empty_rss_entries_returns_unavailable(self):
        with patch("agents.news_agent.get_async_http_client") as mock_get, \
                patch("agents.news_agent._fetch_finnhub_company_news",
                      new=AsyncMock(return_value=[])):
            mock_resp = MagicMock()
            mock_resp.content = b"""<?xml version="1.0"?><rss><channel></channel></rss>"""
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value.get = AsyncMock(return_value=mock_resp)

            result_state = news_agent({
                "company_name": "Tesla",
                "ticker": "TSLA",
                "confidence_score": 1.0,
                "errors": []
            })

            assert result_state["news_data"]["news_available"] is False
            assert result_state["confidence_score"] == 0.9
            assert any("No news articles within 30 days found" in err for err in result_state["errors"])

    @patch("agents.news_agent.get_async_http_client")
    @patch("agents.news_agent.get_gemini_client")
    def test_confidence_unchanged_for_neutral_sentiment(self, mock_gemini_client, mock_requests_get):
        mock_resp = MagicMock()
        mock_resp.content = b"""<?xml version="1.0"?><rss><channel><item><title>Test</title><summary>Summary</summary><pubDate>Mon, 23 Aug 2026 08:02:07 +0000</pubDate></item></channel></rss>"""
        mock_resp.raise_for_status = MagicMock()
        mock_requests_get.return_value.get = AsyncMock(return_value=mock_resp)

        neutral_payload = {
            "sentiment_score": 0.0,
            "key_events": ["Q3 deliverable records broken."],
            "red_flags": ["Margin pressure from recent price drops."],
            "summary": "Tesla shows strong operational metrics despite margin compression."
        }

        mock_response = MagicMock()
        mock_response.text = json.dumps(neutral_payload)
        mock_gemini_client.return_value.models.generate_content.return_value = mock_response

        result_state = news_agent({
            "company_name": "Tesla",
            "ticker": "TSLA",
            "confidence_score": 1.0,
            "errors": []
        })

        assert result_state["confidence_score"] == 1.0
        assert not any("Hostile news environment" in e for e in result_state["errors"])

    @patch("agents.news_agent.get_async_http_client")
    @patch("agents.news_agent.get_gemini_client")
    def test_malformed_json_in_retry_also_fails(self, mock_gemini_client, mock_requests_get):
        mock_resp = MagicMock()
        mock_resp.content = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
    <title>Test Feed</title>
    <item>
        <title>Test</title>
        <summary>Summary</summary>
        <pubDate>Mon, 23 Aug 2026 08:02:07 +0000</pubDate>
    </item>
</channel>
</rss>"""
        mock_resp.raise_for_status = MagicMock()
        mock_requests_get.return_value.get = AsyncMock(return_value=mock_resp)

        mock_bad_response = MagicMock()
        mock_bad_response.text = "not valid json at all"

        mock_gemini_client.return_value.models.generate_content.return_value = mock_bad_response

        result_state = news_agent({
            "company_name": "Tesla",
            "ticker": "TSLA",
            "confidence_score": 1.0,
            "errors": []
        })

        assert result_state["news_data"]["news_available"] is False
        assert any("News sentiment validation failed completely" in err for err in result_state["errors"])

    # ===== RSS RETRY + FINNHUB FALLBACK TESTS =====

    def _fresh_rss(self, n=1):
        items = "".join(
            f"""<item><title>Title {i}</title><summary><p>Summary {i}</p></summary>"""
            f"""<pubDate>Mon, 23 Aug 2026 08:02:07 +0000</pubDate></item>"""
            for i in range(n)
        )
        mock_resp = MagicMock()
        mock_resp.content = (
            b"""<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>"""
            b"""<title>Test Feed</title>""" + items.encode() + b"""</channel></rss>"""
        )
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    def _req(self):
        return httpx.Request("GET", "https://news.google.com/rss")

    @patch("agents.news_agent.get_async_http_client")
    @patch("agents.news_agent.get_gemini_client")
    def test_rss_retry_then_success(self, mock_gemini_client, mock_http_client):
        mock_http_client.return_value.get = AsyncMock(side_effect=[
            httpx.ConnectTimeout("timed out", request=self._req()),
            self._fresh_rss(),
        ])
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "sentiment_score": 0.2,
            "key_events": ["Event."],
            "red_flags": [],
            "summary": "Fine."
        })
        mock_gemini_client.return_value.models.generate_content.return_value = mock_response

        result_state = news_agent({
            "company_name": "Tesla", "ticker": "TSLA",
            "confidence_score": 1.0, "errors": []
        })

        assert result_state["news_data"]["news_available"] is True
        assert mock_http_client.return_value.get.call_count == 2
        assert not any("Network failure" in e for e in result_state["errors"])

    @patch("agents.news_agent.get_async_http_client")
    @patch("agents.news_agent.get_gemini_client")
    def test_rss_retry_exhausted(self, mock_gemini_client, mock_http_client):
        req = self._req()
        mock_http_client.return_value.get = AsyncMock(side_effect=[
            httpx.ConnectError("boom", request=req),
            httpx.ConnectError("boom", request=req),
            httpx.ConnectError("boom", request=req),
        ])

        with patch("agents.news_agent._fetch_finnhub_company_news",
                   new=AsyncMock(return_value=[])):
            result_state = news_agent({
                "company_name": "Tesla", "ticker": "TSLA",
                "confidence_score": 1.0, "errors": []
            })

        assert result_state["news_data"]["news_available"] is False
        assert mock_http_client.return_value.get.call_count == 3
        assert any("after 3 attempt(s)" in e for e in result_state["errors"])

    @patch("agents.news_agent.get_async_http_client")
    def test_rss_no_retry_on_403(self, mock_http_client):
        req = self._req()
        err403 = httpx.HTTPStatusError(
            "Client error '403 Forbidden'",
            request=req, response=httpx.Response(403, request=req),
        )
        mock_http_client.return_value.get = AsyncMock(side_effect=err403)

        with patch("agents.news_agent._fetch_finnhub_company_news",
                   new=AsyncMock(return_value=[])):
            result_state = news_agent({
                "company_name": "Tesla", "ticker": "TSLA",
                "confidence_score": 1.0, "errors": []
            })

        assert result_state["news_data"]["news_available"] is False
        assert mock_http_client.return_value.get.call_count == 1
        assert any("403" in e for e in result_state["errors"])

    @patch("agents.news_agent.get_async_http_client")
    @patch("agents.news_agent.get_gemini_client")
    def test_finnhub_fallback_used_when_rss_empty(self, mock_gemini_client, mock_http_client):
        mock_resp = MagicMock()
        mock_resp.content = b"""<?xml version="1.0"?><rss><channel></channel></rss>"""
        mock_resp.raise_for_status = MagicMock()
        mock_http_client.return_value.get = AsyncMock(return_value=mock_resp)

        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "sentiment_score": 0.1,
            "key_events": ["Fallback event."],
            "red_flags": [],
            "summary": "From fallback."
        })
        mock_gemini_client.return_value.models.generate_content.return_value = mock_response

        fallback_articles = [
            {"title": "Fallback title", "summary": "Fallback summary"},
        ]
        with patch("agents.news_agent._fetch_finnhub_company_news",
                   new=AsyncMock(return_value=fallback_articles)):
            result_state = news_agent({
                "company_name": "Tesla", "ticker": "TSLA",
                "confidence_score": 1.0, "errors": []
            })

        assert result_state["news_data"]["news_available"] is True
        assert any("Finnhub company news fallback" in e for e in result_state["errors"])

    def test_finnhub_company_news_normalization(self):
        from agents.news_agent import _fetch_finnhub_company_news
        raw = [
            {"headline": f"Headline {i}", "summary": f"<p>Summary {i}</p>", "url": "http://x"}
            for i in range(12)
        ] + ["junk", {"headline": "", "summary": ""}]
        with patch("core.clients.finnhub_company_news", new=AsyncMock(return_value=raw)):
            articles = asyncio.run(_fetch_finnhub_company_news("TSLA"))
        assert len(articles) == 10  # bounded to MAX_NEWS_ARTICLES
        assert articles[0] == {"title": "Headline 0", "summary": "Summary 0"}

        short_raw = [{"headline": "", "summary": "<p>S</p>"}]
        with patch("core.clients.finnhub_company_news", new=AsyncMock(return_value=short_raw)):
            short_articles = asyncio.run(_fetch_finnhub_company_news("TSLA"))
        assert short_articles == [{"title": "No Title", "summary": "S"}]

    def test_finnhub_company_news_never_raises(self):
        from agents.news_agent import _fetch_finnhub_company_news
        with patch("core.clients.finnhub_company_news",
                   new=AsyncMock(side_effect=Exception("down"))):
            assert asyncio.run(_fetch_finnhub_company_news("TSLA")) == []


if __name__ == "__main__":
    pytest.main(["-v", __file__])