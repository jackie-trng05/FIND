"""Thin client to the shared, non-containerised FIND MCP server.

The MCP server runs as a local host process on the streamable-HTTP transport.
Containerised student backends reach it at ``http://host.docker.internal:16050``
(overridable with ``MCP_SERVER_URL``). This module exposes a single synchronous
``call_tool`` helper that returns the tool's *retrieval-context object*:

    { "answer_data": ..., "sources": [...], "confidence": "High|Medium|Low" }

The frontend never talks to the MCP server directly — it always goes through
this backend/API (see ``routes/mcp_mode.py``).

The ``mcp`` SDK is imported lazily so that importing this module (and running
the backend with ``MCP_ENABLED=false``, e.g. in CI) does not require the SDK.
"""

import json
import os

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://host.docker.internal:16050/mcp")


class MCPClientError(RuntimeError):
    """Raised when the MCP server cannot be reached or a tool call fails."""


def _parse_result(result) -> dict:
    """Extract the retrieval-context dict from an MCP CallToolResult."""
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        # FastMCP wraps bare return values under a "result" key.
        return structured.get("result", structured)

    content = getattr(result, "content", None) or []
    for item in content:
        text = getattr(item, "text", None)
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"answer_data": text, "sources": [], "confidence": "Low"}
    raise MCPClientError("MCP tool returned no readable content")


def call_tool(tool_name: str, arguments: dict | None = None) -> dict:
    """Call an MCP tool and return its retrieval-context object.

    Raises ``MCPClientError`` on transport/protocol failure so callers can map
    it to an HTTP 503 for the UI.
    """
    arguments = arguments or {}

    try:
        import anyio
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
    except ImportError as exc:  # pragma: no cover - only when SDK missing
        raise MCPClientError(f"MCP SDK not installed: {exc}") from exc

    async def _run() -> dict:
        async with streamablehttp_client(MCP_SERVER_URL) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return _parse_result(result)

    try:
        return anyio.run(_run)
    except MCPClientError:
        raise
    except Exception as exc:  # noqa: BLE001 - surface any transport failure
        raise MCPClientError(f"MCP call '{tool_name}' failed: {exc}") from exc
