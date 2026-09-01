import asyncio
import calendar
import html
import json
import sys
import re
import time
import urllib.parse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import feedparser
import requests
from google import genai
from google.genai import types

from core.state import SystemState, NewsData
from core.config import settings
from core.clients import gemini_client


def _clean_html_text(raw_html: str) -> str:
    if not raw_html:
        return ""
    clean_text = re.sub(r"<[^>]+>", " ", raw_html)
    clean_text = html.unescape(clean_text)
    return re.sub(r"\s+", " ", clean_text).strip()


def _clean_json_response(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


def _validate_sentiment_payload(payload: dict) -> bool:
    if not isinstance(payload, dict):
        return False

    required_keys = {"sentiment_score", "key_events", "red_flags", "summary"}
    if not required_keys.issubset(payload.keys()):
        return False

    if not isinstance(payload["sentiment_score"], (int, float)):
        return False
    if not (-1.0 <= float(payload["sentiment_score"]) <= 1.0):
        return False
    if not isinstance(payload["key_events"], list) or not all(
        isinstance(x, str) for x in payload["key_events"]
    ):
        return False
    if not isinstance(payload["red_flags"], list) or not all(
        isinstance(x, str) for x in payload["red_flags"]
    ):
        return False
    if not isinstance(payload["summary"], str):
        return False

    return True


async def news_agent_async(state: dict) -> dict:
    """Async News & Sentiment Agent with non-blocking RSS fetch and Gemini call."""
    new_errors = []

    news_data = {
        "sentiment_score": 0.0,
        "key_events": [],
        "red_flags": [],
        "news_available": True,
        "summary": "",
    }

    company_name = state.get("company_name", "").strip()
    if not company_name:
        company_name = state.get("ticker", "").strip()

    if not company_name:
        new_errors.append("Agent 2 failed: No company_name or ticker found in state.")
        news_data["news_available"] = False
        news_data["sentiment_score"] = 0.0
        return {
            **state,
            "news_data": news_data,
            "errors": new_errors,
            "confidence_score": max(0.0, round(state.get("confidence_score", 1.0) - 0.1, 2)),
        }

    # Query: when:30d to match NEWS_LOOKBACK_DAYS
    raw_query = f'"{company_name}" (stock OR earnings OR financial) when:30d'
    encoded_query = urllib.parse.quote(raw_query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

    # Non-blocking RSS fetch via requests.get with timeout=5
    try:
        resp = await asyncio.to_thread(
            requests.get,
            rss_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=5.0
        )
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        entries = feed.get("entries", [])
    except Exception as e:
        new_errors.append(f"Network failure accessing RSS Feed: {str(e)}")
        entries = []

    # UTC-Safe Date Filtering using email.utils.parsedate_to_datetime
    current_time = datetime.now(timezone.utc)
    cutoff_seconds = settings.NEWS_LOOKBACK_DAYS * 86400
    valid_entries = []

    for entry in entries:
        published = entry.get("published") or entry.get("updated")
        if published:
            try:
                dt = parsedate_to_datetime(published)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
                if (current_time - dt).total_seconds() <= cutoff_seconds:
                    valid_entries.append(entry)
            except Exception:
                valid_entries.append(entry)  # Keep if parse fails
        else:
            valid_entries.append(entry)

    if not valid_entries:
        new_errors.append(
            f"No news articles within {settings.NEWS_LOOKBACK_DAYS} days found for: '{raw_query}'."
        )
        news_data["news_available"] = False
        news_data["sentiment_score"] = 0.0  # fallback to 0.0, not None
        return {
            **state,
            "news_data": news_data,
            "errors": new_errors,
            "confidence_score": max(0.0, round(state.get("confidence_score", 1.0) - 0.1, 2)),
        }

    extracted_news = []
    for entry in valid_entries[:settings.MAX_NEWS_ARTICLES]:
        title = entry.get("title", "No Title")
        raw_summary = entry.get("summary", "")
        clean_summary = _clean_html_text(raw_summary) or "No Summary Available"
        extracted_news.append({"title": title, "summary": clean_summary})

    formatted_articles = ""
    for idx, article in enumerate(extracted_news, 1):
        formatted_articles += f"--- ARTICLE {idx} ---\nTitle: {article['title']}\nSummary: {article['summary']}\n\n"

    base_prompt = f"""
You are an expert financial analyst. Analyze the following news articles about {company_name} and perform structured sentiment extraction.

Return ONLY a JSON object containing exactly these four fields:
1. "sentiment_score" (float): Overall sentiment across all articles. Must be between -1.0 (strongly negative) and 1.0 (strongly positive). 0.0 is neutral.
2. "key_events" (list of strings): Significant events mentioned. Each string must be exactly one sentence.
3. "red_flags" (list of strings): Specific concerns, risks, regulatory issues, or negative developments.
4. "summary" (string): A single cohesive paragraph synthesizing the overall news picture.

Articles Data:
{formatted_articles}
"""

    gen_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.1,
    )

    sentiment_payload = None
    validation_passed = False

    # Non-blocking Gemini call via thread pool
    try:
        response = await asyncio.to_thread(
            gemini_client.models.generate_content,
            model=settings.GEMINI_MODEL,
            contents=base_prompt,
            config=gen_config,
        )
        cleaned_text = _clean_json_response(response.text)
        parsed_json = json.loads(cleaned_text)

        if _validate_sentiment_payload(parsed_json):
            sentiment_payload = parsed_json
            validation_passed = True
    except Exception as e:
        new_errors.append(f"Gemini sentiment primary attempt failed: {str(e)}")

    if not validation_passed:
        retry_prompt = f"""
{base_prompt}

CRITICAL: Output raw JSON strictly matching the field requirements:
- "sentiment_score" MUST be a floating point number between -1.0 and 1.0.
- "key_events" MUST be a flat list of strings.
- "red_flags" MUST be a flat list of strings.
- "summary" MUST be a single string.
"""
        try:
            response_retry = await asyncio.to_thread(
                gemini_client.models.generate_content,
                model=settings.GEMINI_MODEL,
                contents=retry_prompt,
                config=gen_config,
            )
            cleaned_text_retry = _clean_json_response(response_retry.text)
            parsed_json_retry = json.loads(cleaned_text_retry)

            if _validate_sentiment_payload(parsed_json_retry):
                sentiment_payload = parsed_json_retry
                validation_passed = True
            else:
                new_errors.append("Gemini structural validation failed on retry.")
        except Exception as e:
            new_errors.append(f"Gemini sentiment retry attempt failed: {str(e)}")

    # Fallback assignment
    if not validation_passed:
        new_errors.append("News sentiment validation failed completely. Degraded state recorded.")
        news_data.update({
            "sentiment_score": 0.0,  # fallback to 0.0, not None
            "key_events": [],
            "red_flags": [],
            "news_available": False,
            "summary": "",
        })
    else:
        news_data.update({
            "sentiment_score": float(sentiment_payload["sentiment_score"]),
            "key_events": sentiment_payload["key_events"],
            "red_flags": sentiment_payload["red_flags"],
            "news_available": True,
            "summary": sentiment_payload["summary"],
        })

    score = news_data.get("sentiment_score")
    new_confidence = state.get("confidence_score", 1.0)
    # Threshold: -0.4 (not -0.5)
    if score is not None and score < settings.HOSTILE_NEWS_THRESHOLD:
        new_confidence = max(0.0, round(new_confidence - 0.1, 2))
        new_errors.append(f"Hostile news environment caught for {company_name} (Score: {score}). Confidence docked.")

    return {
        **state,
        "news_data": news_data,
        "errors": new_errors,
        "confidence_score": new_confidence,
    }


def news_agent_sync(state: dict) -> dict:
    """Synchronous wrapper for LangGraph sync node compatibility.
    
    In test mode, runs directly without thread pool to allow mock patches to work.
    """
    test_mode = getattr(sys.modules.get('agents.news_agent', {}), '_TEST_MODE_OVERRIDE', False)
    
    if test_mode:
        return asyncio.run(news_agent_async(state))
    
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, news_agent_async(state))
        return future.result()