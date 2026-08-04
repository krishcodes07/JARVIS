"""
JARVIS Event System — Pub/sub event bus for inter-subsystem communication.

Allows subsystems to communicate without direct coupling.
Example: Memory can listen for "message_sent" events without importing the engine.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

# Type alias for event handlers
EventHandler = Callable[..., Coroutine[Any, Any, None]]


class EventBus:
    """Asynchronous event bus for JARVIS subsystems.

    Supports pub/sub pattern for decoupled communication between
    core engine, memory, tools, MCP, and UI subsystems.

    Usage:
        ```python
        bus = EventBus()

        async def on_message(data):
            print(f"Message received: {data}")

        bus.on("message_sent", on_message)
        await bus.emit("message_sent", {"text": "Hello!"})
        ```
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def on(self, event: str, handler: EventHandler) -> None:
        """Register an event handler.

        Args:
            event: The event name to listen for.
            handler: Async callable to invoke when event fires.
        """
        self._handlers[event].append(handler)
        logger.debug(f"Handler registered for event: {event}")

    def off(self, event: str, handler: EventHandler) -> None:
        """Unregister an event handler.

        Args:
            event: The event name.
            handler: The handler to remove.
        """
        if event in self._handlers:
            self._handlers[event] = [h for h in self._handlers[event] if h != handler]

    async def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Emit an event, calling all registered handlers.

        Args:
            event: The event name.
            *args: Positional arguments passed to handlers.
            **kwargs: Keyword arguments passed to handlers.
        """
        handlers = self._handlers.get(event, [])
        if not handlers:
            return

        logger.debug(f"Emitting event: {event} ({len(handlers)} handlers)")
        tasks = [handler(*args, **kwargs) for handler in handlers]
        await asyncio.gather(*tasks, return_exceptions=True)

    def clear(self) -> None:
        """Remove all event handlers."""
        self._handlers.clear()


# ─── Global event bus instance ────────────────────────────────
event_bus = EventBus()


# ─── Standard event names ─────────────────────────────────────
class Events:
    """Standard event name constants."""

    # Session events
    SESSION_STARTED = "session:started"
    SESSION_ENDED = "session:ended"

    # Message events
    MESSAGE_SENT = "message:sent"
    MESSAGE_RECEIVED = "message:received"
    STREAM_CHUNK = "message:stream_chunk"
    STREAM_END = "message:stream_end"

    # Tool events
    TOOL_CALLED = "tool:called"
    TOOL_RESULT = "tool:result"
    TOOL_ERROR = "tool:error"

    # MCP events
    MCP_SERVER_STARTED = "mcp:server_started"
    MCP_SERVER_STOPPED = "mcp:server_stopped"
    MCP_TOOL_CALLED = "mcp:tool_called"

    # Memory events
    MEMORY_STORED = "memory:stored"
    MEMORY_RETRIEVED = "memory:retrieved"

    # Provider events
    PROVIDER_SWITCHED = "provider:switched"
    PROVIDER_ERROR = "provider:error"

    # Skill events
    SKILL_ACTIVATED = "skill:activated"
    SKILL_DEACTIVATED = "skill:deactivated"
