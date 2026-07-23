import os
import json
import time
from typing import Optional, Dict, Any

CACHE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "cache"))
TTL_SECONDS = 24 * 60 * 60  # 24 Hours

def _get_cache_path(ticker: str, endpoint: str) -> str:
    """Generates a clean file path for the cached JSON asset."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    clean_ticker = ticker.strip().upper()
    clean_endpoint = endpoint.strip().upper()
    return os.path.join(CACHE_DIR, f"{clean_ticker}_{clean_endpoint}.json")

def get_cached_response(ticker: str, endpoint: str) -> Optional[Dict[str, Any]]:
    """
    Checks if a non-stale cached file exists on disk.
    Returns the parsed dictionary if valid, otherwise returns None.
    """
    file_path = _get_cache_path(ticker, endpoint)
    
    if not os.path.exists(file_path):
        return None
        
    # Check if the file timestamp is older than 24 hours
    file_age = time.time() - os.path.getmtime(file_path)
    if file_age > TTL_SECONDS:
        return None
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure it's not an error/rate limit block payload saved by accident
            if "Note" in data or "Information" in data or "Error Message" in data:
                return None
            return data
    except (json.JSONDecodeError, IOError):
        return None

def set_cached_response(ticker: str, endpoint: str, data: Dict[str, Any]) -> None:
    """Saves an Alpha Vantage API response payload to disk as a JSON file."""
    if not data or "Note" in data or "Information" in data or "Error Message" in data:
        return  # Refuse to cache rate limits or explicit system failures
        
    file_path = _get_cache_path(ticker, endpoint)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        print(f"⚠️ Cache write error for {ticker}_{endpoint}: {e}")