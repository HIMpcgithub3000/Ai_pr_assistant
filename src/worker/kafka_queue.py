import json
import time
from typing import Any

import redis.asyncio as aioredis

from src.config import settings


class MultiTopicQueueAdapter:
    """
    Stage 2 Architecture: Multi-Topic Partitioning Queue.
    Provides strict topic/partition isolation per priority tier:
    - Topic `pr-p0-hotfix`   -> Dedicated partition group (reserved worker pool)
    - Topic `pr-p1-security` -> Security patches
    - Topic `pr-p2-normal`   -> HPA-driven worker pool
    - Topic `pr-p3-low`      -> Low priority / chores
    Guarantees that a surge of P2 PRs can never saturate or block the P0 hotfix partition.
    """

    TOPIC_MAPPING = {
        "P0": "pr-p0-hotfix",
        "P1": "pr-p1-security",
        "P2": "pr-p2-normal",
        "P3": "pr-p3-low",
    }

    def __init__(self, redis_client: aioredis.Redis | None = None):
        self.redis_client = redis_client

    async def get_redis(self) -> aioredis.Redis:
        if self.redis_client is None:
            self.redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        return self.redis_client

    async def publish_event(self, tier: str, payload: dict[str, Any]) -> str:
        """Publishes an analysis payload to its dedicated priority topic."""
        topic = self.TOPIC_MAPPING.get(tier.upper(), "pr-p2-normal")
        r = await self.get_redis()
        payload["topic"] = topic
        payload["enqueued_at"] = time.time()
        await r.rpush(f"topic:{topic}", json.dumps(payload))
        return topic

    async def consume_from_topic(self, topic: str) -> dict[str, Any] | None:
        """Consumes a message from an isolated topic partition."""
        r = await self.get_redis()
        msg_raw = await r.lpop(f"topic:{topic}")
        if msg_raw:
            return json.loads(msg_raw)
        return None

    async def get_topic_depths(self) -> dict[str, int]:
        """Provides per-topic queue depth telemetry for Prometheus and HPA."""
        r = await self.get_redis()
        depths = {}
        for tier, topic in self.TOPIC_MAPPING.items():
            depths[topic] = await r.llen(f"topic:{topic}")
        return depths
