"""MCP tool adapter (ADR-005): calls an allowlisted tool of EASF's own local MCP server over stdio.

The server is started with a fixed command (this interpreter, `-m app.mcp_server`); nothing about the command,
the server or the tool name comes from contract data. The call is real MCP protocol, but the server is local:
it is never reported as an external integration. Arguments are the node inputs plus the node config.
"""

import json
import sys
from pathlib import Path
from typing import Any

import anyio
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

from app.adapters.base import MAX_OUTPUT_BYTES, AdapterResult

BACKEND_DIR = Path(__file__).resolve().parents[2]
LOCAL_SERVER = StdioServerParameters(command=sys.executable, args=["-m", "app.mcp_server"], cwd=str(BACKEND_DIR))


class McpToolHandler:
    def __init__(self, tool: str, server: StdioServerParameters = LOCAL_SERVER) -> None:
        self.tool = tool
        self.server = server

    def invoke(self, inputs: dict[str, Any], config: dict[str, Any], timeout_s: float) -> AdapterResult:
        try:
            result = anyio.run(self._call, {**inputs, **config}, timeout_s)
        except TimeoutError:
            return AdapterResult(status="timeout", error_code="timeout")
        except Exception as exc:  # the server failed to start or the protocol broke: report the type only
            cause: BaseException = exc
            while isinstance(cause, BaseExceptionGroup) and cause.exceptions:  # anyio task groups wrap errors
                cause = cause.exceptions[0]
            if isinstance(cause, TimeoutError):
                return AdapterResult(status="timeout", error_code="timeout")
            return AdapterResult(status="error", error_code=f"mcp_{type(cause).__name__.lower()[:40]}")
        if result is None:
            return AdapterResult(status="unavailable", error_code="mcp_tool_not_advertised")
        if result.is_error or not isinstance(result.structured_content, dict):
            return AdapterResult(status="error", error_code="mcp_tool_error")
        output = result.structured_content
        if len(json.dumps(output, ensure_ascii=False).encode()) > MAX_OUTPUT_BYTES:
            return AdapterResult(status="too_large", error_code="output_too_large")
        return AdapterResult(status="ok", output=output)

    async def _call(self, arguments: dict[str, Any], timeout_s: float) -> types.CallToolResult | None:
        """None when the server does not advertise the tool (only allowlisted, advertised tools are called)."""
        with anyio.fail_after(timeout_s):
            async with stdio_client(self.server) as (read, write), ClientSession(read, write) as session:
                await session.initialize()
                listed = await session.list_tools()
                if self.tool not in {tool.name for tool in listed.tools}:
                    return None
                result = await session.call_tool(self.tool, arguments)
        if not isinstance(result, types.CallToolResult):
            raise TypeError("unexpected MCP result")
        return result
