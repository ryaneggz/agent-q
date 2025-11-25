import asyncio
import logging
from typing import Optional, AsyncGenerator
from datetime import datetime

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from app.models import QueuedMessage, MessageState
from app.queue_manager import QueueManager
from app.config import settings


logger = logging.getLogger(__name__)


class AgentProcessor:
    """Processes messages using LangGraph agent"""

    def __init__(self, queue_manager: QueueManager):
        self.queue_manager = queue_manager
        self.agent = None
        self._initialize_agent()

    def _initialize_agent(self):
        """Initialize the LangGraph agent"""
        try:
            # Initialize the LLM
            llm = ChatOpenAI(
                model=settings.model_name,
                api_key=settings.openai_api_key,
                streaming=True,
            )

            # Create agent with basic tools (can be extended)
            # For MVP, we'll create a simple agent without tools
            self.agent = create_react_agent(
                model=llm,
                tools=[],  # Add your tools here as needed
            )

            logger.info(f"Agent initialized with model: {settings.model_name}")

        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            raise

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
            async for chunk in self._stream_agent(message):
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
        try:
            # Prepare input for agent
            inputs = {"messages": [("user", message.user_message)]}

            # Stream agent output
            # Note: LangGraph's streaming may vary based on version
            # This is a simplified implementation
            async for event in self.agent.astream_events(inputs, version="v1"):
                # Extract content from different event types
                if event["event"] == "on_chat_model_stream":
                    content = event["data"].get("chunk", {}).content
                    if content:
                        yield content

        except Exception as e:
            logger.error(f"Agent streaming error: {e}", exc_info=True)
            raise

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
