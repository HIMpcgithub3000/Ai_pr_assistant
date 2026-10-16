import asyncio
import os
import shutil
import pytest
from src.sandbox.pool import SandboxPoolManager
from src.services.salvage_gate import SalvageGateService
from src.agents.circuit_breaker import AgentCircuitBreaker, CircuitState
from src.db.write_queue import AsyncWriteQueue
from src.worker.capacity import CapacityManager
from src.worker.kafka_queue import MultiTopicQueueAdapter
from src.db.models import AnalysisRun, AnalysisFinding
from src.db.session import async_session_factory, init_db


@pytest.mark.asyncio
async def test_sandbox_pool_lifecycle():
    """Validates Stage 2 Pre-Warmed Sandbox Pool initialization, lease, execution, and release."""
    pool_dir = "./sandboxes/test_pool"
    if os.path.exists(pool_dir):
        shutil.rmtree(pool_dir, ignore_errors=True)

    pool = SandboxPoolManager(pool_size=2, base_pool_dir=pool_dir)
    await pool.initialize()

    metrics = await pool.get_pool_metrics()
    assert metrics["total_sandboxes"] == 2
    assert metrics["idle_sandboxes"] == 2
    assert metrics["busy_sandboxes"] == 0

    # Acquire sandbox
    sb = await pool.acquire_sandbox()
    assert sb.is_busy is True
    metrics_after_lease = await pool.get_pool_metrics()
    assert metrics_after_lease["busy_sandboxes"] == 1
    assert metrics_after_lease["idle_sandboxes"] == 1

    # Execute a fast test in the warm sandbox
    target_checkout = "./sandboxes/test_checkout"
    os.makedirs(target_checkout, exist_ok=True)
    with open(os.path.join(target_checkout, "calc.py"), "w") as f:
        f.write("def add(x, y): return x + y\n")

    test_code = "from calc import add\ndef test_add(): assert add(2, 3) == 5\n"
    res = await sb.execute_test(target_dir=target_checkout, test_code=test_code, test_name="test_calc.py")
    assert res["passed"] is True
    assert res["exit_code"] == 0
    assert res["mode"] == "warm_pool_sandbox"

    # Release sandbox
    await pool.release_sandbox(sb)
    assert sb.is_busy is False
    metrics_released = await pool.get_pool_metrics()
    assert metrics_released["busy_sandboxes"] == 0
    assert metrics_released["idle_sandboxes"] == 2

    # Cleanup
    shutil.rmtree(pool_dir, ignore_errors=True)
    shutil.rmtree(target_checkout, ignore_errors=True)


@pytest.mark.asyncio
async def test_salvage_gate_unchanged_file_calculation():
    """Validates Stage 2 Partial Artifact Salvage Gate."""
    await init_db()
    salvage_gate = SalvageGateService()

    all_files = ["src/auth.py", "src/payment.py", "src/user.py"]
    stale_to_new_diff_files = ["src/payment.py"]  # only payment changed in new commit

    unchanged = salvage_gate.identify_salvageable_files(all_files, stale_to_new_diff_files)
    assert "src/auth.py" in unchanged
    assert "src/user.py" in unchanged
    assert "src/payment.py" not in unchanged

    async with async_session_factory() as db_session:
        # Test salvage artifacts persistence
        stale_run = AnalysisRun(
            repository_id="test/repo",
            pr_number=99,
            base_sha="base000",
            head_sha="head001",
            status="STALE",
        )
        new_run = AnalysisRun(
            repository_id="test/repo",
            pr_number=99,
            base_sha="base000",
            head_sha="head002",
            status="RUNNING",
        )
        db_session.add_all([stale_run, new_run])
        await db_session.flush()

        finding = AnalysisFinding(
            analysis_id=stale_run.id,
            file_path="src/auth.py",
            line_number=12,
            symbol_name="verify_token",
            title="Valid finding",
            description="Detected potential token expiration issue",
            category="SECURITY",
            severity="HIGH",
            verified=True,
        )
        db_session.add(finding)
        await db_session.commit()

        report = await salvage_gate.salvage_artifacts(
            db=db_session,
            stale_analysis_id=stale_run.id,
            new_analysis_id=new_run.id,
            salvageable_files=unchanged,
        )

        assert report["salvaged_files_count"] == 2
        assert report["salvaged_findings_count"] == 1
        assert "src/auth.py" in report["salvaged_files"]


@pytest.mark.asyncio
async def test_agent_circuit_breaker():
    """Validates Stage 2 Circuit Breaker tripping and degraded fallback execution."""
    cb = AgentCircuitBreaker(
        name="test_cb",
        failure_threshold=2,
        recovery_timeout_seconds=0.5,
        execution_timeout_seconds=1.0,
    )
    assert cb.state == CircuitState.CLOSED

    async def failing_llm():
        raise RuntimeError("LLM 429 Rate Limit Throttled")

    def static_fallback():
        return {"mode": "degraded_static_analysis", "findings": ["lint_warning"]}

    # First failure -> still CLOSED
    res1 = await cb.call(failing_llm, static_fallback)
    assert res1["mode"] == "degraded_static_analysis"
    assert cb.failure_count == 1
    assert cb.state == CircuitState.CLOSED

    # Second failure -> trips to OPEN
    res2 = await cb.call(failing_llm, static_fallback)
    assert res2["mode"] == "degraded_static_analysis"
    assert cb.state == CircuitState.OPEN
    assert cb.total_trips == 1

    # While OPEN, immediately executes fallback without calling LLM
    res3 = await cb.call(failing_llm, static_fallback)
    assert res3["mode"] == "degraded_static_analysis"

    # Wait for recovery window to allow HALF_OPEN probe
    await asyncio.sleep(0.6)

    async def successful_llm():
        return {"mode": "llm_agent_review", "findings": ["ai_insight"]}

    # HALF_OPEN success resets circuit back to CLOSED
    res4 = await cb.call(successful_llm, static_fallback)
    assert res4["mode"] == "llm_agent_review"
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


@pytest.mark.asyncio
async def test_async_write_queue():
    """Validates Stage 2 Split Write Path Async Write Queue micro-batching."""
    await init_db()
    write_queue = AsyncWriteQueue(batch_size=2, flush_interval_seconds=0.5)

    run1 = AnalysisRun(
        repository_id="test/write_queue_1",
        pr_number=101,
        base_sha="b1",
        head_sha="h1",
        status="RUNNING",
    )
    run2 = AnalysisRun(
        repository_id="test/write_queue_2",
        pr_number=102,
        base_sha="b2",
        head_sha="h2",
        status="RUNNING",
    )

    await write_queue.enqueue(run1)
    assert write_queue.pending_count() == 1

    # Reaching batch_size triggers immediate flush
    await write_queue.enqueue(run2)
    assert write_queue.pending_count() == 0


@pytest.mark.asyncio
async def test_capacity_manager_and_topic_isolation():
    """Validates Stage 2 Capacity Engine headroom tracking, starvation aging, and topic routing."""
    capacity_mgr = CapacityManager(max_concurrency=5, aging_threshold_seconds=0.2)

    # 1. Register worker lease
    await capacity_mgr.register_worker_heartbeat("worker-test-1", ttl_seconds=5)
    active = await capacity_mgr.get_active_workers_count()
    assert active >= 1

    headroom = await capacity_mgr.get_headroom()
    assert headroom <= 4
    assert await capacity_mgr.is_at_capacity() is False

    # 2. Multi-Topic queue routing
    topic_adapter = MultiTopicQueueAdapter()
    t0 = await topic_adapter.publish_event("P0", {"pr_number": 999, "title": "Hotfix"})
    assert t0 == "pr-p0-hotfix"

    msg = await topic_adapter.consume_from_topic("pr-p0-hotfix")
    assert msg is not None
    assert msg["pr_number"] == 999

    depths = await topic_adapter.get_topic_depths()
    assert "pr-p0-hotfix" in depths
    assert "pr-p2-normal" in depths
