import asyncio
import signal
import sys

from src.db.session import async_session_factory, init_db
from src.worker.capacity import CapacityManager
from src.worker.processor import PRAnalysisProcessor
from src.worker.queue import PriorityQueueManager


async def run_worker():
    print("Starting AI PR Assistant Priority Queue Worker (Stage 2 Distributed Scaling)...", flush=True)
    await init_db()
    queue = PriorityQueueManager()
    processor = PRAnalysisProcessor()
    capacity_mgr = CapacityManager()
    running = True

    def _shutdown(signum, frame):
        nonlocal running
        print("Received termination signal. Shutting down worker gracefully...", flush=True)
        running = False

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    print("🚀 Worker is ready and listening for P0, P1, P2, P3 analysis jobs...", flush=True)
    tick = 0
    while running:
        tick += 1
        # Register worker lease heartbeat
        await capacity_mgr.register_worker_heartbeat("worker-node-1", ttl_seconds=15)

        # Starvation aging check periodically (every 5 iterations)
        if tick % 5 == 0:
            promoted = await capacity_mgr.apply_starvation_aging()
            if promoted:
                print(f"[CapacityManager] ⚡ Promoted aged jobs to prevent starvation: {promoted}", flush=True)

        job = await queue.dequeue_job()
        if job:
            tier = job.get("priority_tier", "P2")
            analysis_id = job.get("analysis_id", "unknown")
            pr_num = job.get("pr_number")
            repo = job.get("repository_id", "repo")
            headroom = await capacity_mgr.get_headroom()
            print(f"[{tier}] 📥 Received Job {analysis_id} for {repo} PR #{pr_num} (headroom={headroom})", flush=True)
            async with async_session_factory() as db:
                try:
                    result = await processor.process_analysis_run(db, job)
                    status = result.get("status")
                    findings_count = result.get("validated_findings", 0)
                    print(f"[{tier}] ✅ Job {analysis_id} COMPLETED: status={status}, findings={findings_count}", flush=True)
                except Exception as e:
                    print(f"[{tier}] ❌ Job {analysis_id} FAILED: {e}", file=sys.stderr, flush=True)
        else:
            await asyncio.sleep(1.0)


if __name__ == "__main__":
    asyncio.run(run_worker())
