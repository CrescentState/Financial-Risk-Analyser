from google import genai
import httpx
import finnhub
import asyncio
import time
import logging
from core.config import settings

logger = logging.getLogger(__name__)

# Lazy-initialized clients
_gemini_client: genai.Client | None = None
_async_http_client: httpx.AsyncClient | None = None
_finnhub_client: finnhub.Client | None = None


def get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY not configured")
        _gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _gemini_client


def get_async_http_client() -> httpx.AsyncClient:
    global _async_http_client
    if _async_http_client is None:
        _async_http_client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )
    return _async_http_client


def get_finnhub_client() -> finnhub.Client:
    global _finnhub_client
    if _finnhub_client is None:
        if not settings.FINNHUB_API_KEY:
            raise RuntimeError("FINNHUB_API_KEY not configured")
        _finnhub_client = finnhub.Client(api_key=settings.FINNHUB_API_KEY)
    return _finnhub_client


async def close_clients():
    global _async_http_client
    if _async_http_client is not None:
        await _async_http_client.aclose()
        _async_http_client = None

# In-memory rate limit tracking with TTL
_finnhub_rate_limit_cache: dict[str, float] = {}
_finnhub_rate_limit_lock = asyncio.Lock()
FINNHUB_RATE_LIMIT_TTL = 300  # 5 minutes cooldown after rate limit

async def _run_finnhub_sync(func, *args, **kwargs):
    """Run synchronous finnhub call in executor with timeout."""
    try:
        return await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, lambda: func(*args, **kwargs)),
            timeout=30.0
        )
    except asyncio.TimeoutError:
        logger.warning("Finnhub call timed out after 30s")
        return {}
    except Exception as e:
        if "403" in str(e) or "401" in str(e):
            logger.warning(f"Finnhub rate limited or unauthorized: {e}")
            return {}
        raise


async def _check_finnhub_rate_limit(symbol: str) -> bool:
    """Check if Finnhub is rate limited for this symbol."""
    async with _finnhub_rate_limit_lock:
        key = f"rate_limit:{symbol}"
        if key in _finnhub_rate_limit_cache:
            if time.time() - _finnhub_rate_limit_cache[key] < FINNHUB_RATE_LIMIT_TTL:
                return True
    return False


async def _set_finnhub_rate_limit(symbol: str):
    """Mark symbol as rate limited, evicting stale entries."""
    async with _finnhub_rate_limit_lock:
        now = time.time()
        # Evict expired entries so the cache doesn't grow unbounded
        for expired_key in [
            k for k, ts in _finnhub_rate_limit_cache.items()
            if now - ts >= FINNHUB_RATE_LIMIT_TTL
        ]:
            _finnhub_rate_limit_cache.pop(expired_key, None)
        _finnhub_rate_limit_cache[f"rate_limit:{symbol}"] = now


async def _clear_finnhub_rate_limit(symbol: str):
    """Clear rate limit flag on successful call."""
    async with _finnhub_rate_limit_lock:
        key = f"rate_limit:{symbol}"
        _finnhub_rate_limit_cache.pop(key, None)


async def finnhub_company_profile(symbol: str) -> dict:
    """Get company profile from Finnhub."""
    if await _check_finnhub_rate_limit(symbol):
        return {}
    try:
        result = await _run_finnhub_sync(get_finnhub_client().company_profile2, symbol=symbol)
        await _clear_finnhub_rate_limit(symbol)
        return result
    except Exception as e:
        if "403" in str(e) or "401" in str(e):
            await _set_finnhub_rate_limit(symbol)
            return {}
        raise


async def finnhub_company_metrics(symbol: str) -> dict:
    """Get basic financials (ratios, margins, etc.) from Finnhub."""
    if await _check_finnhub_rate_limit(symbol):
        return {}
    try:
        result = await _run_finnhub_sync(get_finnhub_client().company_basic_financials, symbol=symbol, metric="all")
        await _clear_finnhub_rate_limit(symbol)
        return result
    except Exception as e:
        if "403" in str(e) or "401" in str(e):
            await _set_finnhub_rate_limit(symbol)
            return {}
        raise


async def finnhub_quote(symbol: str) -> dict:
    """Get real-time quote from Finnhub."""
    if await _check_finnhub_rate_limit(symbol):
        return {}
    try:
        result = await _run_finnhub_sync(get_finnhub_client().quote, symbol=symbol)
        await _clear_finnhub_rate_limit(symbol)
        return result
    except Exception as e:
        if "403" in str(e) or "401" in str(e):
            await _set_finnhub_rate_limit(symbol)
            return {}
        raise


async def finnhub_symbol_search(query: str) -> dict:
    """Search symbols by company name or keyword (free-tier /search endpoint)."""
    if await _check_finnhub_rate_limit(f"search:{query}"):
        return {}
    try:
        result = await _run_finnhub_sync(get_finnhub_client().symbol_lookup, query)
        await _clear_finnhub_rate_limit(f"search:{query}")
        return result if isinstance(result, dict) else {}
    except Exception as e:
        if "403" in str(e) or "401" in str(e):
            await _set_finnhub_rate_limit(f"search:{query}")
            return {}
        raise


async def finnhub_company_news(symbol: str, _from: str, to: str) -> list:
    """Company news from Finnhub for a date range (ISO YYYY-MM-DD).

    Returns a list of article dicts (headline, summary, url, ...).
    Empty list on rate limiting, auth failure, or empty results;
    other errors propagate to the caller.
    """
    try:
        result = await _run_finnhub_sync(
            get_finnhub_client().company_news, symbol, _from=_from, to=to
        )
        return result if isinstance(result, list) else []
    except Exception as e:
        if "403" in str(e) or "401" in str(e):
            logger.warning(f"Finnhub company-news unavailable for {symbol}: {e}")
            return []
        raise


async def finnhub_financials(symbol: str) -> dict:
    """Get financial statements from Finnhub (requires paid plan)."""
    if await _check_finnhub_rate_limit(symbol):
        return {}
    try:
        result = await _run_finnhub_sync(get_finnhub_client().financials, symbol=symbol, freq="annual")
        await _clear_finnhub_rate_limit(symbol)
        return result
    except Exception as e:
        if "403" in str(e) or "401" in str(e):
            await _set_finnhub_rate_limit(symbol)
            return {}
        raise