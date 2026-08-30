"""
Tool Executor — Safe tool execution with timeout, error handling, and permission checks.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from jarvis.core.exceptions import ToolExecutionError, ToolNotFoundError, ToolTimeoutError

if TYPE_CHECKING:
    from jarvis.core.config import JarvisConfig
    from jarvis.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

ApprovalCallback = Callable[[str, dict[str, Any]], Awaitable[bool]]


class ToolExecutor:
    """Executes tools safely with timeout, error handling, and permission checks.

    Features:
    - Execution timeout protection
    - Automatic retry on transient failures
    - Approval gate for dangerous tools (fail closed)
    - Schema validation & parameter mismatch diagnostic suggestions
    - Structured error formatting for LLM self-correction
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
        ask_user_callback: Any | None = None,
    ) -> str:
        """Execute a tool by name with the given arguments.

        Args:
            tool_name: The tool name.
            arguments: Tool arguments (dict or JSON string).
            approval_callback: Async callback invoked for dangerous tools.
                Return True to approve, False to deny.
            ask_user_callback: Optional async callback for interactive user prompts.

        Returns:
            Tool execution result as a string.

        Raises:
            ToolExecutionError: If execution fails after retries.
            ToolTimeoutError: If execution exceeds timeout.
        """
        try:
            tool = self.registry.get(tool_name)
        except ToolNotFoundError as e:
            return f"Error: {e}"

        # Parse arguments if string
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {"input": arguments}

        if not isinstance(arguments, dict):
            arguments = {}

        exec_args = dict(arguments)
        if ask_user_callback is not None:
            exec_args["ask_user_callback"] = ask_user_callback

        # Approval gate for dangerous tools
        if tool.schema.dangerous and not self.config.tools.auto_approve:
            approved = False
            if approval_callback is not None:
                try:
                    approved = await approval_callback(tool_name, arguments)
                except Exception as e:
                    logger.warning("Approval callback failed for '%s': %s", tool_name, e)
            else:
                logger.warning(
                    "Tool '%s' is dangerous and no approval callback was provided. Denying by default.",
                    tool_name,
                )

            if not approved:
                logger.warning("Tool '%s' blocked: approval denied.", tool_name)
                return (
                    f"Tool '{tool_name}' was blocked because its execution was not "
                    "approved. Tell the user what you intended to do and ask whether "
                    "they want to allow it."
                )

        # For interactive tools like ask_user, provide a generous timeout (300s)
        execution_timeout = 300.0 if tool_name in ("ask_user", "ask_question") else self.timeout

        # Execute with retries
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                t0 = time.perf_counter()
                result = await asyncio.wait_for(
                    tool.execute(**exec_args),
                    timeout=execution_timeout,
                )
                duration_ms = int((time.perf_counter() - t0) * 1000)
                logger.info(
                    "Tool '%s' executed successfully in %dms (attempt %d)",
                    tool_name,
                    duration_ms,
                    attempt,
                )
                return result

            except TimeoutError:
                raise ToolTimeoutError(
                    f"Tool '{tool_name}' timed out after {self.timeout}s"
                ) from None

            except PermissionError as e:
                return f"Permission Denied executing '{tool_name}': {e}"

            except TypeError as e:
                # Parameter mismatch error — diagnose and return actionable hint
                expected_params = [p.name for p in tool.schema.parameters]
                passed_params = list(arguments.keys())
                logger.warning(
                    "Parameter error for tool '%s': %s (Passed: %s, Expected: %s)",
                    tool_name,
                    e,
                    passed_params,
                    expected_params,
                )
                return (
                    f"Tool Calling Error for '{tool_name}': {e}\n"
                    f"Parameters passed: {passed_params}\n"
                    f"Expected parameters: {expected_params}\n"
                    f"Tool Description: {tool.schema.description}"
                )

            except Exception as e:
                last_error = e
                logger.warning(
                    "Tool '%s' failed (attempt %d/%d): %s",
                    tool_name,
                    attempt,
                    self.max_retries,
                    e,
                )

        raise ToolExecutionError(
            f"Tool '{tool_name}' failed after {self.max_retries} attempts: {last_error}"
        )
