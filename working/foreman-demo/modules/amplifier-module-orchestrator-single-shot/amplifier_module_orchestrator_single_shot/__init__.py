"""
Single-shot orchestrator - executes exactly one LLM cycle and returns.
No loops, no retries. Maximum 2 LLM calls total (initial + optional tool follow-up).
"""

import asyncio
import logging
from typing import Any

from amplifier_core import HookRegistry
from amplifier_core import ModuleCoordinator
from amplifier_core.events import ORCHESTRATOR_COMPLETE
from amplifier_core.events import PROMPT_SUBMIT
from amplifier_core.events import PROVIDER_REQUEST
from amplifier_core.events import TOOL_POST
from amplifier_core.events import TOOL_PRE
from amplifier_core.message_models import ChatRequest
from amplifier_core.message_models import Message
from amplifier_core.message_models import ToolSpec

logger = logging.getLogger(__name__)


async def mount(coordinator: ModuleCoordinator, config: dict[str, Any] | None = None):
    """Mount the single-shot orchestrator module."""
    config = config or {}
    orchestrator = SingleShotOrchestrator(config)
    await coordinator.mount("orchestrator", orchestrator)
    logger.info("Mounted SingleShotOrchestrator")
    return


class SingleShotOrchestrator:
    """
    Single-shot orchestrator: executes ONE LLM interaction and returns.

    Flow:
    1. Call LLM once
    2. If tool calls: execute them, call LLM again with results
    3. Return immediately (max 2 LLM calls)

    No loops, no iterations, no "until done" logic.
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.extended_thinking = config.get("extended_thinking", False)

    async def execute(
        self,
        prompt: str,
        context,
        providers: dict[str, Any],
        tools: dict[str, Any],
        hooks: HookRegistry,
        coordinator: ModuleCoordinator | None = None,
    ) -> str:
        """Execute one prompt-response cycle."""

        # Emit prompt submit
        result = await hooks.emit(PROMPT_SUBMIT, {"prompt": prompt})
        if coordinator:
            result = await coordinator.process_hook_result(result, "prompt:submit", "orchestrator")
            if result.action == "deny":
                return f"Operation denied: {result.reason}"

        # Add user message
        await context.add_message({"role": "user", "content": prompt})

        # Select provider
        provider = self._select_provider(providers)
        if not provider:
            return "Error: No providers available"

        provider_name = self._get_provider_name(providers, provider)

        # FIRST LLM CALL
        await hooks.emit(PROVIDER_REQUEST, {"provider": provider_name, "iteration": 1})

        chat_request = self._build_chat_request(context, tools)
        response = await provider.complete(chat_request, extended_thinking=self.extended_thinking)

        # Parse tool calls
        tool_calls = provider.parse_tool_calls(response) if hasattr(provider, "parse_tool_calls") else []

        if not tool_calls:
            # No tools - extract text and return
            text = self._extract_text(response)
            print(f"[ORCHESTRATOR] No tool calls made by LLM - returning text response")
            await context.add_message({"role": "assistant", "content": text})

            await hooks.emit(ORCHESTRATOR_COMPLETE, {
                "orchestrator": "single-shot",
                "turn_count": 1,
                "status": "success"
            })

            return text

        # Add assistant message with tool calls
        await context.add_message({
            "role": "assistant",
            "content": self._extract_text(response),
            "tool_calls": [
                {"id": tc.id, "tool": tc.name, "arguments": tc.arguments}
                for tc in tool_calls
            ]
        })

        # Execute tools in parallel
        tool_results = await self._execute_tools_parallel(tool_calls, tools, hooks, coordinator)

        # Add tool results to context
        for tool_call_id, content in tool_results:
            await context.add_message({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": content
            })

        # SECOND LLM CALL (with tool results)
        await hooks.emit(PROVIDER_REQUEST, {"provider": provider_name, "iteration": 2})

        chat_request = self._build_chat_request(context, tools)
        response = await provider.complete(chat_request, extended_thinking=self.extended_thinking)

        text = self._extract_text(response)
        await context.add_message({"role": "assistant", "content": text})

        await hooks.emit(ORCHESTRATOR_COMPLETE, {
            "orchestrator": "single-shot",
            "turn_count": 2,
            "status": "success"
        })

        return text

    def _build_chat_request(self, context, tools) -> ChatRequest:
        """Build ChatRequest from context messages and tools."""
        message_dicts = list(context.messages)
        messages = [Message(**msg) for msg in message_dicts]

        tools_list = None
        if tools:
            tools_list = [
                ToolSpec(name=t.name, description=t.description, parameters=t.input_schema)
                for t in tools.values()
            ]

        return ChatRequest(messages=messages, tools=tools_list)

    async def _execute_tools_parallel(
        self,
        tool_calls,
        tools: dict[str, Any],
        hooks: HookRegistry,
        coordinator: ModuleCoordinator | None,
    ) -> list[tuple[str, str]]:
        """Execute all tool calls in parallel."""

        async def execute_one(tc):
            # Emit pre-tool hook
            await hooks.emit(TOOL_PRE, {"tool_name": tc.name, "tool_input": tc.arguments})

            tool = tools.get(tc.name)
            if not tool:
                return (tc.id, f"Error: Tool '{tc.name}' not found")

            try:
                result = await tool.execute(tc.arguments)
                content = str(result.output if hasattr(result, 'output') else result)

                # Emit post-tool hook
                await hooks.emit(TOOL_POST, {
                    "tool_name": tc.name,
                    "tool_input": tc.arguments,
                    "result": result
                })

                return (tc.id, content)
            except Exception as e:
                logger.error(f"Tool {tc.name} failed: {e}")
                return (tc.id, f"Error: {str(e)}")

        return await asyncio.gather(*[execute_one(tc) for tc in tool_calls])

    def _extract_text(self, response) -> str:
        """Extract text content from response."""
        if hasattr(response, "text") and response.text:
            return response.text

        content = getattr(response, "content", "")
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            text_parts = []
            for block in content:
                if hasattr(block, "text"):
                    text_parts.append(block.text)
            return "\n\n".join(text_parts)

        return str(content)

    def _select_provider(self, providers: dict[str, Any]) -> Any:
        """Select highest priority provider."""
        if not providers:
            return None

        provider_list = []
        for name, provider in providers.items():
            priority = getattr(provider, "priority", 100)
            provider_list.append((priority, provider))

        provider_list.sort(key=lambda x: x[0])
        return provider_list[0][1] if provider_list else None

    def _get_provider_name(self, providers: dict[str, Any], provider) -> str:
        """Find provider name from provider instance."""
        for name, prov in providers.items():
            if prov is provider:
                return name
        return "unknown"
