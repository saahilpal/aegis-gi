import time
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("aegis_idempotency")

class IdempotencyCache:
    """
    In-memory idempotency cache storing completed operation results.
    Ensures that identical requests with the same Idempotency-Key return
    the same cached result without executing duplicate database mutations.
    """
    def __init__(self, ttl_seconds: int = 3600):
        # key -> {"result": Any, "status_code": int, "created_at": float}
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = ttl_seconds

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        entry = self._cache.get(key)
        if not entry:
            return None
        if time.time() - entry["created_at"] > self.ttl_seconds:
            del self._cache[key]
            return None
        logger.info(f"Idempotency cache HIT for key: {key}")
        return entry

    def set(self, key: str, result: Any, status_code: int = 200):
        self._cache[key] = {
            "result": result,
            "status_code": status_code,
            "created_at": time.time()
        }
        # Evict old entries if cache grows large
        if len(self._cache) > 2000:
            now = time.time()
            cutoff = now - self.ttl_seconds
            for k in list(self._cache.keys()):
                if self._cache[k]["created_at"] < cutoff:
                    del self._cache[k]

idempotency_cache = IdempotencyCache()
