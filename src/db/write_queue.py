import asyncio
from typing import Any

from src.db.session import async_session_factory


class AsyncWriteQueue:
    """
    Stage 2 Architecture: Split Write Path & Async Write Queue.
    Separates the write paths:
    - Hot operational state -> Redis (leases, queues, capacity counters)
    - Durable state -> Buffered through AsyncWriteQueue into PostgreSQL
    Eliminates database lock contention across concurrent worker sandboxes by serializing
    and micro-batching database writes.
    """

    def __init__(self, batch_size: int = 50, flush_interval_seconds: float = 1.0):
        self.batch_size = batch_size
        self.flush_interval_seconds = flush_interval_seconds
        self._queue: asyncio.Queue[Any] = asyncio.Queue()
        self._running = False
        self._flush_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Starts the background batching flush worker."""
        if self._running:
            return
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())

    async def stop(self) -> None:
        """Stops the worker and flushes remaining entities."""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self.flush()

    async def enqueue(self, item: Any) -> None:
        """Enqueues an item (e.g., finding, test evidence, event) for asynchronous persistence."""
        await self._queue.put(item)
        if self._queue.qsize() >= self.batch_size:
            await self.flush()

    async def flush(self) -> int:
        """Flushes all queued items to PostgreSQL in a single database transaction."""
        items: list[Any] = []
        while not self._queue.empty():
            try:
                item = self._queue.get_nowait()
                items.append(item)
            except asyncio.QueueEmpty:
                break

        if not items:
            return 0

        async with async_session_factory() as session:
            for item in items:
                session.add(item)
            await session.commit()

        return len(items)

    async def _flush_loop(self) -> None:
        """Continuous background timer loop flushing at configured intervals."""
        while self._running:
            await asyncio.sleep(self.flush_interval_seconds)
            if not self._queue.empty():
                try:
                    await self.flush()
                except Exception as ex:
                    print(f"[AsyncWriteQueue] Error during batch flush: {ex}")

    def pending_count(self) -> int:
        """Returns the number of buffered writes pending in queue."""
        return self._queue.qsize()
