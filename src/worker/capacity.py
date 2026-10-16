import asyncio
import json
import time
from typing import Any

import redis.asyncio as aioredis

from src.config import settings


class CapacityManager:
    """
    Stage 2 Architecture: Capacity Engine & Starvation-Free Priority Scheduler.
    - Tracks live active worker leases and headroom in Redis.
    - Prevents scheduler over-enqueue under high concurrency.
    - Enforces aging promotion: lower-priority PRs (P2/P3) that wait longer than
      aging_threshold_seconds are automatically promoted to prevent starvation.
    """

    def __init__(
        self,
        redis_client: aioredis.Redis | None = None,
        max_concurrency: int = 10,
        aging_threshold_seconds: float = 180.0,
    ):
        self.redis_client = redis_client
        self.max_concurrency = max_concurrency
        self.aging_threshold_seconds = aging_threshold_seconds

    async def get_redis(self) -> aioredis.Redis:
        if self.redis_client is None:
            self.redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        return self.redis_client

    async def register_worker_heartbeat(self, worker_id: str, ttl_seconds: int = 15) -> None:
        """Registers a worker lease with auto-expiry in Redis."""
        r = await self.get_redis()
        await r.set(f"worker_lease:{worker_id}", int(time.time()), ex=ttl_seconds)

    async def get_active_workers_count(self) -> int:
        """Returns the number of currently active, non-expired worker leases."""
        r = await self.get_redis()
        keys = await r.keys("worker_lease:*")
        return len(keys)

    async def get_headroom(self) -> int:
        """Calculates available capacity headroom."""
        active = await self.get_active_workers_count()
        return max(0, self.max_concurrency - active)

    async def is_at_capacity(self) -> bool:
        """Returns True if cluster is running at maximum worker concurrency."""
        headroom = await self.get_headroom()
        return headroom <= 0

    async def apply_starvation_aging(self) -> list[str]:
        """
        Scans lower-priority queues (P2, P3). If a job has been waiting longer than
        the aging threshold, promotes it to P1 or P0 to guarantee zero starvation.
        """
        r = await self.get_redis()
        now = time.time()
        promoted_job_ids = []

        for queue_key, target_queue in [
            ("pr_queue:P3", "pr_queue:P2"),
            ("pr_queue:P2", "pr_queue:P1"),
        ]:
            length = await r.llen(queue_key)
            if not length:
                continue

            for _ in range(length):
                item_raw = await r.lpop(queue_key)
                if not item_raw:
                    break
                job = json.loads(item_raw)
                enqueued_at = job.get("enqueued_at", now)

                # Promote if age exceeds threshold
                if now - enqueued_at >= self.aging_threshold_seconds:
                    job["promoted"] = True
                    job["priority_tier"] = target_queue.split(":")[-1]
                    await r.rpush(target_queue, json.dumps(job))
                    promoted_job_ids.append(job.get("analysis_id", "unknown"))
                else:
                    # Put back in queue
                    await r.rpush(queue_key, item_raw)

        return promoted_job_ids
