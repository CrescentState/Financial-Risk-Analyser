import json
import os
import time
from typing import Any, Dict, Optional

try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False  # Windows fallback

CACHE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "cache")
)
TTL_SECONDS = 24 * 60 * 60  # 24 Hours


def _get_cache_path(ticker: str, endpoint: str) -> str:
    """Generates a normalized file path for the cached JSON payload."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    clean_ticker = ticker.strip().upper()
    clean_endpoint = endpoint.strip().upper()
    return os.path.join(CACHE_DIR, f"{clean_ticker}_{clean_endpoint}.json")


def _file_lock(file_obj, exclusive: bool = True):
    """Portable file locking - uses fcntl on Unix, no-op on Windows."""
    if not HAS_FCNTL:
        return
    lock_type = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
    fcntl.flock(file_obj.fileno(), lock_type)


def _file_unlock(file_obj):
    """Release file lock."""
    if not HAS_FCNTL:
        return
    fcntl.flock(file_obj.fileno(), fcntl.LOCK_UN)


def get_cached_response(ticker: str, endpoint: str) -> Optional[Dict[str, Any]]:
    """Retrieves cached response if present and within the 24-hour TTL window.
    
    Uses file locking to prevent TOCTOU race conditions between concurrent readers/writers.
    """
    file_path = _get_cache_path(ticker, endpoint)

    if not os.path.exists(file_path):
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            _file_lock(f, exclusive=False)  # Shared lock for reading
            
            # Re-check existence after acquiring lock (TOCTOU protection)
            if not os.path.exists(file_path):
                return None

            # TTL Expiration Check - done while holding lock to prevent TOCTOU
            file_age = time.time() - os.path.getmtime(file_path)
            if file_age > TTL_SECONDS:
                _file_unlock(f)
                # Use os.unlink which is atomic, and ignore errors if file was already removed
                try:
                    os.unlink(file_path)
                except OSError:
                    pass
                return None

            data = json.load(f)

            # Reject rate limit notifications or API errors saved accidentally
            if (
                "Note" in data
                or "Information" in data
                or "Error Message" in data
                or not data
            ):
                _file_unlock(f)
                try:
                    os.unlink(file_path)
                except OSError:
                    pass
                return None

            _file_unlock(f)
            return data

    except (json.JSONDecodeError, IOError, OSError):
        # File corrupted or deleted mid-read - clean up and return miss
        if os.path.exists(file_path):
            try:
                os.unlink(file_path)
            except OSError:
                pass
        return None


def set_cached_response(ticker: str, endpoint: str, data: Dict[str, Any]) -> None:
    """Writes JSON payload atomically to disk to prevent cache corruption.
    
    Uses exclusive file locking to prevent concurrent write races.
    """
    if (
        not data
        or "Note" in data
        or "Information" in data
        or "Error Message" in data
    ):
        return

    file_path = _get_cache_path(ticker, endpoint)
    temp_path = f"{file_path}.tmp"

    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            _file_lock(f, exclusive=True)  # Exclusive lock for writing
            json.dump(data, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
            _file_unlock(f)
        
        # Atomic replace (POSIX guarantees atomicity for rename within same filesystem)
        os.replace(temp_path, file_path)
    except IOError:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass