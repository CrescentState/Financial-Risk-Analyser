from google import genai
import httpx
from core.config import settings

# Global Gemini Client Singleton
gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)

# Global Async HTTP Client Pool
async_http_client = httpx.AsyncClient(
    timeout=30.0,
    limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
)