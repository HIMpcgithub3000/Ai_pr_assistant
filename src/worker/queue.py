import json
from typing import Any

import redis.asyncio as aioredis

from src.config import settings


class PriorityQueueManager:
    """
    Problem 2 Solution: Tiered Priority Queue.
    Maintains per-priority queue isolation in Redis:
    P0 (Hotfix) -> P1 (Security) -> P2 (Normal) -> P3 (Low)
    Ensures hotfixes are processed immediately with zero starvation.
    """

    QUEUE_KEYS = [
        ("P0", "pr_queue:P0"),
        ("P1", "pr_queue:P1"),
        ("P2", "pr_queue:P2"),
        ("P3", "pr_queue:P3"),
    ]

    def __init__(self, redis_client: aioredis.Redis | None = None):
        self.redis_client = redis_client

    async def get_redis(self) -> aioredis.Redis:
        if self.redis_client is None:
            self.redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        return self.redis_client

    async def enqueue_job(self, job_data: dict[str, Any], priority: str = "P2") -> None:
        r = await self.get_redis()
        priority_key = f"pr_queue:{priority.upper()}"
        await r.rpush(priority_key, json.dumps(job_data))

    async def dequeue_job(self) -> dict[str, Any] | None:
        """
        Dequeues jobs strictly adhering to priority order (P0 first, then P1, P2, P3).
        """
        r = await self.get_redis()
        for priority, queue_key in self.QUEUE_KEYS:
            job_raw = await r.lpop(queue_key)
            if job_raw:
                job_dict = json.loads(job_raw)
                job_dict["priority_tier"] = priority
                return job_dict
        return None

    async def get_queue_metrics(self) -> dict[str, int]:
        """Returns live queue depths for Prometheus and Autoscaling (HPA)."""
        r = await self.get_redis()
        metrics = {}
        for priority, queue_key in self.QUEUE_KEYS:
            metrics[priority] = await r.llen(queue_key)
        return metrics
