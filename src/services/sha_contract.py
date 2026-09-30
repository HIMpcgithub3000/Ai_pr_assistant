import json
import uuid

import redis.asyncio as aioredis
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.db.models import AnalysisRun


class SHAContract(BaseModel):
    analysis_id: str
    repository_id: str
    pr_number: int
    base_sha: str
    head_sha: str
    priority: str
    created_at: str


class SHAContractService:
    def __init__(self, redis_client: aioredis.Redis | None = None):
        self.redis_client = redis_client

    async def get_redis(self) -> aioredis.Redis:
        if self.redis_client is None:
            self.redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        return self.redis_client

    async def issue_contract(
        self,
        db: AsyncSession,
        repository_id: str,
        pr_number: int,
        base_sha: str,
        head_sha: str,
        priority: str = "P2",
    ) -> AnalysisRun:
        """
        Problem 1 Solution: Issues an immutable SHA contract.
        Records (HEAD_SHA, BASE_SHA) locked to an analysis run UUID.
        Saves both to PostgreSQL and hot-state in Redis.
        """
        analysis_id = str(uuid.uuid4())
        run = AnalysisRun(
            id=analysis_id,
            repository_id=repository_id,
            pr_number=pr_number,
            base_sha=base_sha,
            head_sha=head_sha,
            priority=priority,
            status="QUEUED",
            is_fresh=True,
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)

        # Store in Redis hot state
        r = await self.get_redis()
        redis_key = f"sha_contract:{repository_id}:{pr_number}"
        contract_data = {
            "analysis_id": analysis_id,
            "repository_id": repository_id,
            "pr_number": pr_number,
            "base_sha": base_sha,
            "head_sha": head_sha,
            "priority": priority,
            "created_at": run.created_at.isoformat(),
        }
        await r.set(redis_key, json.dumps(contract_data))
        return run

    async def get_active_contract(
        self, repository_id: str, pr_number: int
    ) -> SHAContract | None:
        r = await self.get_redis()
        redis_key = f"sha_contract:{repository_id}:{pr_number}"
        data = await r.get(redis_key)
        if not data:
            return None
        return SHAContract(**json.loads(data))
