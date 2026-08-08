"""
JARVIS Core Engine — The central orchestrator.

This is the brain of JARVIS. It coordinates all subsystems:
- Provider management (LLM backends)
- Memory (conversation, long-term, vector)
- Tools (built-in tool execution)
- MCP (Model Context Protocol servers)
- UI (user interface abstraction)
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import json
import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from jarvis.prompts.persona import get_persona
from jarvis.prompts.system import SystemPromptBuilder
from jarvis.providers.base import GenerationConfig, Message, ToolDefinition

if TYPE_CHECKING:
    from jarvis.core.config import JarvisConfig
    from jarvis.core.session import Session
    from jarvis.mcp.manager import MCPManager
    from jarvis.memory.manager import MemoryManager
    from jarvis.providers.manager import ProviderManager
    from jarvis.tools.executor import ToolExecutor
    from jarvis.tools.registry import ToolRegistry
    from jarvis.voice.manager import VoiceManager

logger = logging.getLogger(__name__)


class JarvisEngine:
    """Main JARVIS engine — orchestrates all subsystems.

    The engine is the central coordination point. It:
    1. Loads configuration
    2. Initializes all subsystems
    3. Manages the conversation loop & tool execution loop
    4. Routes tool calls and MCP requests
    5. Handles graceful shutdown

    Usage:
        ```python
        engine = JarvisEngine()
        await engine.initialize()
        response = await engine.chat("Hello, JARVIS!")
        await engine.shutdown()
        ```
    """

    def __init__(self) -> None:
        self.config: JarvisConfig | None = None
        self.provider_manager: ProviderManager | None = None
        self.memory_manager: MemoryManager | None = None
        self.tool_registry: ToolRegistry | None = None
        self.tool_executor: ToolExecutor | None = None
        self.mcp_manager: MCPManager | None = None
        self.voice_manager: VoiceManager | None = None
        self.prompt_builder: SystemPromptBuilder = SystemPromptBuilder()
        self.session: Session | None = None
        self._initialized: bool = False
        self._background_tasks: set[Any] = set()

    async def initialize(self, config: JarvisConfig | None = None) -> None:
        """Initialize all subsystems.

        Loads config (or uses the provided one), sets up providers, memory,
        tools, MCP, and voice. Must be called before any other operations.

        Args:
            config: Pre-loaded configuration to use. If ``None``, the default
                ``config/jarvis.yaml`` is loaded.
        """
        logger.info("Initializing JARVIS engine...")

        # 1. Load configuration
        if config is None:
            from jarvis.core.config import JarvisConfig
            config = JarvisConfig.load()
        self.config = config

        # 2. Initialize subsystems
        await self._init_providers(config)
        await self._init_memory(config)
        await self._init_tools(config)
        await self._init_mcp(config)
        await self._init_voice(config)

        # 3. Create session
        from jarvis.core.session import Session
        self.session = Session(engine=self)

        self._initialized = True
        logger.info("JARVIS engine initialized successfully.")

    async def chat(self, message: str, **kwargs: Any) -> str:
        """Send a message to JARVIS and get a response.

        Args:
            message: The user's message.
            **kwargs: Additional parameters (e.g. callback for tool execution
                ``on_tool_call``, or async ``approval_callback`` for dangerous tools).

        Returns:
            JARVIS's response text.

        Raises:
            RuntimeError: If the engine is not initialized.
        """
        if not self._initialized or not self.config or not self.session:
            raise RuntimeError("Engine not initialized. Call initialize() first.")

        session_id = self.session.session_id

        # 2. Gather tool definitions & capability summary
        tool_defs, capability_summary = await self._get_tool_definitions(query=message)
        all_raw_defs = await self._get_all_raw_tool_definitions()

        # 3. Build system prompt & context
        persona = get_persona(self.config.jarvis.persona)

        memory_ctx = ""
        if self.memory_manager:
            raw_mem = await self.memory_manager.get_context(session_id, query=message)
            memory_ctx = self._format_memory_context(raw_mem)

        system_prompt = self.prompt_builder.build(
            persona=persona,
            memory_context=memory_ctx,
            capability_summary=capability_summary,
        )

        # 4. Save user message to memory
        if self.memory_manager:
            await self.memory_manager.add_message(session_id, "user", message)

        # 5. Assemble messages pipeline
        messages: list[Message] = [Message(role="system", content=system_prompt)]

        # Fetch conversation history from memory store
        if self.memory_manager and self.memory_manager.conversation:
            history = await self.memory_manager.conversation.retrieve(session_id)
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant"):
                    messages.append(Message(role=role, content=content))

        # 6. Tool execution & generation loop
        max_turns = self.config.tools.max_turns if (self.config and self.config.tools) else 25
        current_turn = 0
        on_tool_call = kwargs.get("on_tool_call")
        approval_callback = kwargs.get("approval_callback")

        while current_turn < max_turns:
            gen_config = GenerationConfig(
                model=self.config.provider.model,
                temperature=self.config.provider.temperature,
                max_tokens=self.config.provider.max_tokens,
                top_p=self.config.provider.top_p,
                tools=tool_defs if tool_defs else None,
            )

            if not self.provider_manager:
                raise RuntimeError("Provider manager not available.")

            response = await self.provider_manager.generate(messages, gen_config)

            # If no tool calls requested, we have the final assistant answer
            if not response.tool_calls:
                final_answer = response.content
                if self.memory_manager:
                    await self.memory_manager.add_message(session_id, "assistant", final_answer)
                self._schedule_memory_extraction(session_id, message, final_answer)
                return final_answer

            # Add assistant message with tool calls to conversation trace
            messages.append(
                Message(
                    role="assistant",
                    content=response.content,
                    tool_calls=response.tool_calls,
                )
            )

            # Execute tool calls
            for tool_call in response.tool_calls:
                tool_name, tool_args, tool_call_id = self._parse_tool_call(tool_call)

                if callable(on_tool_call):
                    with contextlib.suppress(Exception):
                        res = on_tool_call(tool_name, tool_args)
                        if inspect.isawaitable(res):
                            await res

                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                result = await self._execute_tool(
                    tool_name,
                    tool_args,
                    approval_callback=approval_callback,
                )
                self._update_tool_defs_from_schema_call(tool_defs, tool_name, tool_args, all_raw_defs)

                # Record tool call and result in conversation memory
                args_str = ", ".join(f"{k}={v!r}" for k, v in tool_args.items())
                if self.memory_manager:
                    await self.memory_manager.add_message(
                        session_id,
                        "tool",
                        result,
                        tool_name=tool_name,
                        args_str=args_str,
                    )

                # Append tool result to conversation trace
                messages.append(
                    Message(
                        role="tool",
                        content=result,
                        tool_call_id=tool_call_id,
                        name=tool_name,
                    )
                )

            current_turn += 1

        return "Reached maximum tool execution turns limit."

    async def stream_chat(self, message: str, **kwargs: Any) -> AsyncIterator[str]:
        """Stream a response from JARVIS.

        Runs the full agent loop while streaming text as it arrives.
        Tool calls are accumulated across chunks (OpenAI delta format),
        executed, and the loop continues until a final text answer.

        Args:
            message: The user's message.
            **kwargs: Additional parameters (``on_tool_call``, ``on_tool_result``
                sync callbacks, or async ``approval_callback`` for dangerous tools).

        Yields:
            Response chunks as strings.
        """
        if not self._initialized or not self.config or not self.session:
            raise RuntimeError("Engine not initialized. Call initialize() first.")

        session_id = self.session.session_id

        tool_defs, capability_summary = await self._get_tool_definitions(query=message)
        all_raw_defs = await self._get_all_raw_tool_definitions()

        persona = get_persona(self.config.jarvis.persona)

        memory_ctx = ""
        if self.memory_manager:
            raw_mem = await self.memory_manager.get_context(session_id, query=message)
            memory_ctx = self._format_memory_context(raw_mem)

        system_prompt = self.prompt_builder.build(
            persona=persona,
            memory_context=memory_ctx,
            capability_summary=capability_summary,
        )

        messages: list[Message] = [Message(role="system", content=system_prompt)]
        if self.memory_manager and self.memory_manager.conversation:
            history = await self.memory_manager.conversation.retrieve(session_id)
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant"):
                    messages.append(Message(role=role, content=content))

        messages.append(Message(role="user", content=message))

        if self.memory_manager:
            await self.memory_manager.add_message(session_id, "user", message)

        on_tool_call = kwargs.get("on_tool_call")
        on_tool_result = kwargs.get("on_tool_result")
        approval_callback = kwargs.get("approval_callback")

        if not self.provider_manager:
            raise RuntimeError("Provider manager unavailable.")

        accumulated_assistant_chunks: list[str] = []
        max_turns = self.config.tools.max_turns if (self.config and self.config.tools) else 25
        saved_assistant_msg = False

        try:
            for _ in range(max_turns):
                gen_config = GenerationConfig(
                    model=self.config.provider.model,
                    temperature=self.config.provider.temperature,
                    max_tokens=self.config.provider.max_tokens,
                    top_p=self.config.provider.top_p,
                    tools=tool_defs if tool_defs else None,
                )

                content_parts: list[str] = []
                tool_calls_box: dict[str, Any] = {}

                async for chunk_text in self._stream_turn(
                    messages, gen_config, content_parts, tool_calls_box
                ):
                    accumulated_assistant_chunks.append(chunk_text)
                    yield chunk_text

                tool_calls = tool_calls_box.get("calls", [])

                if not tool_calls:
                    final_text = "".join(content_parts)
                    if self.memory_manager:
                        await self.memory_manager.add_message(session_id, "assistant", final_text)
                        saved_assistant_msg = True
                    self._schedule_memory_extraction(session_id, message, final_text)
                    return

                # Assistant turn requested tools — append trace & execute
                messages.append(
                    Message(
                        role="assistant",
                        content="".join(content_parts),
                        tool_calls=tool_calls,
                    )
                )

                for tool_call in tool_calls:
                    tool_name, tool_args, tool_call_id = self._parse_tool_call(tool_call)

                    if callable(on_tool_call):
                        with contextlib.suppress(Exception):
                            res = on_tool_call(tool_name, tool_args)
                            if inspect.isawaitable(res):
                                await res

                    logger.info(f"[stream] Executing tool: {tool_name} with args: {tool_args}")
                    result = await self._execute_tool(
                        tool_name,
                        tool_args,
                        approval_callback=approval_callback,
                    )
                    self._update_tool_defs_from_schema_call(tool_defs, tool_name, tool_args, all_raw_defs)

                    if callable(on_tool_result):
                        with contextlib.suppress(Exception):
                            on_tool_result(tool_name, result)

                    # Record tool call and result in conversation memory
                    args_str = ", ".join(f"{k}={v!r}" for k, v in tool_args.items())
                    if self.memory_manager:
                        await self.memory_manager.add_message(
                            session_id,
                            "tool",
                            result,
                            tool_name=tool_name,
                            args_str=args_str,
                        )

                    messages.append(
                        Message(
                            role="tool",
                            content=result,
                            tool_call_id=tool_call_id,
                            name=tool_name,
                        )
                    )
        except (Exception, asyncio.CancelledError, BaseException) as err:
            if not saved_assistant_msg:
                partial_text = "".join(accumulated_assistant_chunks).strip()
                if partial_text and self.memory_manager:
                    with contextlib.suppress(Exception):
                        await self.memory_manager.add_message(session_id, "assistant", partial_text)
                        saved_assistant_msg = True
            raise err

        yield "Reached maximum tool execution turns limit."

    async def shutdown(self) -> None:
        """Gracefully shut down all subsystems."""
        logger.info("Shutting down JARVIS engine...")

        if self.mcp_manager:
            await self.mcp_manager.shutdown()
        if self.memory_manager:
            await self.memory_manager.flush()
        if self.voice_manager:
            await self.voice_manager.shutdown()

        self._initialized = False
        logger.info("JARVIS engine shut down.")

    # ─── Private initialization & helper methods ───────────────

    async def _init_providers(self, config: JarvisConfig) -> None:
        """Initialize the LLM provider manager."""
        from jarvis.providers.manager import ProviderManager
        self.provider_manager = ProviderManager(config)
        await self.provider_manager.initialize()
        logger.info("Provider manager initialized.")

    async def _init_memory(self, config: JarvisConfig) -> None:
        """Initialize the memory subsystem."""
        from jarvis.memory.manager import MemoryManager
        self.memory_manager = MemoryManager(config)
        if self.provider_manager:
            self.memory_manager.set_provider_source(
                lambda: self.provider_manager.active_provider if self.provider_manager else None
            )
            self.memory_manager.set_provider_manager(self.provider_manager)
        await self.memory_manager.initialize()
        logger.info("Memory manager initialized.")

    async def _init_tools(self, config: JarvisConfig) -> None:
        """Initialize the tool registry and tool executor."""
        from jarvis.tools.executor import ToolExecutor
        from jarvis.tools.registry import ToolRegistry
        self.tool_registry = ToolRegistry(config)
        self.tool_registry.discover_tools()
        self.tool_executor = ToolExecutor(config, self.tool_registry)
        logger.info(f"Tool registry initialized with {len(self.tool_registry)} tools.")

    async def _init_mcp(self, config: JarvisConfig) -> None:
        """Initialize the MCP manager."""
        from jarvis.mcp.manager import MCPManager
        self.mcp_manager = MCPManager(config)
        await self.mcp_manager.initialize()
        logger.info("MCP manager initialized.")

    async def _init_voice(self, config: JarvisConfig) -> None:
        """Initialize the voice (TTS/STT) manager.

        Voice initialization is best-effort: if a provider fails (e.g. a
        missing ElevenLabs API key or audio device), JARVIS continues in
        text mode rather than crashing.
        """
        if not config.voice.enabled:
            self.voice_manager = None
            return

        from jarvis.voice.manager import VoiceManager
        try:
            manager = VoiceManager(config)
            await manager.initialize()
            self.voice_manager = manager
            logger.info("Voice manager initialized.")
        except Exception as e:
            self.voice_manager = None
            logger.warning(f"Voice manager failed to initialize ({e}); using text mode.")

    def _update_tool_defs_from_schema_call(
        self,
        tool_defs: list[ToolDefinition],
        tool_name: str,
        tool_args: dict[str, Any],
        all_raw_defs: list[ToolDefinition],
    ) -> None:
        """If get_schema was invoked, add requested tool schemas to tool_defs for subsequent turns."""
        if tool_name != "get_schema":
            return
        raw_names = tool_args.get("tool_names") or tool_args.get("names") or []
        if isinstance(raw_names, str):
            names = [n.strip() for n in raw_names.split(",") if n.strip()]
        elif isinstance(raw_names, list):
            names = [str(n).strip() for n in raw_names if str(n).strip()]
        else:
            names = []

        existing = {t.name for t in tool_defs}
        for raw in all_raw_defs:
            if raw.name in names and raw.name not in existing:
                tool_defs.append(raw)
                existing.add(raw.name)

    def _get_capability_summary(self, all_tools: list[ToolDefinition]) -> str:
        """Generate a concise capability summary informing the model of discovery tools."""
        return (
            "JARVIS has access to external tools and MCP capabilities.\n"
            "Use the `list_tools()` tool to discover all available tool names (built-in and MCP tools),\n"
            "and use `get_schema(tool_names=[...])` to retrieve the JSON parameters schema for any tool you wish to invoke."
        )

    async def _get_all_raw_tool_definitions(self) -> list[ToolDefinition]:
        """Gather complete list of all registered built-in and MCP tool definitions."""
        tool_defs: list[ToolDefinition] = []

        if self.config and self.config.tools.enabled and self.tool_registry:
            for schema_dict in self.tool_registry.get_schemas():
                tool_defs.append(
                    ToolDefinition(
                        name=schema_dict["name"],
                        description=schema_dict["description"],
                        parameters=schema_dict["parameters"],
                        aliases=schema_dict.get("aliases", []),
                        category=schema_dict.get("category", "basic"),
                        keywords=schema_dict.get("keywords", []),
                    )
                )

        if self.mcp_manager and self.config and self.config.mcp.enabled:
            tool_defs.extend(self.mcp_manager.get_all_tool_definitions())

        return tool_defs

    async def _get_tool_definitions(self, query: str | None = None) -> tuple[list[ToolDefinition], str]:
        """Convert registered tools into provider ToolDefinition list & capability summary.

        Filters total tools down to always_include tools (including list_tools and get_schema).
        """
        all_defs = await self._get_all_raw_tool_definitions()
        capability_summary = self._get_capability_summary(all_defs)

        always_inc_names = set()
        if self.config and self.config.tools and self.config.tools.always_include:
            always_inc_names.update(self.config.tools.always_include)

        always_inc_names.add("list_tools")
        always_inc_names.add("get_schema")

        selected_tools = [t for t in all_defs if t.name in always_inc_names]
        return selected_tools, capability_summary

    async def _execute_tool(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        approval_callback: Any = None,
    ) -> str:
        """Execute a tool, routing MCP-qualified names to the MCP manager.

        Falls back to the built-in tool executor for regular tools.
        """
        if self.mcp_manager and self.mcp_manager.has_tool(tool_name):
            try:
                return await self.mcp_manager.call_tool(tool_name, tool_args)
            except Exception as e:
                return f"Error executing MCP tool '{tool_name}': {e}"

        if not self.tool_executor:
            return f"Tool executor unavailable for '{tool_name}'."

        try:
            return await self.tool_executor.execute(
                tool_name,
                tool_args,
                approval_callback=approval_callback,
            )
        except Exception as e:
            return f"Error executing tool '{tool_name}': {e}"

    def _parse_tool_call(self, tool_call: dict[str, Any]) -> tuple[str, dict[str, Any], str]:
        """Parse a normalized tool call into (name, args, call_id)."""
        fn = tool_call.get("function", {})
        tool_name = fn.get("name", "unknown")
        tool_args_raw = fn.get("arguments", {})

        if isinstance(tool_args_raw, str):
            try:
                tool_args = json.loads(tool_args_raw)
            except json.JSONDecodeError:
                tool_args = {"input": tool_args_raw}
        else:
            tool_args = tool_args_raw or {}

        tool_call_id = tool_call.get("id", f"call_{tool_name}")
        return tool_name, tool_args, tool_call_id

    async def _stream_turn(
        self,
        messages: list[Message],
        gen_config: GenerationConfig,
        content_parts: list[str],
        tool_calls_box: dict[str, Any],
    ) -> AsyncIterator[str]:
        """Stream one generation turn, accumulating tool call deltas.

        Yields content chunks as they arrive and stores the merged
        tool calls in ``tool_calls_box["calls"]`` when the turn ends.
        Tool call deltas are merged by index (OpenAI streaming format).
        """
        if not self.provider_manager:
            raise RuntimeError("Provider manager unavailable. Call initialize() first.")

        accumulated: dict[int, dict[str, Any]] = {}

        async for chunk in self.provider_manager.stream(messages, gen_config):
            if chunk.content:
                content_parts.append(chunk.content)
                yield chunk.content

            for tc in chunk.tool_calls or []:
                index = tc.get("index")
                if index is None:
                    index = len(accumulated)
                if index not in accumulated:
                    accumulated[index] = {
                        "id": tc.get("id") or f"call_{index}",
                        "type": "function",
                        "function": {"name": "", "arguments": ""},
                    }
                sig = tc.get("thought_signature") or tc.get("thoughtSignature")
                if sig:
                    accumulated[index]["thought_signature"] = sig

                fn = tc.get("function", {})
                if fn.get("name"):
                    accumulated[index]["function"]["name"] += fn["name"]
                if fn.get("arguments"):
                    accumulated[index]["function"]["arguments"] += fn["arguments"]

        # Drop incomplete deltas (no function name received)
        tool_calls_box["calls"] = [
            tc for tc in accumulated.values()
            if tc.get("function", {}).get("name")
        ]

    async def _extract_memories(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        """Extract and store long-term memories from a completed exchange."""
        if not self.memory_manager or not self.memory_manager.long_term:
            return
        if not self.config or not self.config.memory.long_term.auto_extract:
            return

        try:
            await self.memory_manager.extract_and_store(
                session_id,
                [
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": assistant_message},
                ],
            )
        except Exception as e:
            logger.warning(f"Long-term memory extraction failed: {e}")

    def _schedule_memory_extraction(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        """Schedule long-term memory extraction in the background.

        Runs without blocking the user's response so chat stays snappy.
        """
        if not self.memory_manager:
            return
        if not self.config or not self.config.memory.long_term.auto_extract:
            return

        task = asyncio.create_task(
            self._extract_memories(session_id, user_message, assistant_message)
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    def _format_memory_context(self, raw_mem: dict[str, Any]) -> str:
        """Format raw memory context into readable string."""
        parts: list[str] = []

        long_term = raw_mem.get("long_term") or []
        if long_term:
            parts.append("Long-term Facts:")
            for item in long_term:
                parts.append(f"- {item.get('content', '')}")

        return "\n".join(parts)
