import asyncio
import signal
import sys

from src.db.session import async_session_factory, init_db
from src.worker.processor import PRAnalysisProcessor
from src.worker.queue import PriorityQueueManager


async def run_worker():
    print("Starting AI PR Assistant Priority Queue Worker...", flush=True)
    await init_db()
    queue = PriorityQueueManager()
    processor = PRAnalysisProcessor()
    running = True

    def _shutdown(signum, frame):
        nonlocal running
        print("Received termination signal. Shutting down worker gracefully...", flush=True)
        running = False

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    print("🚀 Worker is ready and listening for P0, P1, P2, P3 analysis jobs...", flush=True)
    while running:
        job = await queue.dequeue_job()
        if job:
            tier = job.get("priority_tier", "P2")
            analysis_id = job.get("analysis_id", "unknown")
            pr_num = job.get("pr_number")
            repo = job.get("repository_id", "repo")
            print(f"[{tier}] 📥 Received Job {analysis_id} for {repo} PR #{pr_num}", flush=True)
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
