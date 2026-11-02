import asyncio
import os
import shutil
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.db.models import HumanReviewFeedback, MergeTrainCandidate, SpeculativeMergeResult
from src.db.session import async_session_factory, init_db
from src.services.feedback_buffer import HumanReviewFeedbackBuffer
from src.services.reindex_scheduler import ReindexScheduler
from src.services.speculative_queue import SpeculativeMergeQueue


@pytest.mark.asyncio
async def test_speculative_merge_queue_enqueuing_and_ordering():
    """Validates Stage 3 Speculative Merge Queue candidate ordering and SHA calculation."""
    await init_db()
    queue = SpeculativeMergeQueue()
    repo_id = f"test-owner/repo-{uuid.uuid4().hex[:6]}"

    async with async_session_factory() as db:
        c1 = await queue.enqueue_candidate(db, repo_id, pr_number=101, head_sha="sha_101", target_branch="main")
        c2 = await queue.enqueue_candidate(db, repo_id, pr_number=102, head_sha="sha_102", target_branch="main")
        c3 = await queue.enqueue_candidate(db, repo_id, pr_number=103, head_sha="sha_103", target_branch="main")

        assert c1.queue_position == 0
        assert c2.queue_position == 1
        assert c3.queue_position == 2
        assert c1.status == "ENQUEUED"

        train = await queue.get_merge_train(db, repo_id)
        assert len(train) == 3
        assert [c.pr_number for c in train] == [101, 102, 103]

        # Speculative SHA calculation is deterministic and includes preceding PRs
        spec_sha_1 = queue.compute_speculative_sha("base_main", "sha_101", [])
        spec_sha_2 = queue.compute_speculative_sha("base_main", "sha_102", ["sha_101"])
        spec_sha_3 = queue.compute_speculative_sha("base_main", "sha_103", ["sha_101", "sha_102"])

        assert len(spec_sha_1) == 40
        assert len(spec_sha_2) == 40
        assert spec_sha_1 != spec_sha_2
        assert spec_sha_2 != spec_sha_3


@pytest.mark.asyncio
async def test_speculative_merge_simulation_pass_and_conflict():
    """Validates Stage 3 Sandbox Speculative Verification and Conflict Rejection."""
    await init_db()
    queue = SpeculativeMergeQueue()
    repo_id = f"test-owner/repo-{uuid.uuid4().hex[:6]}"

    async with async_session_factory() as db:
        candidate_pass = await queue.enqueue_candidate(db, repo_id, pr_number=201, head_sha="sha_pass")
        res_pass = await queue.simulate_speculative_merge(
            db=db,
            candidate_id=candidate_pass.id,
            base_target_sha="main_head_sha",
            mock_conflict=False,
        )
        assert res_pass["status"] == "VERIFIED"
        assert res_pass["mergeable"] is True
        assert res_pass["tests_passed"] is True
        assert res_pass["exit_code"] == 0

        # Simulate candidate with merge conflict
        candidate_conflict = await queue.enqueue_candidate(db, repo_id, pr_number=202, head_sha="sha_conflict")
        res_conflict = await queue.simulate_speculative_merge(
            db=db,
            candidate_id=candidate_conflict.id,
            base_target_sha="main_head_sha",
            mock_conflict=True,
        )
        assert res_conflict["status"] == "REJECTED"
        assert res_conflict["mergeable"] is False
        assert res_conflict["tests_passed"] is False
        assert "components/Header.tsx" in res_conflict["conflict_files"]


@pytest.mark.asyncio
async def test_human_review_feedback_buffer_calibration():
    """Validates Closed-Loop Calibration (+0.15 boost, -0.25 penalty, and < 0.50 suppression)."""
    await init_db()
    buffer = HumanReviewFeedbackBuffer()
    repo_id = f"test-owner/repo-{uuid.uuid4().hex[:6]}"

    async with async_session_factory() as db:
        # Record approved finding
        f1 = await buffer.record_feedback(
            db=db,
            repository_id=repo_id,
            pr_number=50,
            reviewer_handle="octocat",
            event_type="approved",
            finding_category="SECURITY",
            rule_or_title="SQL_INJECTION_RISK",
        )
        assert f1.weight_delta == 0.15

        # Record dismissed finding (repeated nagging / false-positive)
        f2 = await buffer.record_feedback(
            db=db,
            repository_id=repo_id,
            pr_number=50,
            reviewer_handle="octocat",
            event_type="dismissed",
            finding_category="LINT",
            rule_or_title="TRAILING_WHITESPACE",
        )
        assert f2.weight_delta == -0.25

        # Check net calibrations
        calib_boost = await buffer.get_historical_calibration(db, repo_id, rule_or_title="SQL_INJECTION_RISK")
        assert calib_boost == 0.15

        calib_penalty = await buffer.get_historical_calibration(db, repo_id, rule_or_title="TRAILING_WHITESPACE")
        assert calib_penalty == -0.25

        # Test findings calibration & suppression
        raw_findings = [
            {
                "file_path": "auth.py",
                "title": "SQL_INJECTION_RISK",
                "category": "SECURITY",
                "confidence": 0.80,
            },
            {
                "file_path": "utils.py",
                "title": "TRAILING_WHITESPACE",
                "category": "LINT",
                "confidence": 0.65,  # 0.65 - 0.25 = 0.40 -> below 0.50 -> MUST BE SUPPRESSED
            },
        ]

        calibrated = await buffer.calibrate_findings(db, repo_id, raw_findings)
        assert len(calibrated) == 1
        assert calibrated[0]["title"] == "SQL_INJECTION_RISK"
        assert calibrated[0]["confidence"] == 0.95
        assert calibrated[0]["calibrated"] is True


@pytest.mark.asyncio
async def test_batched_semantic_reindexing_and_eviction():
    """Validates Stage 3 ReindexScheduler chunk eviction and incremental pgvector re-indexing."""
    await init_db()
    scheduler = ReindexScheduler()
    repo_id = f"test-owner/repo-{uuid.uuid4().hex[:6]}"

    async with async_session_factory() as db:
        # First commit indexes files
        res1 = await scheduler.sync_merged_commit(
            db=db,
            repository_id=repo_id,
            commit_sha="commit_1",
            changed_files=["src/server.py", "src/auth.py"],
        )
        assert res1["status"] == "COMPLETED"
        assert res1["reindexed_chunks"] == 2
        assert res1["evicted_chunks"] == 0

        stats1 = await scheduler.get_repository_index_stats(db, repo_id)
        assert stats1["total_chunks"] == 2
        assert stats1["file_count"] == 2

        # Second commit touches src/server.py -> evicts old chunk and reindexes
        res2 = await scheduler.sync_merged_commit(
            db=db,
            repository_id=repo_id,
            commit_sha="commit_2",
            changed_files=["src/server.py"],
        )
        assert res2["status"] == "COMPLETED"
        assert res2["evicted_chunks"] == 1
        assert res2["reindexed_chunks"] == 1

        stats2 = await scheduler.get_repository_index_stats(db, repo_id)
        assert stats2["total_chunks"] == 2


@pytest.mark.asyncio
async def test_stage3_fastapi_endpoints_integration():
    """Validates Stage 3 REST endpoints and Webhook Ingress (merge_group, review, push)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        repo = f"test-org/repo-{uuid.uuid4().hex[:6]}"

        # 1. Enqueue PR into merge train
        enq_resp = await ac.post("/api/v1/merge-queue/enqueue", json={
            "repository_id": repo,
            "pr_number": 42,
            "head_sha": "head_sha_42",
            "target_branch": "main",
        })
        assert enq_resp.status_code == 200
        candidate = enq_resp.json()
        assert candidate["pr_number"] == 42
        candidate_id = candidate["id"]

        # 2. Get merge train list
        owner, repo_name = repo.split("/")
        train_resp = await ac.get(f"/api/v1/merge-queue/{owner}/{repo_name}")
        assert train_resp.status_code == 200
        train_data = train_resp.json()
        assert train_data["total_queued"] >= 1

        # 3. Simulate speculative merge
        sim_resp = await ac.post("/api/v1/merge-queue/simulate", json={
            "candidate_id": candidate_id,
            "base_target_sha": "main_base_sha",
            "mock_conflict": False,
        })
        assert sim_resp.status_code == 200
        assert sim_resp.json()["status"] == "VERIFIED"

        # 4. Record human feedback
        fb_resp = await ac.post("/api/v1/feedback", json={
            "repository_id": repo,
            "pr_number": 42,
            "reviewer_handle": "lead_dev",
            "event_type": "approved",
            "finding_category": "PERFORMANCE",
            "rule_or_title": "N_PLUS_ONE_QUERY",
            "feedback_text": "Great catch, solved with joinload",
        })
        assert fb_resp.status_code == 200
        assert fb_resp.json()["weight_delta"] == 0.15

        # 5. List feedback entries
        list_fb_resp = await ac.get(f"/api/v1/feedback/{owner}/{repo_name}")
        assert list_fb_resp.status_code == 200
        assert list_fb_resp.json()["count"] >= 1

        # 6. Trigger reindex
        reindex_resp = await ac.post("/api/v1/reindex", json={
            "repository_id": repo,
            "commit_sha": "merged_sha_99",
            "changed_files": ["api/v1/users.py"],
        })
        assert reindex_resp.status_code == 200
        assert reindex_resp.json()["status"] == "COMPLETED"

        # 7. Get reindex stats
        stats_resp = await ac.get(f"/api/v1/reindex/{owner}/{repo_name}")
        assert stats_resp.status_code == 200
        assert stats_resp.json()["file_count"] >= 1

        # 8. Webhook Ingress: merge_group event
        wh_merge_group = await ac.post(
            "/api/v1/webhooks/github",
            headers={"X-GitHub-Event": "merge_group"},
            json={
                "action": "checks_requested",
                "merge_group": {
                    "head_sha": "mg_head_sha",
                    "base_sha": "mg_base_sha",
                    "head_ref": "refs/heads/gh-readonly-queue/main/pr-42-sha",
                },
                "repository": {"full_name": repo},
            },
        )
        assert wh_merge_group.status_code == 200
        assert wh_merge_group.json()["status"] == "speculative_merge_simulated"

        # 9. Webhook Ingress: pull_request_review event
        wh_review = await ac.post(
            "/api/v1/webhooks/github",
            headers={"X-GitHub-Event": "pull_request_review"},
            json={
                "action": "submitted",
                "review": {
                    "state": "approved",
                    "user": {"login": "sr_architect"},
                    "body": "LGTM! Approved.",
                },
                "pull_request": {"number": 42},
                "repository": {"full_name": repo},
            },
        )
        assert wh_review.status_code == 200
        assert wh_review.json()["status"] == "feedback_recorded"

        # 10. Webhook Ingress: push event to default branch
        wh_push = await ac.post(
            "/api/v1/webhooks/github",
            headers={"X-GitHub-Event": "push"},
            json={
                "ref": "refs/heads/main",
                "repository": {"full_name": repo, "default_branch": "main"},
                "after": "push_head_sha_999",
                "head_commit": {
                    "id": "push_head_sha_999",
                    "modified": ["src/app.py"],
                    "added": [],
                },
            },
        )
        assert wh_push.status_code == 200
        assert wh_push.json()["status"] == "reindexed"
