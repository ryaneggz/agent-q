"""Main AgentProcessor class for processing messages with LangGraph agents."""

import asyncio
from typing import AsyncGenerator

from shinzo.models import QueuedMessage, MessageState
from shinzo.queue import QueueManager
from shinzo.config import settings
from shinzo.agent import initialization, streaming
from shinzo.utils import get_logger


logger = get_logger(__name__)


class AgentProcessor:
    """Processes messages using LangGraph agent"""

    def __init__(self, queue_manager: QueueManager):
        self.queue_manager = queue_manager
        self.agent = None
        self._initialize_agent()

    def _initialize_agent(self):
        """Initialize the LangGraph agent"""
        self.agent = initialization.create_agent()

    async def process_message(self, message: QueuedMessage) -> None:
        """
        Process a message with the LangGraph agent

        Args:
            message: The QueuedMessage to process
        """
        logger.info(f"Starting to process message: id={message.id}")

        try:
            # Update state to processing
            await self.queue_manager.update_state(message.id, MessageState.PROCESSING)

            # Process with timeout
            result = await asyncio.wait_for(
                self._invoke_agent(message),
                timeout=settings.processing_timeout,
            )

            # Store result and mark as completed
            await self.queue_manager.set_result(message.id, result)
            await self.queue_manager.update_state(message.id, MessageState.COMPLETED)

            logger.info(
                f"Message processed successfully: id={message.id}, "
                f"result_length={len(result)}"
            )

        except asyncio.TimeoutError:
            error_msg = f"Processing timeout after {settings.processing_timeout}s"
            logger.error(f"Message processing timeout: id={message.id}")
            await self.queue_manager.update_state(
                message.id, MessageState.FAILED, error=error_msg
            )

        except Exception as e:
            error_msg = f"Agent error: {str(e)}"
            logger.error(f"Message processing error: id={message.id}, error={e}", exc_info=True)
            await self.queue_manager.update_state(
                message.id, MessageState.FAILED, error=error_msg
            )

    async def _invoke_agent(self, message: QueuedMessage) -> str:
        """
        Invoke the LangGraph agent and collect streaming output

        Args:
            message: The QueuedMessage to process

        Returns:
            The complete agent response
        """
        chunks = []

        try:
            # Invoke agent with streaming
            async for chunk in streaming.stream_agent_response(
                self.agent, message, self.queue_manager
            ):
                chunks.append(chunk)
                # Store chunk in message for streaming to clients
                await self.queue_manager.add_chunk(message.id, chunk)

            # Combine all chunks into final result
            result = "".join(chunks)
            return result

        except Exception as e:
            logger.error(f"Agent invocation error: {e}", exc_info=True)
            raise

    async def _stream_agent(self, message: QueuedMessage) -> AsyncGenerator[str, None]:
        """
        Stream output from the LangGraph agent

        Args:
            message: The QueuedMessage to process

        Yields:
            Chunks of the agent response
        """
        async for chunk in streaming.stream_agent_response(
            self.agent, message, self.queue_manager
        ):
            yield chunk

    async def process_message_streaming(
        self, message: QueuedMessage
    ) -> AsyncGenerator[str, None]:
        """
        Process a message and yield streaming chunks in real-time

        This is an alternative method that yields chunks as they're generated,
        useful for direct streaming without storing in queue manager

        Args:
            message: The QueuedMessage to process

        Yields:
            Chunks of the agent response
        """
        logger.info(f"Starting streaming process for message: id={message.id}")

        try:
            # Update state to processing
            await self.queue_manager.update_state(message.id, MessageState.PROCESSING)

            chunks = []

            # Stream agent output
            async for chunk in self._stream_agent(message):
                chunks.append(chunk)
                yield chunk

            # Store complete result
            result = "".join(chunks)
            await self.queue_manager.set_result(message.id, result)
            await self.queue_manager.update_state(message.id, MessageState.COMPLETED)

            logger.info(f"Message streaming completed: id={message.id}")

        except asyncio.TimeoutError:
            error_msg = f"Processing timeout after {settings.processing_timeout}s"
            logger.error(f"Message streaming timeout: id={message.id}")
            await self.queue_manager.update_state(
                message.id, MessageState.FAILED, error=error_msg
            )
            raise

        except Exception as e:
            error_msg = f"Agent error: {str(e)}"
            logger.error(f"Message streaming error: id={message.id}, error={e}", exc_info=True)
            await self.queue_manager.update_state(
                message.id, MessageState.FAILED, error=error_msg
            )
            raise

