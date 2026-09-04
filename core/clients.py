from google import genai
import httpx
import finnhub
import asyncio
import time
import logging
from core.config import settings

logger = logging.getLogger(__name__)

# Global Gemini Client Singleton
gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)

# Global Async HTTP Client Pool
async_http_client = httpx.AsyncClient(
    timeout=30.0,
    limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
)

# Finnhub Client Singleton
_finnhub_client = finnhub.Client(api_key=settings.FINNHUB_API_KEY)

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
            if time.time() - _finnhub_rate_limit_cache[key] < 300:  # 5 min cooldown
                return True
    return False


async def _set_finnhub_rate_limit(symbol: str):
    """Mark symbol as rate limited."""
    async with _finnhub_rate_limit_lock:
        _finnhub_rate_limit_cache[f"rate_limit:{symbol}"] = time.time()


async def finnhub_company_profile(symbol: str) -> dict:
    """Get company profile from Finnhub."""
    try:
        return await _run_finnhub_sync(_finnhub_client.company_profile2, symbol=symbol)
    except Exception as e:
        if "403" in str(e) or "401" in str(e):
            return {}
        raise


async def finnhub_company_metrics(symbol: str) -> dict:
    """Get basic financials (ratios, margins, etc.) from Finnhub."""
    try:
        return await _run_finnhub_sync(_finnhub_client.company_basic_financials, symbol=symbol, metric="all")
    except Exception as e:
        if "403" in str(e) or "401" in str(e):
            return {}
        raise


async def finnhub_quote(symbol: str) -> dict:
    """Get real-time quote from Finnhub."""
    try:
        return await _run_finnhub_sync(_finnhub_client.quote, symbol=symbol)
    except Exception as e:
        if "403" in str(e) or "401" in str(e):
            return {}
        raise


async def finnhub_financials(symbol: str) -> dict:
    """Get financial statements from Finnhub (requires paid plan)."""
    try:
        return await _run_finnhub_sync(_finnhub_client.financials, symbol=symbol, freq="annual")
    except Exception as e:
        if "403" in str(e) or "401" in str(e):
            return {}
        raise