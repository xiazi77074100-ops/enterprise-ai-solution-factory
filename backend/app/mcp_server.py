"""EASF's own local MCP server (ADR-005): `python -m app.mcp_server`, stdio only, one tool.

This is a real MCP protocol call made by the Executor's MCP adapter, not an external integration. The tool's
input/output schemas are the Catalog contract's (contracts/examples/capabilities/evidence_locator.json); the
Catalog compares them when an mcp_tool version is registered (app/catalog/service.py).
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from app.capabilities.evidence import locate

SERVER_NAME = "easf_local_mcp"
_CONTRACT = Path(__file__).resolve().parent / "mcp_tools" / "locate_evidence.json"
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {"locate_evidence": json.loads(_CONTRACT.read_text(encoding="utf-8"))}


def call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Runs an advertised tool after validating its input. Unknown tools raise (deny by default)."""
    schemas = TOOL_SCHEMAS[name]
    errors = list(Draft202012Validator(schemas["input_schema"]).iter_errors(arguments))
    if errors:
        raise ValueError("invalid tool input")
    if name == "locate_evidence":
        return locate(arguments["document_id"], arguments["pages"], arguments["fields"], arguments["match"])
    raise KeyError(name)


async def _list_tools(ctx: Any, params: Any) -> types.ListToolsResult:
    return types.ListToolsResult(
        tools=[
            types.Tool(name=name, input_schema=s["input_schema"], output_schema=s["output_schema"])
            for name, s in TOOL_SCHEMAS.items()
        ]
    )


async def _call_tool(ctx: Any, params: Any) -> types.CallToolResult:
    try:
        result = call(params.name, dict(params.arguments or {}))
    except (KeyError, ValueError) as exc:  # the type only: inputs are documents
        return types.CallToolResult(content=[types.TextContent(text=type(exc).__name__)], is_error=True)
    return types.CallToolResult(
        content=[types.TextContent(text=json.dumps(result, ensure_ascii=False))], structured_content=result
    )


async def _main() -> None:
    server: Server[Any] = Server(SERVER_NAME, on_list_tools=_list_tools, on_call_tool=_call_tool)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(_main())
