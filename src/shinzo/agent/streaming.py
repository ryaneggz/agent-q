"""Streaming logic for agent responses."""

from typing import AsyncGenerator

from shinzo.models import QueuedMessage
from shinzo.agent.history import build_conversation_history


async def stream_agent_response(
    agent, message: QueuedMessage, queue_manager
) -> AsyncGenerator[str, None]:
    """
    Stream output from the LangGraph agent.

    Args:
        agent: The LangGraph agent instance
        message: The QueuedMessage to process
        queue_manager: Queue manager for retrieving thread history

    Yields:
        Chunks of the agent response
    """
    try:
        # Build conversation history
        messages = await build_conversation_history(message, queue_manager)

        # Prepare input for agent
        inputs = {"messages": messages}

        # Stream agent output
        # Note: LangGraph's streaming may vary based on version
        # This is a simplified implementation
        async for event in agent.astream_events(inputs, version="v1"):
            # Extract content from different event types
            if event["event"] == "on_chat_model_stream":
                content = event["data"].get("chunk", {}).content
                if content:
                    yield content

    except Exception as e:
        from shinzo.utils import get_logger
        logger = get_logger(__name__)
        logger.error(f"Agent streaming error: {e}", exc_info=True)
        raise

