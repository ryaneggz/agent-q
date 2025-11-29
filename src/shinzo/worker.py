import asyncio
from typing import Optional, Dict

from shinzo.queue_manager import QueueManager
from shinzo.agent_processor import AgentProcessor
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
        self._main_task = asyncio.create_task(self._run_coordinator())
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

    async def _run_coordinator(self):
        """Main coordinator loop that spawns workers for each thread"""
        logger.info("Worker coordinator loop started")

        while self._running:
            try:
                # Get all active threads
                active_threads = self.queue_manager.get_active_threads()

                # Start workers for new threads
                async with self._lock:
                    for thread_id in active_threads:
                        if thread_id not in self._thread_tasks:
                            # Start a new worker for this thread
                            task = asyncio.create_task(self._process_thread(thread_id))
                            self._thread_tasks[thread_id] = task
                            logger.info(f"Started worker for thread: {thread_id}")

                    # Clean up completed thread tasks
                    completed_threads = []
                    for thread_id, task in self._thread_tasks.items():
                        if task.done():
                            completed_threads.append(thread_id)
                            try:
                                # Get exception if any
                                task.result()
                            except asyncio.CancelledError:
                                pass
                            except Exception as e:
                                logger.error(
                                    f"Thread worker error for {thread_id}: {e}",
                                    exc_info=True
                                )

                    for thread_id in completed_threads:
                        del self._thread_tasks[thread_id]
                        logger.info(f"Cleaned up worker for thread: {thread_id}")

                # Wait a bit before checking for new threads
                await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                logger.info("Worker coordinator cancelled")
                break

            except Exception as e:
                logger.error(f"Worker coordinator error: {e}", exc_info=True)
                await asyncio.sleep(1.0)

        logger.info("Worker coordinator loop ended")

    async def _process_thread(self, thread_id: str):
        """
        Process messages for a specific thread
        
        Args:
            thread_id: The thread ID to process messages for
        """
        logger.info(f"Thread worker started for: {thread_id}")

        while self._running:
            try:
                # Check if thread has messages
                if self.queue_manager.has_messages(thread_id):
                    # Dequeue next message from this thread
                    message = await self.queue_manager.dequeue(thread_id)

                    if message:
                        logger.info(
                            f"Thread worker processing message: thread_id={thread_id}, "
                            f"message_id={message.id}, priority={message.priority}"
                        )

                        # Process the message
                        await self.agent_processor.process_message(message)

                        logger.info(
                            f"Thread worker completed message: thread_id={thread_id}, "
                            f"message_id={message.id}"
                        )
                    else:
                        # Message was None (e.g., cancelled), continue to next
                        continue
                else:
                    # Thread queue is empty, exit this worker
                    logger.info(f"Thread queue empty, worker exiting for: {thread_id}")
                    break

            except asyncio.CancelledError:
                logger.info(f"Thread worker cancelled for: {thread_id}")
                break

            except Exception as e:
                logger.error(
                    f"Thread worker error for {thread_id}: {e}",
                    exc_info=True
                )
                # Continue processing despite error
                await asyncio.sleep(1.0)

        logger.info(f"Thread worker ended for: {thread_id}")
