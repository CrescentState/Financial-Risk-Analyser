import html
import json
import os
import re
import urllib.parse
import feedparser
import google.genai as genai
from google.genai.client import configure
from core.state import State 
from dotenv import load_dotenv


load_dotenv()
configure(api_key=os.getenv("GEMINI_API_KEY"))


def _clean_html_text(raw_html: str) -> str:
    """Strips HTML tags and unescapes entities from RSS summaries."""
    if not raw_html:
        return ""
    clean_text = re.sub(r"<[^>]+>", " ", raw_html)
    return html.unescape(clean_text).strip()


def _clean_json_response(text: str) -> str:
    """Removes markdown code block wrappers if present."""
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
    if not (-1.0 <= payload["sentiment_score"] <= 1.0):
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


def news_agent(state: State) -> State:
    """Agent 2: Google News RSS parsing & Structured Gemini Sentiment Extractor."""
    if "errors" not in state:
        state["errors"] = []

    news_data = {
        "sentiment_score": None,
        "key_events": [],
        "red_flags": [],
        "news_available": True,
        "summary": None,
    }

    # =====================================================================
    # STAGE 1: QUERY CONSTRUCTION
    # =====================================================================
    company_name = state.get("company_name", "").strip()
    if not company_name:
        company_name = state.get("ticker", "").strip()

    if not company_name:
        state["errors"].append(
            "Agent 2 failed: No company_name or ticker found in state."
        )
        news_data["news_available"] = False
        state["confidence_score"] = max(
            0.0, round(state.get("confidence_score", 1.0) - 0.2, 2)
        )
        state["news_data"] = news_data
        return state

    # FIX 1: Wrap OR conditions in parentheses and quote the company name
    raw_query = f'"{company_name}" (stock OR earnings OR financial) when:7d'
    encoded_query = urllib.parse.quote(raw_query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

    # =====================================================================
    # STAGE 2: FEED RETRIEVAL AND PARSING
    # =====================================================================
    try:
        # FIX 2: Set browser User-Agent so Google RSS doesn't reject feedparser requests
        feed = feedparser.parse(
            rss_url,
            agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        entries = feed.get("entries", [])
    except Exception as e:
        state["errors"].append(f"Network failure accessing RSS Feed: {str(e)}")
        entries = []

    if not entries:
        state["errors"].append(
            f"No news articles found for query: '{raw_query}'."
        )
        news_data["news_available"] = False
        state["confidence_score"] = max(
            0.0, round(state.get("confidence_score", 1.0) - 0.2, 2)
        )
        state["news_data"] = news_data
        return state

    # Extract & clean top 10 articles
    extracted_news = []
    for entry in entries[:10]:
        title = entry.get("title", "No Title")
        raw_summary = entry.get("summary", "")
        # Strip HTML tags out of summary
        clean_summary = _clean_html_text(raw_summary) or "No Summary Available"
        extracted_news.append({"title": title, "summary": clean_summary})

    # =====================================================================
    # STAGE 4: GEMINI STRUCTURED EXTRACTION
    # =====================================================================
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

    model = genai.GenerativeModel("gemini-1.5-flash")
    generation_config = genai.GenerationConfig(
        response_mime_type="application/json", temperature=0.1
    )

    sentiment_payload = None
    validation_passed = False

    # Attempt 1
    try:
        response = model.generate_content(
            base_prompt, generation_config=generation_config
        )
        cleaned_text = _clean_json_response(response.text)
        parsed_json = json.loads(cleaned_text)

        if _validate_sentiment_payload(parsed_json):
            sentiment_payload = parsed_json
            validation_passed = True
    except Exception as e:
        state["errors"].append(f"Gemini sentiment primary attempt failed: {str(e)}")

    # Retry 1
    if not validation_passed:
        retry_prompt = f"""
{base_prompt}

CRITICAL: You must strictly output valid raw JSON without markdown formatting.
- "sentiment_score" MUST be a floating point number between -1.0 and 1.0.
- "key_events" MUST be a flat list of strings.
- "red_flags" MUST be a flat list of strings.
- "summary" MUST be a single string.
"""
        try:
            response_retry = model.generate_content(
                retry_prompt, generation_config=generation_config
            )
            cleaned_text_retry = _clean_json_response(response_retry.text)
            parsed_json_retry = json.loads(cleaned_text_retry)

            if _validate_sentiment_payload(parsed_json_retry):
                sentiment_payload = parsed_json_retry
                validation_passed = True
            else:
                state["errors"].append("Gemini structural validation failed on retry.")
        except Exception as e:
            state["errors"].append(f"Gemini sentiment retry attempt failed: {str(e)}")

    # Fallback assignment
    if not validation_passed:
        state["errors"].append(
            "News sentiment validation failed completely. Degraded state recorded."
        )
        news_data.update(
            {
                "sentiment_score": None,
                "key_events": [],
                "red_flags": [],
                "news_available": True,
                "summary": None,
            }
        )
    else:
        news_data.update(
            {
                "sentiment_score": float(sentiment_payload["sentiment_score"]),
                "key_events": sentiment_payload["key_events"],
                "red_flags": sentiment_payload["red_flags"],
                "news_available": True,
                "summary": sentiment_payload["summary"],
            }
        )

    # =====================================================================
    # STAGE 5: STATE UPDATE
    # =====================================================================
    state["news_data"] = news_data

    score = news_data.get("sentiment_score")
    if score is not None and score < -0.5:
        current_confidence = state.get("confidence_score", 1.0)
        state["confidence_score"] = max(
            0.0, round(current_confidence - 0.1, 2)
        )
        state["errors"].append(
            f"Hostile news environment caught for {company_name} (Score: {score}). Confidence docked."
        )

    return state
