"""
Tool Executor — Safe tool execution with timeout, error handling, and permission checks.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from jarvis.core.exceptions import ToolExecutionError, ToolTimeoutError

if TYPE_CHECKING:
    from jarvis.core.config import JarvisConfig
    from jarvis.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

ApprovalCallback = Callable[[str, dict[str, Any]], Awaitable[bool]]


class ToolExecutor:
    """Executes tools safely with timeout and error handling.

    Features:
    - Execution timeout protection
    - Automatic retry on failure
    - Approval gate for dangerous tools (fail closed)
    - Result formatting for LLM consumption
    """

    def __init__(self, config: JarvisConfig, registry: ToolRegistry) -> None:
        self.config = config
        self.registry = registry
        self.timeout = config.tools.timeout
        self.max_retries = config.tools.max_retries

    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any] | str,
        approval_callback: ApprovalCallback | None = None,
    ) -> str:
        """Execute a tool by name with the given arguments.

        Args:
            tool_name: The tool name.
            arguments: Tool arguments (dict or JSON string).
            approval_callback: Async callback invoked for dangerous tools.
                Return True to approve, False to deny. When None (and
                ``auto_approve`` is disabled), dangerous tools are denied
                by default (fail closed).

        Returns:
            Tool execution result as a string.

        Raises:
            ToolExecutionError: If execution fails after retries.
            ToolTimeoutError: If execution exceeds timeout.
        """
        tool = self.registry.get(tool_name)

        # Parse arguments if string
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {"input": arguments}

        # Approval gate for dangerous tools
        if tool.schema.dangerous and not self.config.tools.auto_approve:
            approved = False
            if approval_callback is not None:
                try:
                    approved = await approval_callback(tool_name, arguments)
                except Exception as e:
                    logger.warning(f"Approval callback failed for '{tool_name}': {e}")
            else:
                logger.warning(
                    f"Tool '{tool_name}' is dangerous and no approval callback was "
                    "provided. Denying by default."
                )

            if not approved:
                logger.warning(f"Tool '{tool_name}' blocked: approval denied.")
                return (
                    f"Tool '{tool_name}' was blocked because its execution was not "
                    "approved. Tell the user what you intended to do and ask whether "
                    "they want to allow it."
                )

        # Execute with retries
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                result = await asyncio.wait_for(
                    tool.execute(**arguments),
                    timeout=self.timeout,
                )
                logger.info(f"Tool '{tool_name}' executed successfully (attempt {attempt})")
                return result
            except TimeoutError:
                raise ToolTimeoutError(
                    f"Tool '{tool_name}' timed out after {self.timeout}s"
                ) from None
            except PermissionError as e:
                raise ToolExecutionError(str(e)) from None
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Tool '{tool_name}' failed (attempt {attempt}/{self.max_retries}): {e}"
                )

        raise ToolExecutionError(
            f"Tool '{tool_name}' failed after {self.max_retries} attempts: {last_error}"
        )
