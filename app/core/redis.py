import logging
from typing import Optional
import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)
_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None


async def publish_event(event_type: str, payload: dict) -> None:
    try:
        r = await get_redis()
        import json
        from datetime import datetime, timezone
        envelope = {
            "event_type": event_type,
            "version": "1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "mocktest-auth",
            "payload": payload,
        }
        await r.publish("mocktest:events", json.dumps(envelope))
    except Exception as e:
        logger.warning("Failed to publish event %s: %s", event_type, e)


async def check_rate_limit(key: str, limit: int, window_seconds: int) -> bool:
    try:
        r = await get_redis()
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds)
        results = await pipe.execute()
        count = results[0]
        return count <= limit
    except Exception as e:
        logger.warning("Rate limit check failed: %s", e)
        return True
