"""Type definitions for queue operations."""

from typing import Optional, NamedTuple


class CancelResult(NamedTuple):
    """Result of a cancel operation."""
    success: bool
    error_message: Optional[str] = None

