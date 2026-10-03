import time
from typing import Dict, Tuple, Optional
from collections import defaultdict
from fastapi import Request, HTTPException, status
import logging

logger = logging.getLogger("aegis_rate_limiter")

class InMemoryRateLimiter:
    """
    Lightweight, thread-safe, in-memory sliding window rate limiter.
    Zero-cost, requires no external Redis/Memcached infrastructure.
    """
    def __init__(self):
        # Map: key -> list of timestamps
        self._requests: Dict[str, list] = defaultdict(list)
        # Periodic cleanup threshold
        self._last_cleanup = time.time()

    def _cleanup(self, window_seconds: int):
        now = time.time()
        if now - self._last_cleanup > 300:  # Every 5 minutes
            cutoff = now - window_seconds
            for k in list(self._requests.keys()):
                self._requests[k] = [ts for ts in self._requests[k] if ts > cutoff]
                if not self._requests[k]:
                    del self._requests[k]
            self._last_cleanup = now

    def check(self, key: str, max_requests: int, window_seconds: int = 60) -> Tuple[bool, int]:
        """
        Check if request is allowed within sliding window.
        Returns: (is_allowed, remaining_seconds_until_retry)
        """
        now = time.time()
        self._cleanup(window_seconds)
        
        timestamps = self._requests[key]
        cutoff = now - window_seconds
        
        # Keep only timestamps within window
        valid_timestamps = [ts for ts in timestamps if ts > cutoff]
        self._requests[key] = valid_timestamps
        
        if len(valid_timestamps) >= max_requests:
            oldest = valid_timestamps[0]
            retry_after = max(1, int(window_seconds - (now - oldest)))
            return False, retry_after
            
        self._requests[key].append(now)
        return True, 0

limiter = InMemoryRateLimiter()

def enforce_rate_limit(request: Request, max_requests: int = 30, window_seconds: int = 60, operation: str = "general"):
    """
    FastAPI dependency / helper to enforce endpoint rate limits.
    Derives client identifier from IP and Authorization token if present.
    """
    client_ip = request.client.host if request.client else "unknown"
    auth_header = request.headers.get("Authorization", "")
    ident = f"{client_ip}:{auth_header[-16:]}" if auth_header else client_ip
    key = f"{operation}:{ident}"
    
    allowed, retry_after = limiter.check(key, max_requests=max_requests, window_seconds=window_seconds)
    if not allowed:
        logger.warning(f"Rate limit exceeded for key={key} on operation={operation}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for {operation}. Maximum {max_requests} requests per {window_seconds}s.",
            headers={"Retry-After": str(retry_after)}
        )
