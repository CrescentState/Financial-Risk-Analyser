import asyncio
import time


class TokenBucketRateLimiter:
    """Token bucket rate limiter for enforcing API rate limits."""
    
    def __init__(self, rate: int = 5, per_seconds: int = 60):
        """
        Initialize token bucket rate limiter.
        
        Args:
            rate: Number of tokens (requests) available per period
            per_seconds: Time period in seconds for token refill
        """
        self.rate = rate
        self.per_seconds = per_seconds
        self._tokens = float(rate)
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire a token, waiting if necessary. Thread-safe and async-safe."""
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = now - self.last_refill
                self.last_refill = now
                # Refill tokens based on elapsed time
                self._tokens = min(self.rate, self._tokens + elapsed * self.rate / self.per_seconds)
                
                if self._tokens >= 1:
                    self._tokens -= 1
                    return
                # Calculate how long to wait for the next token
                wait_time = (1 - self._tokens) * self.per_seconds / self.rate
            
            # Sleep OUTSIDE the lock so other tasks can proceed
            await asyncio.sleep(wait_time)


# Global Alpha Vantage rate limiter: 5 requests per minute
alpha_vantage_limiter = TokenBucketRateLimiter(rate=5, per_seconds=60)
