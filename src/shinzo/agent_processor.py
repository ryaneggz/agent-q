import asyncio
from typing import Optional, AsyncGenerator
from datetime import datetime

from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent

from shinzo.models import QueuedMessage, MessageState
from shinzo.queue_manager import QueueManager
from shinzo.config import settings
from shinzo.tools import get_company_info
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
        try:
            # Initialize the LLM
            llm = init_chat_model(
                model=settings.model,
                streaming=True,
            )

            # Create agent with tools
            self.agent = create_react_agent(
                model=llm,
                tools=[get_company_info],
            )

            logger.info(f"Agent initialized with model: {settings.model}")

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
            # Build conversation history if message is part of a thread
            messages = []

            if message.thread_id:
                # Get all previous messages in the thread (chronologically)
                thread_messages = await self.queue_manager.get_thread_messages(message.thread_id)

                # Add previous messages to conversation history
                for prev_msg in thread_messages:
                    # Skip the current message (it will be added last)
                    if prev_msg.id == message.id:
                        continue

                    # Add user message
                    messages.append(("user", prev_msg.user_message))

                    # Add assistant response if completed
                    if prev_msg.result and prev_msg.state == MessageState.COMPLETED:
                        messages.append(("assistant", prev_msg.result))

            # Add current user message last
            messages.append(("user", message.user_message))

            # Prepare input for agent
            inputs = {"messages": messages}

            logger.info(f"Processing message with {len(messages)} messages in context (thread_id={message.thread_id})")

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
