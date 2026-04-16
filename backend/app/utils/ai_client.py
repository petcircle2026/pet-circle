"""
PetCircle — Unified AI Client Adapter

Provides get_ai_client() and get_sync_ai_client() that return Anthropic-API-compatible
objects when AI_PROVIDER='openai'. This lets all services call client.messages.create(...)
and access response.content[0].text without any changes to response-parsing code.

Routing:
    AI_PROVIDER='claude'  → returns native AsyncAnthropic / Anthropic clients
    AI_PROVIDER='openai'  → returns _OpenAIAdapter / _SyncOpenAIAdapter which translate
                             Anthropic-style calls into OpenAI ChatCompletion calls and
                             wrap results in Anthropic-shaped response objects.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy-initialised client singletons
# ---------------------------------------------------------------------------

_async_anthropic_client = None
_async_openai_client = None
_sync_openai_client = None
_sync_anthropic_client = None

_async_openai_adapter: _OpenAIAdapter | None = None
_sync_openai_adapter: _SyncOpenAIAdapter | None = None


# ---------------------------------------------------------------------------
# Anthropic-shaped response shims
# ---------------------------------------------------------------------------

class _TextContent:
    """Mimics Anthropic TextBlock: response.content[0].text"""
    __slots__ = ("text", "type")

    def __init__(self, text: str) -> None:
        self.text = text
        self.type = "text"


class _ToolUseContent:
    """Mimics Anthropic ToolUseBlock: response.content[0].input (a dict)"""
    __slots__ = ("input", "type", "id", "name")

    def __init__(self, input_dict: dict, tool_id: str = "", tool_name: str = "") -> None:
        self.input = input_dict
        self.type = "tool_use"
        self.id = tool_id
        self.name = tool_name


class _FakeResponse:
    """Anthropic-shaped response wrapper for OpenAI replies."""
    __slots__ = ("content", "stop_reason")

    def __init__(self, content_items: list, stop_reason: str = "end_turn") -> None:
        self.content = content_items
        self.stop_reason = stop_reason


# ---------------------------------------------------------------------------
# OpenAI image block translation helper
# ---------------------------------------------------------------------------

def _translate_messages_to_openai(
    messages: list[dict], system: str | None = None
) -> list[dict]:
    """
    Convert Anthropic-style messages (possibly with image content blocks) to
    OpenAI ChatCompletion messages format.

    Anthropic image block:
        {"type": "image", "source": {"type": "base64", "media_type": "...", "data": "..."}}
    OpenAI image block:
        {"type": "image_url", "image_url": {"url": "data:...;base64,...", "detail": "high"}}
    """
    oai_messages: list[dict] = []
    if system:
        oai_messages.append({"role": "system", "content": system})

    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        if isinstance(content, list):
            # Check for Anthropic-style tool_result blocks (user turn after a tool call).
            # Translate each into a separate OpenAI "tool" message.
            if any(part.get("type") == "tool_result" for part in content if isinstance(part, dict)):
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    if part.get("type") == "tool_result":
                        tool_content = part.get("content", "")
                        if isinstance(tool_content, list):
                            # Nested content blocks — flatten to text
                            tool_content = " ".join(
                                p.get("text", "") for p in tool_content
                                if isinstance(p, dict) and p.get("type") == "text"
                            )
                        oai_messages.append({
                            "role": "tool",
                            "tool_call_id": part.get("tool_use_id", ""),
                            "content": str(tool_content),
                        })
                continue

            # Check for Anthropic-style tool_use blocks (assistant turn with tool calls).
            tool_use_parts = [
                p for p in content
                if isinstance(p, dict) and p.get("type") == "tool_use"
            ]
            if tool_use_parts:
                tool_calls = []
                for p in tool_use_parts:
                    tool_calls.append({
                        "id": p.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": p.get("name", ""),
                            "arguments": json.dumps(p.get("input", {})),
                        },
                    })
                # Include any text blocks alongside tool_calls
                text_parts = [
                    p.get("text", "") for p in content
                    if isinstance(p, dict) and p.get("type") == "text"
                ]
                oai_messages.append({
                    "role": "assistant",
                    "content": " ".join(text_parts) if text_parts else None,
                    "tool_calls": tool_calls,
                })
                continue

            # Standard multi-part content (vision or mixed text/image)
            oai_content: list[dict] = []
            for part in content:
                if not isinstance(part, dict):
                    continue
                ptype = part.get("type")
                if ptype == "text":
                    oai_content.append({"type": "text", "text": part["text"]})
                elif ptype == "image":
                    src = part.get("source", {})
                    if src.get("type") == "base64":
                        data_url = f"data:{src['media_type']};base64,{src['data']}"
                        oai_content.append({
                            "type": "image_url",
                            "image_url": {"url": data_url, "detail": "high"},
                        })
            if oai_content:
                oai_messages.append({"role": role, "content": oai_content})
            # Skip empty content lists (e.g. corrupted turns) rather than sending []
        else:
            oai_messages.append(msg)

    return oai_messages


def _anthropic_tools_to_openai(tools: list[dict]) -> list[dict]:
    """Convert Anthropic tool schema list to OpenAI function definitions."""
    oai_tools = []
    for t in tools:
        oai_tools.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", {}),
            },
        })
    return oai_tools


def _anthropic_tool_choice_to_openai(tool_choice: dict | None) -> Any:
    """Convert Anthropic tool_choice dict to OpenAI format."""
    if not tool_choice:
        return "auto"
    if tool_choice.get("type") == "tool":
        return {"type": "function", "function": {"name": tool_choice["name"]}}
    return "auto"


# ---------------------------------------------------------------------------
# Async adapter — routes client.messages.create() to OpenAI async
# ---------------------------------------------------------------------------

class _AsyncMessagesProxy:
    """
    Async proxy for client.messages.  Accepts Anthropic-style kwargs and
    routes to the OpenAI async ChatCompletion API.
    """

    async def create(
        self,
        *,
        model: str,
        messages: list[dict],
        temperature: float = 0.0,
        max_tokens: int = 1500,
        system: str | None = None,
        tools: list[dict] | None = None,
        tool_choice: dict | None = None,
        **_kwargs: Any,
    ) -> _FakeResponse:
        client = _get_async_openai_client()
        oai_messages = _translate_messages_to_openai(messages, system)

        if tools:
            oai_tools = _anthropic_tools_to_openai(tools)
            oai_tc = _anthropic_tool_choice_to_openai(tool_choice)

            response = await client.chat.completions.create(
                model=model,
                messages=oai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=oai_tools,
                tool_choice=oai_tc,
            )
            stop_reason = response.choices[0].finish_reason or "end_turn"
            # OpenAI may return None or empty tool_calls list if model didn't use tools
            tool_calls = response.choices[0].message.tool_calls
            if tool_calls and len(tool_calls) > 0:
                blocks = []
                for tc in tool_calls:
                    input_dict = json.loads(tc.function.arguments or "{}")
                    blocks.append(_ToolUseContent(input_dict, tool_id=tc.id, tool_name=tc.function.name))
                return _FakeResponse(blocks, stop_reason=stop_reason)
            # Model returned text instead of a tool call — use the text directly
            text = response.choices[0].message.content or ""
            return _FakeResponse([_TextContent(text)], stop_reason=stop_reason)

        response = await client.chat.completions.create(
            model=model,
            messages=oai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = response.choices[0].message.content or ""
        stop_reason = response.choices[0].finish_reason or "end_turn"
        return _FakeResponse([_TextContent(text)], stop_reason=stop_reason)


class _OpenAIAdapter:
    """
    Drop-in async replacement for AsyncAnthropic.
    Exposes the `.messages` attribute so `client.messages.create(...)` works unchanged.
    """

    def __init__(self) -> None:
        self.messages = _AsyncMessagesProxy()


# ---------------------------------------------------------------------------
# Sync adapter — routes client.messages.create() to OpenAI sync
# ---------------------------------------------------------------------------

class _SyncMessagesProxy:
    """Sync proxy for client.messages used by nudge_scheduler and similar."""

    def create(
        self,
        *,
        model: str,
        messages: list[dict],
        temperature: float = 0.0,
        max_tokens: int = 1500,
        system: str | None = None,
        tools: list[dict] | None = None,
        tool_choice: dict | None = None,
        **_kwargs: Any,
    ) -> _FakeResponse:
        client = _get_sync_openai_client()
        oai_messages = _translate_messages_to_openai(messages, system)

        if tools:
            oai_tools = _anthropic_tools_to_openai(tools)
            oai_tc = _anthropic_tool_choice_to_openai(tool_choice)

            response = client.chat.completions.create(
                model=model,
                messages=oai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=oai_tools,
                tool_choice=oai_tc,
            )
            stop_reason = response.choices[0].finish_reason or "end_turn"
            # OpenAI may return None or empty tool_calls list if model didn't use tools
            tool_calls = response.choices[0].message.tool_calls
            if tool_calls and len(tool_calls) > 0:
                blocks = []
                for tc in tool_calls:
                    input_dict = json.loads(tc.function.arguments or "{}")
                    blocks.append(_ToolUseContent(input_dict, tool_id=tc.id, tool_name=tc.function.name))
                return _FakeResponse(blocks, stop_reason=stop_reason)
            # Model returned text instead of a tool call — use the text directly
            text = response.choices[0].message.content or ""
            return _FakeResponse([_TextContent(text)], stop_reason=stop_reason)

        response = client.chat.completions.create(
            model=model,
            messages=oai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = response.choices[0].message.content or ""
        stop_reason = response.choices[0].finish_reason or "end_turn"
        return _FakeResponse([_TextContent(text)], stop_reason=stop_reason)


class _SyncOpenAIAdapter:
    """Drop-in sync replacement for anthropic.Anthropic."""

    def __init__(self) -> None:
        self.messages = _SyncMessagesProxy()


# ---------------------------------------------------------------------------
# Internal client constructors
# ---------------------------------------------------------------------------

def _get_async_openai_client():
    global _async_openai_client
    if _async_openai_client is None:
        from openai import AsyncOpenAI  # noqa: PLC0415
        from app.config import settings  # noqa: PLC0415
        _async_openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _async_openai_client


def _get_sync_openai_client():
    global _sync_openai_client
    if _sync_openai_client is None:
        from openai import OpenAI  # noqa: PLC0415
        from app.config import settings  # noqa: PLC0415
        _sync_openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _sync_openai_client


def _get_async_anthropic_client():
    global _async_anthropic_client
    if _async_anthropic_client is None:
        from anthropic import AsyncAnthropic  # noqa: PLC0415
        from app.config import settings  # noqa: PLC0415
        _async_anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _async_anthropic_client


def _get_sync_anthropic_client():
    global _sync_anthropic_client
    if _sync_anthropic_client is None:
        import anthropic  # noqa: PLC0415
        from app.config import settings  # noqa: PLC0415
        _sync_anthropic_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _sync_anthropic_client


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_ai_client():
    """
    Return the appropriate async AI client based on the AI_PROVIDER setting.

    - AI_PROVIDER='claude' → AsyncAnthropic (native)
    - AI_PROVIDER='openai' → _OpenAIAdapter (Anthropic-compatible interface over OpenAI)

    Both expose `client.messages.create(...)` and return responses with `.content[0].text`
    so no changes are needed in service response-parsing code.
    """
    from app.core.constants import AI_PROVIDER  # noqa: PLC0415

    if AI_PROVIDER == "openai":
        global _async_openai_adapter
        if _async_openai_adapter is None:
            _async_openai_adapter = _OpenAIAdapter()
        return _async_openai_adapter

    return _get_async_anthropic_client()


def get_sync_ai_client():
    """
    Return the appropriate sync AI client based on the AI_PROVIDER setting.

    Used by services that call the AI API synchronously (nudge_scheduler,
    medicine_recurrence_service, etc.).

    - AI_PROVIDER='claude' → anthropic.Anthropic (native sync)
    - AI_PROVIDER='openai' → _SyncOpenAIAdapter (Anthropic-compatible interface over OpenAI)
    """
    from app.core.constants import AI_PROVIDER  # noqa: PLC0415

    if AI_PROVIDER == "openai":
        global _sync_openai_adapter
        if _sync_openai_adapter is None:
            _sync_openai_adapter = _SyncOpenAIAdapter()
        return _sync_openai_adapter

    return _get_sync_anthropic_client()
