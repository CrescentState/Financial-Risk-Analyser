import json
import os
import urllib.parse
import feedparser
import google.generativeai as genai
from core.state import State

# Ensure Gemini is configured via environment variables
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def _validate_sentiment_payload(payload: dict) -> bool:
    """
    Validates that the Gemini payload strictly complies with our schema and constraints.
    """
    if not isinstance(payload, dict):
        return False
        
    required_keys = {"sentiment_score", "key_events", "red_flags", "summary"}
    if not required_keys.issubset(payload.keys()):
        return False
        
    # Check types & constraints
    if not isinstance(payload["sentiment_score"], (int, float)):
        return False
    if not (-1.0 <= payload["sentiment_score"] <= 1.0):
        return False
    if not isinstance(payload["key_events"], list) or not all(isinstance(x, str) for x in payload["key_events"]):
        return False
    if not isinstance(payload["red_flags"], list) or not all(isinstance(x, str) for x in payload["red_flags"]):
        return False
    if not isinstance(payload["summary"], str):
        return False
        
    return True


def news_agent(state: State) -> State:
    """
    Agent 2: Google News RSS parsing & Structured Gemini Sentiment Extractor.
    Gathers last 7 days of financial news by company name and scores sentiment.
    """
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
        # Fall back to ticker symbol if company name is completely absent
        company_name = state.get("ticker", "").strip()

    if not company_name:
        state["errors"].append("Agent 2 failed: No company_name or ticker found in state.")
        news_data["news_available"] = False
        state["confidence_score"] = max(0.0, round(state.get("confidence_score", 1.0) - 0.2, 2))
        state["news_data"] = news_data
        return state

    # Construct highly targeted search query matching strict filters
    raw_query = f"{company_name} stock OR earnings OR financial when:7d"
    encoded_query = urllib.parse.quote(raw_query)
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

    # =====================================================================
    # STAGE 2: FEED RETRIEVAL AND PARSING
    # =====================================================================
    try:
        feed = feedparser.parse(rss_url)
        entries = feed.get("entries", [])
    except Exception as e:
        state["errors"].append(f"Network / parsing failure accessing RSS Feed: {str(e)}")
        entries = []

    if not entries:
        state["errors"].append(f"No news articles found for query: '{raw_query}'.")
        news_data["news_available"] = False
        state["confidence_score"] = max(0.0, round(state.get("confidence_score", 1.0) - 0.2, 2))
        state["news_data"] = news_data
        return state

    # Cap raw extraction strictly at the first 10 entries
    extracted_news = []
    for entry in entries[:10]:
        title = entry.get("title", "No Title")
        summary = entry.get("summary", "No Summary Available")
        extracted_news.append({"title": title, "summary": summary})

    # =====================================================================
    # STAGE 3: REDIRECT LINK HANDLING (Abridged)
    # =====================================================================
    # NOTE: We deliberately bypass following 'entry.link' redirects here.
    # The titles and summaries collected in Stage 2 contain all necessary 
    # and sufficient context to run the downstream sentiment extraction.

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

    # We use gemini-1.5-flash as the fast, structurally responsive default
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    # Configure generation parameters to force application/json
    generation_config = genai.GenerationConfig(
        response_mime_type="application/json",
        temperature=0.1
    )

    sentiment_payload = None
    validation_passed = False

    # Attempt 1
    try:
        response = model.generate_content(base_prompt, generation_config=generation_config)
        parsed_json = json.loads(response.text.strip())
        if _validate_sentiment_payload(parsed_json):
            sentiment_payload = parsed_json
            validation_passed = True
    except Exception as e:
        state["errors"].append(f"Gemini primary sentiment extraction parsing failed: {str(e)}")

    # Retry 1 (with Stricter Instructions if Validation Failed)
    if not validation_passed:
        retry_prompt = f"""
{base_prompt}

CRITICAL: Your previous response was invalid. You must strictly output valid JSON.
- "sentiment_score" MUST be a floating point number strictly between -1.0 and 1.0.
- "key_events" MUST be a flat list of strings.
- "red_flags" MUST be a flat list of strings.
- "summary" MUST be a single string.
"""
        try:
            response_retry = model.generate_content(retry_prompt, generation_config=generation_config)
            parsed_json_retry = json.loads(response_retry.text.strip())
            if _validate_sentiment_payload(parsed_json_retry):
                sentiment_payload = parsed_json_retry
                validation_passed = True
            else:
                state["errors"].append("Gemini structural validation failed again on retry.")
        except Exception as e:
            state["errors"].append(f"Gemini secondary sentiment extraction retry failed: {str(e)}")

    # Handle permanent validation failure
    if not validation_passed:
        state["errors"].append("News sentiment payload validation failed completely. Falling back to degraded state.")
        news_data.update({
            "sentiment_score": None,
            "key_events": [],
            "red_flags": [],
            "news_available": True,
            "summary": None
        })
    else:
        # Populate verified values
        news_data.update({
            "sentiment_score": float(sentiment_payload["sentiment_score"]),
            "key_events": sentiment_payload["key_events"],
            "red_flags": sentiment_payload["red_flags"],
            "news_available": True,
            "summary": sentiment_payload["summary"]
        })

    # =====================================================================
    # STAGE 5: STATE UPDATE & ADAPTIVE CONFIDENCE SCORES
    # =====================================================================
    state["news_data"] = news_data
    
    # Assess overall news hospitality
    score = news_data.get("sentiment_score")
    if score is not None and score < -0.5:
        current_confidence = state.get("confidence_score", 1.0)
        state["confidence_score"] = max(0.0, round(current_confidence - 0.1, 2))
        state["errors"].append(f"Hostile news environment caught for {company_name} (Score: {score}). Confidence docked.")

    return state