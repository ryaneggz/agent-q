import asyncio
import logging
from typing import Optional

from app.queue_manager import QueueManager
from app.agent_processor import AgentProcessor


logger = logging.getLogger(__name__)


class Worker:
    """Background worker that processes messages from the queue"""

    def __init__(self, queue_manager: QueueManager, agent_processor: AgentProcessor):
        self.queue_manager = queue_manager
        self.agent_processor = agent_processor
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the worker task"""
        if self._running:
            logger.warning("Worker already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("Worker started")

    async def stop(self):
        """Stop the worker task gracefully"""
        if not self._running:
            return

        logger.info("Stopping worker...")
        self._running = False

        if self._task:
            # Wait for current message to finish processing
            try:
                await asyncio.wait_for(self._task, timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("Worker did not stop gracefully, cancelling...")
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass

        logger.info("Worker stopped")

    async def _run(self):
        """Main worker loop"""
        logger.info("Worker loop started")

        while self._running:
            try:
                # Check if there are messages in the queue
                if self.queue_manager.has_messages():
                    # Dequeue next message
                    message = await self.queue_manager.dequeue()

                    if message:
                        logger.info(
                            f"Worker processing message: id={message.id}, "
                            f"priority={message.priority}"
                        )

                        # Process the message
                        await self.agent_processor.process_message(message)

                        logger.info(f"Worker completed message: id={message.id}")
                    else:
                        # Message was None (e.g., cancelled), continue to next
                        continue
                else:
                    # Queue is empty, wait for new messages
                    logger.debug("Worker idle, waiting for messages...")
                    try:
                        # Wait for new messages with timeout to allow checking _running flag
                        await asyncio.wait_for(
                            self.queue_manager.wait_for_messages(),
                            timeout=1.0
                        )
                    except asyncio.TimeoutError:
                        # Timeout is expected, continue loop
                        continue

            except asyncio.CancelledError:
                logger.info("Worker task cancelled")
                break

            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                # Continue processing despite error
                await asyncio.sleep(1.0)

        logger.info("Worker loop ended")
