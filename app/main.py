import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.queue_manager import QueueManager
from app.agent_processor import AgentProcessor
from app.worker import Worker
from app.api import routes, streaming, threads


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Global instances
queue_manager: QueueManager = None
agent_processor: AgentProcessor = None
worker: Worker = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan events

    This context manager handles startup and shutdown of the worker task
    """
    global queue_manager, agent_processor, worker

    # Startup
    logger.info("Starting Agent Queue System...")

    try:
        # Initialize components
        queue_manager = QueueManager()
        agent_processor = AgentProcessor(queue_manager)
        worker = Worker(queue_manager, agent_processor)

        # Inject queue_manager into routers
        routes.set_queue_manager(queue_manager)
        streaming.set_queue_manager(queue_manager)
        threads.set_queue_manager(queue_manager)

        # Start worker
        await worker.start()

        logger.info("Agent Queue System started successfully")

        yield

    except Exception as e:
        logger.error(f"Failed to start application: {e}", exc_info=True)
        raise

    finally:
        # Shutdown
        logger.info("Shutting down Agent Queue System...")

        if worker:
            await worker.stop()

        logger.info("Agent Queue System shut down")


# Create FastAPI application
app = FastAPI(
    title="Agent Queue System",
    description="AI Agent Queue System with FastAPI and LangGraph",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes.router, tags=["messages"])
app.include_router(threads.router, tags=["threads"])
app.include_router(streaming.router, tags=["streaming"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Agent Queue System",
        "version": "0.1.0",
        "status": "running",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
