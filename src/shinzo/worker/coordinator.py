"""Coordinator logic for managing thread workers."""

import asyncio
from typing import Dict, Optional

from shinzo.queue import QueueManager
from shinzo.agent import AgentProcessor
from shinzo.worker.thread_worker import process_thread
from shinzo.utils import get_logger


logger = get_logger(__name__)


async def run_coordinator(
    running_check,
    lock: asyncio.Lock,
    thread_tasks: Dict[str, asyncio.Task],
    queue_manager: QueueManager,
    agent_processor: AgentProcessor,
):
    """Main coordinator loop that spawns workers for each thread"""
    logger.info("Worker coordinator loop started")

    while running_check():
        try:
            # Get all active threads
            active_threads = queue_manager.get_active_threads()

            # Start workers for new threads
            async with lock:
                for thread_id in active_threads:
                    if thread_id not in thread_tasks:
                        # Start a new worker for this thread
                        task = asyncio.create_task(
                            process_thread(
                                thread_id, running_check, queue_manager, agent_processor
                            )
                        )
                        thread_tasks[thread_id] = task
                        logger.info(f"Started worker for thread: {thread_id}")

                # Clean up completed thread tasks
                completed_threads = []
                for thread_id, task in thread_tasks.items():
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
                    del thread_tasks[thread_id]
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

