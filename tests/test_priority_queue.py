import pytest

from src.worker.queue import PriorityQueueManager


@pytest.mark.asyncio
async def test_priority_scheduling_order():
    queue = PriorityQueueManager()
    redis = await queue.get_redis()
    # Clean test keys
    for _, key in queue.QUEUE_KEYS:
        await redis.delete(key)

    # Enqueue in reverse order: P3, then P2, then P0 hotfix
    await queue.enqueue_job({"id": "job_p3", "pr": 3}, priority="P3")
    await queue.enqueue_job({"id": "job_p2", "pr": 2}, priority="P2")
    await queue.enqueue_job({"id": "job_p0_hotfix", "pr": 1}, priority="P0")

    # Dequeue must return P0 first!
    job1 = await queue.dequeue_job()
    assert job1 is not None
    assert job1["id"] == "job_p0_hotfix"
    assert job1["priority_tier"] == "P0"

    # Then P2
    job2 = await queue.dequeue_job()
    assert job2 is not None
    assert job2["id"] == "job_p2"
    assert job2["priority_tier"] == "P2"

    # Then P3
    job3 = await queue.dequeue_job()
    assert job3 is not None
    assert job3["id"] == "job_p3"
    assert job3["priority_tier"] == "P3"

    # Empty
    assert await queue.dequeue_job() is None
