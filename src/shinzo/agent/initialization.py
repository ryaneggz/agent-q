"""Agent initialization logic for creating LangGraph agents."""

from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent

from shinzo.config import settings
from shinzo.tools import get_company_info
from shinzo.utils import get_logger


logger = get_logger(__name__)


def create_agent():
    """
    Initialize and create a LangGraph agent with LLM and tools.

    Returns:
        Initialized LangGraph agent

    Raises:
        Exception: If agent initialization fails
    """
    try:
        # Initialize the LLM
        llm = init_chat_model(
            model=settings.model,
            streaming=True,
        )

        # Create agent with tools
        agent = create_react_agent(
            model=llm,
            tools=[get_company_info],
        )

        logger.info(f"Agent initialized with model: {settings.model}")
        return agent

    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        raise

