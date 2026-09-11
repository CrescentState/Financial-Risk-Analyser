"""Company name / keyword to ticker resolution.

Finnhub symbol search is primary (free tier, no quota pressure).
Alpha Vantage SYMBOL_SEARCH is the fallback (costs quota from the
shared 5 req/min bucket, so it is only used when Finnhub is unavailable).
"""
import logging
import os
import sys

from core.cache import get_cached_response, set_cached_response
from core.config import settings

logger = logging.getLogger(__name__)

SEARCH_CACHE_ENDPOINT = "SEARCH"
MIN_QUERY_LENGTH = 2
MAX_CANDIDATES = 8

# Types boosted in ranking (never excluded - ETFs etc. remain searchable)
_EQUITY_TYPES = {"common stock", "equity", "eqs"}

# Known non-US exchange suffixes (Finnhub free tier covers US listings only).
# Bias is toward allowing: unknown suffixes are treated as supported so a
# valid US ticker is never locked out (worst case degrades gracefully).
# NOTE: single-letter class-share suffixes A/B/C (BRK.B) are US; V is left
# out deliberately (Toronto Venture also uses .V, and MKC.V is US).
_NON_US_SUFFIXES = frozenset({
    "T", "L", "MX", "NS", "BO", "PA", "DE", "F", "TO", "AX", "HK",
    "SS", "SZ", "KS", "KQ", "SI", "BK", "JK", "TW", "TWO", "OL", "ST",
    "HE", "CO", "MI", "AS", "BR", "LS", "IR", "VX", "SW", "VI", "PR",
    "ME", "AT", "SA", "BA", "SN", "NX", "QA", "KW", "EG", "MU", "IS",
    "NE", "CN", "KL", "J",
})


def is_free_tier_supported(symbol: str, region: str = "") -> bool:
    """Heuristic for Finnhub free-tier (US listings) coverage.

    Explicit region wins; otherwise the symbol's exchange suffix decides.
    Unknown suffixes default to supported.
    """
    r = (region or "").strip().lower()
    if r:
        return "united states" in r or r in ("us", "usa", "u.s.", "u.s.a.")
    sym = (symbol or "").strip().upper()
    if "." not in sym:
        return True
    return sym.rsplit(".", 1)[-1] not in _NON_US_SUFFIXES


def _is_test_mode() -> bool:
    """Check if test mode is enabled (checks at call time for test overrides)."""
    return getattr(sys.modules.get(__name__, {}), '_TEST_MODE_OVERRIDE', False)


def _is_mock_mode() -> bool:
    """Check if mock mode is enabled via environment variable."""
    return os.getenv("USE_MOCK_DATA", "false").lower() == "true"


def _normalize_finnhub(payload: dict) -> list[dict]:
    """Normalize Finnhub /search payload to [{symbol, name, type, region}]."""
    out = []
    for r in (payload.get("result") or []) if isinstance(payload, dict) else []:
        if not isinstance(r, dict):
            continue
        symbol = (r.get("symbol") or "").strip()
        if not symbol:
            continue
        out.append({
            "symbol": symbol,
            "name": (r.get("description") or "").strip(),
            "type": (r.get("type") or "").strip(),
            "region": "",
        })
    return out


def _normalize_alpha_vantage(payload: dict) -> list[dict]:
    """Normalize AV SYMBOL_SEARCH payload to [{symbol, name, type, region}]."""
    out = []
    matches = payload.get("bestMatches") if isinstance(payload, dict) else None
    for m in matches or []:
        if not isinstance(m, dict):
            continue
        symbol = (m.get("1. symbol") or "").strip()
        if not symbol:
            continue
        out.append({
            "symbol": symbol,
            "name": (m.get("2. name") or "").strip(),
            "type": (m.get("3. type") or "").strip(),
            "region": (m.get("4. region") or "").strip(),
        })
    return out


async def _search_finnhub(query: str) -> list[dict]:
    """Query Finnhub symbol search. Returns [] when unconfigured or failing."""
    if not settings.FINNHUB_API_KEY:
        return []
    try:
        from core.clients import finnhub_symbol_search
        payload = await finnhub_symbol_search(query)
        return _normalize_finnhub(payload)
    except Exception as e:
        logger.warning(f"Finnhub symbol search failed for '{query}': {e}")
        return []


async def _search_alpha_vantage(query: str) -> list[dict]:
    """Query AV SYMBOL_SEARCH (consumes shared rate-limit quota)."""
    api_key = settings.ALPHA_VANTAGE_API_KEY
    if not api_key:
        return []
    try:
        from core.clients import get_async_http_client
        from core.rate_limiter import alpha_vantage_limiter
        await alpha_vantage_limiter.acquire()
        resp = await get_async_http_client().get(
            "https://www.alphavantage.co/query",
            params={"function": "SYMBOL_SEARCH", "keywords": query, "apikey": api_key},
            timeout=10.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"Alpha Vantage symbol search failed for '{query}': {e}")
        return []
    if not isinstance(data, dict) or any(k in data for k in ("Note", "Information", "Error Message")):
        return []
    return _normalize_alpha_vantage(data)


def _score_candidate(candidate: dict, query_upper: str) -> int:
    """Score a candidate for a query. Higher is better."""
    symbol = candidate.get("symbol", "").upper()
    name = candidate.get("name", "").upper()
    if symbol == query_upper:
        score = 100
    elif name == query_upper:
        score = 90
    elif symbol.startswith(query_upper):
        score = 70
    elif name.startswith(query_upper):
        score = 60
    elif query_upper in symbol:
        score = 50
    elif query_upper in name:
        score = 40
    else:
        score = 0
    if candidate.get("type", "").lower() in _EQUITY_TYPES:
        score += 5
    if "united states" in candidate.get("region", "").lower():
        score += 5
    return score


def rank_candidates(candidates: list[dict], query: str) -> list[dict]:
    """Dedupe by symbol and sort best-first (stable for equal scores)."""
    query_upper = query.strip().upper()
    seen: dict[str, dict] = {}
    for c in candidates:
        symbol = (c.get("symbol") or "").strip()
        if not symbol or symbol.upper() in seen:
            continue
        entry = {
            "symbol": symbol,
            "name": c.get("name", ""),
            "type": c.get("type", ""),
            "region": c.get("region", ""),
            "freeTierSupported": is_free_tier_supported(symbol, c.get("region", "")),
        }
        entry["_score"] = _score_candidate(entry, query_upper)
        seen[symbol.upper()] = entry
    # Score first, then shorter names (primary companies tend to have
    # concise names), then symbol for a fully deterministic order.
    ranked = sorted(
        seen.values(),
        key=lambda c: (-c["_score"], len(c.get("name") or ""), c["symbol"]),
    )
    for c in ranked:
        c.pop("_score", None)
    return ranked


def resolve_best(query: str, candidates: list[dict]) -> tuple:
    """Split ranked candidates into (best_or_None, ambiguous_list).

    Auto-resolves on a single candidate or an exact symbol/name match;
    otherwise returns the top candidates for the caller to disambiguate.
    """
    ranked = rank_candidates(candidates, query)
    if not ranked:
        return None, []
    if len(ranked) == 1:
        return ranked[0], []
    query_upper = query.strip().upper()
    top = ranked[0]
    if top["symbol"].upper() == query_upper or top["name"].upper() == query_upper:
        return top, []
    return None, ranked[:MAX_CANDIDATES]


def _is_valid_cached_search(payload) -> bool:
    """SEARCH cache schema check.

    Rejects payloads written before freeTierSupported existed so they are
    refetched instead of served (missing flags would default to supported).
    """
    if not isinstance(payload, dict):
        return False
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        return False
    return all(
        isinstance(c, dict) and "freeTierSupported" in c
        for c in candidates
    )


async def search_companies(query: str) -> list[dict]:
    """Resolve a company name/keyword to ranked ticker candidates."""
    q = (query or "").strip()
    if len(q) < MIN_QUERY_LENGTH:
        return []

    if _is_test_mode() or _is_mock_mode():
        from agents.mock_data import get_mock_search
        return rank_candidates(get_mock_search(q), q)

    cached = get_cached_response(f"SEARCH:{q.upper()}", SEARCH_CACHE_ENDPOINT)
    if _is_valid_cached_search(cached):
        return cached["candidates"]

    candidates = await _search_finnhub(q)
    if not candidates:
        candidates = await _search_alpha_vantage(q)
    ranked = rank_candidates(candidates, q)

    set_cached_response(f"SEARCH:{q.upper()}", SEARCH_CACHE_ENDPOINT, {"candidates": ranked})
    return ranked
