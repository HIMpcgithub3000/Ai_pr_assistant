
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import AnalysisRun
from src.services.sha_contract import SHAContractService


class FreshnessChecker:
    """
    Problem 1 Solution: Freshness Check Gate.
    Verifies that the PR's live HEAD SHA matches the locked contract SHA before publishing findings.
    If the developer pushed new commits during analysis, marks the run STALE,
    preventing misleading comments on outdated code.
    """

    def __init__(self, sha_service: SHAContractService | None = None):
        self.sha_service = sha_service or SHAContractService()

    async def verify_run_freshness(
        self,
        db: AsyncSession,
        analysis_id: str,
        repository_id: str,
        pr_number: int,
        locked_head_sha: str,
        live_head_sha: str,
    ) -> tuple[bool, str]:
        """
        Compares live PR HEAD SHA with locked analysis HEAD SHA.
        Returns: (is_fresh: bool, status_reason: str)
        """
        if live_head_sha == locked_head_sha:
            return True, "Analysis SHA matches current live PR HEAD SHA. Analysis is FRESH."

        # Developer pushed new code while analysis was running!
        # Mark run as STALE in database
        stmt = (
            update(AnalysisRun)
            .where(AnalysisRun.id == analysis_id)
            .values(status="STALE", is_fresh=False)
        )
        await db.execute(stmt)
        await db.commit()

        return False, f"STALE RUN: PR HEAD advanced from {locked_head_sha[:7]} to {live_head_sha[:7]}. Analysis discarded."
