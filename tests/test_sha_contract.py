import pytest

from src.db.session import async_session_factory, init_db
from src.services.freshness_checker import FreshnessChecker
from src.services.sha_contract import SHAContractService


@pytest.mark.asyncio
async def test_sha_contract_and_freshness():
    await init_db()
    sha_service = SHAContractService()
    freshness_checker = FreshnessChecker(sha_service)

    async with async_session_factory() as db:
        # 1. Issue an immutable contract for PR #101
        run = await sha_service.issue_contract(
            db=db,
            repository_id="org/service-payment",
            pr_number=101,
            base_sha="base_sha_abc123",
            head_sha="head_sha_def456",
            priority="P0",
        )

        assert run.id is not None
        assert run.priority == "P0"
        assert run.status == "QUEUED"
        assert run.head_sha == "head_sha_def456"

        # 2. Verify hot-state contract stored in Redis
        contract = await sha_service.get_active_contract("org/service-payment", 101)
        assert contract is not None
        assert contract.head_sha == "head_sha_def456"

        # 3. Test Freshness Gate when SHA still matches
        is_fresh, _reason = await freshness_checker.verify_run_freshness(
            db=db,
            analysis_id=run.id,
            repository_id="org/service-payment",
            pr_number=101,
            locked_head_sha="head_sha_def456",
            live_head_sha="head_sha_def456",
        )
        assert is_fresh is True

        # 4. Test Freshness Gate when developer pushed new code mid-run
        is_stale, stale_reason = await freshness_checker.verify_run_freshness(
            db=db,
            analysis_id=run.id,
            repository_id="org/service-payment",
            pr_number=101,
            locked_head_sha="head_sha_def456",
            live_head_sha="new_head_sha_789xyz",
        )
        assert is_stale is False
        assert "STALE" in stale_reason
