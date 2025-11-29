"""Queue management package for message queuing with priority support."""

from shinzo.queue.types import CancelResult
from shinzo.queue.manager import QueueManager

__all__ = ["QueueManager", "CancelResult"]

