"""Thread processing logic for individual conversation threads."""

import asyncio
from shinzo.queue import QueueManager
from shinzo.agent import AgentProcessor
from shinzo.utils import get_logger


logger = get_logger(__name__)


async def process_thread(
    thread_id: str,
    running_check,
    queue_manager: QueueManager,
    agent_processor: AgentProcessor,
):
    """
    Process messages for a specific thread
    
    Args:
        thread_id: The thread ID to process messages for
        running_check: Callable that returns True if worker is running
        queue_manager: Queue manager instance
        agent_processor: Agent processor instance
    """
    logger.info(f"Thread worker started for: {thread_id}")

    while running_check():
        try:
            # Check if thread has messages
            if queue_manager.has_messages(thread_id):
                # Dequeue next message from this thread
                message = await queue_manager.dequeue(thread_id)

                if message:
                    logger.info(
                        f"Thread worker processing message: thread_id={thread_id}, "
                        f"message_id={message.id}, priority={message.priority}"
                    )

                    # Process the message
                    await agent_processor.process_message(message)

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

