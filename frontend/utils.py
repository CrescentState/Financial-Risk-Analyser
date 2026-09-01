import os
import requests
import streamlit as st
from typing import Dict, Any, Optional
import time


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")


def analyze_ticker(ticker: str) -> Optional[Dict[str, Any]]:
    """Call the analyze endpoint and return the full pipeline result."""
    url = f"{API_BASE_URL}/analyze/{ticker.upper()}"
    try:
        with st.spinner(f"Running pipeline for {ticker.upper()}..."):
            response = requests.post(url, timeout=120)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 400:
            st.error(f"Invalid ticker: {response.json().get('detail', 'Unknown error')}")
        elif response.status_code == 500:
            st.error(f"Pipeline error: {response.json().get('detail', 'Unknown error')}")
        else:
            st.error(f"Unexpected error: {response.status_code}")
    except requests.exceptions.Timeout:
        st.error("Request timed out. The pipeline took too long.")
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to API. Is the backend running on port 8000?")
    except Exception as e:
        st.error(f"Error: {str(e)}")
    return None


def check_health() -> bool:
    """Check if the backend is healthy."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def format_number(val: Any, prefix: str = "", suffix: str = "", decimals: int = 2) -> str:
    """Format a number for display."""
    if val is None:
        return "N/A"
    try:
        if isinstance(val, (int, float)):
            if val >= 1e12:
                return f"{prefix}{val/1e12:.{decimals}f}T{suffix}"
            elif val >= 1e9:
                return f"{prefix}{val/1e9:.{decimals}f}B{suffix}"
            elif val >= 1e6:
                return f"{prefix}{val/1e6:.{decimals}f}M{suffix}"
            elif val >= 1e3:
                return f"{prefix}{val/1e3:.{decimals}f}K{suffix}"
            else:
                return f"{prefix}{val:.{decimals}f}{suffix}"
        return str(val)
    except:
        return "N/A"


def format_pct(val: Any, decimals: int = 2) -> str:
    """Format a decimal as percentage."""
    if val is None:
        return "N/A"
    try:
        return f"{val*100:.{decimals}f}%"
    except:
        return "N/A"


RECOMMENDATION_COLORS = {
    "Strong Buy Signal": "#00C851",      # Green
    "Cautious Positive": "#33B5E5",      # Blue
    "Neutral": "#FFBB33",                # Amber
    "Flag for Review": "#FF4444",        # Red
}

RECOMMENDATION_ICONS = {
    "Strong Buy Signal": "🟢",
    "Cautious Positive": "🔵",
    "Neutral": "🟡",
    "Flag for Review": "🔴",
}