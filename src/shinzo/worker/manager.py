"""Main Worker class for managing background processing."""

import asyncio
from typing import Optional, Dict

from shinzo.queue import QueueManager
from shinzo.agent import AgentProcessor
from shinzo.worker.coordinator import run_coordinator
from shinzo.utils import get_logger


logger = get_logger(__name__)


class Worker:
    """Background worker that processes messages from the queue with per-thread concurrency"""

    def __init__(self, queue_manager: QueueManager, agent_processor: AgentProcessor):
        self.queue_manager = queue_manager
        self.agent_processor = agent_processor
        self._running = False
        self._main_task: Optional[asyncio.Task] = None
        self._thread_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def start(self):
        """Start the worker task"""
        if self._running:
            logger.warning("Worker already running")
            return

        self._running = True
        self._main_task = asyncio.create_task(
            run_coordinator(
                lambda: self._running,
                self._lock,
                self._thread_tasks,
                self.queue_manager,
                self.agent_processor
            )
        )
        logger.info("Worker coordinator started")

    async def stop(self):
        """Stop the worker task gracefully"""
        if not self._running:
            return

        logger.info("Stopping worker coordinator...")
        self._running = False

        # Stop all thread workers
        async with self._lock:
            thread_tasks = list(self._thread_tasks.values())
            self._thread_tasks.clear()

        for task in thread_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Stop main coordinator
        if self._main_task:
            try:
                await asyncio.wait_for(self._main_task, timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("Worker coordinator did not stop gracefully, cancelling...")
                self._main_task.cancel()
                try:
                    await self._main_task
                except asyncio.CancelledError:
                    pass

        logger.info("Worker stopped")

