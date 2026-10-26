"""Implementation keys bound to code (run_execution.md §5). The only place where a key becomes executable.

`human_review.v1` is handled by the Executor itself (it pauses the run). app/catalog/registry.py marks exactly
these keys (plus human review) as available; a test checks it. Handlers that need stored resources (documents,
Rule packs) read them in the worker and pass them to the child process (app/adapters/resources.py).
"""

import sys

from app.adapters.llm import LlmHandler, MockLlm
from app.adapters.local import LocalHandler
from app.adapters.mcp import BACKEND_DIR, McpToolHandler
from app.adapters.resources import RulePackHandler, StoredDocumentHandler
from app.capabilities import mock_extractor
from app.capabilities.document_parser import parse_document
from app.capabilities.result_exporter import export_result
from app.capabilities.rule_extractor import extract_by_labels
from app.capabilities.rule_validator import validate_rules
from app.catalog.implementation_integrity import (
    Binding,
    ImplementationIntegrityError,
    verify_bindings,
    verify_files,
)
from app.core.config import Settings
from app.core.db import make_session_factory
from app.executor.engine import HandlerTable


def production_handlers(settings: Settings) -> HandlerTable:
    manifest = verify_files()
    session_factory = make_session_factory(settings)  # connects lazily
    handlers: HandlerTable = {
        ("local", "document_parser.v1"): StoredDocumentHandler(parse_document, session_factory, settings.storage_dir),
        ("local", "rule_based_extractor.v1"): LocalHandler(extract_by_labels),
        # D-004: only the mock provider is wired. A real provider replaces MockLlm behind the same port.
        ("llm", "structured_extractor.v1"): LlmHandler(
            MockLlm(mock_extractor.mock_response), mock_extractor.INSTRUCTIONS, mock_extractor.output_schema
        ),
        ("local", "rule_validator.v1"): RulePackHandler(validate_rules, session_factory),
        # ADR-005: EASF's own local MCP server over stdio (real protocol, not an external integration).
        ("mcp_tool", "easf_local_mcp:locate_evidence"): McpToolHandler("locate_evidence"),
        ("local", "result_exporter.v1"): LocalHandler(export_result),
    }
    verify_bindings(manifest, _bindings(handlers))
    return handlers


def _bindings(handlers: HandlerTable) -> dict[tuple[str, str], Binding]:
    """既知のオブジェクトとの同一性を検査し、表の文字列は実行に使わない。"""
    functions = {
        ("local", "document_parser.v1"): parse_document,
        ("local", "rule_based_extractor.v1"): extract_by_labels,
        ("local", "rule_validator.v1"): validate_rules,
        ("local", "result_exporter.v1"): export_result,
    }
    result: dict[tuple[str, str], Binding] = {}
    for key, handler in handlers.items():
        entry = ""
        if type(handler) in (StoredDocumentHandler, RulePackHandler) and isinstance(
            handler, (StoredDocumentHandler, RulePackHandler)
        ):
            if type(handler.local) is LocalHandler and handler.local.func is functions.get(key):
                entry = f"{handler.local.func.__module__}.{handler.local.func.__qualname__}"
        elif type(handler) is LocalHandler and isinstance(handler, LocalHandler):
            if handler.func is functions.get(key):
                entry = f"{handler.func.__module__}.{handler.func.__qualname__}"
        elif type(handler) is LlmHandler and isinstance(handler, LlmHandler):
            if (
                type(handler.port) is MockLlm
                and isinstance(handler.port, MockLlm)
                and handler.port.responder is mock_extractor.mock_response
                and handler.schema_for is mock_extractor.output_schema
                and handler.instructions == mock_extractor.INSTRUCTIONS
            ):
                entry = "app.capabilities.mock_extractor.mock_response"
        elif type(handler) is McpToolHandler and isinstance(handler, McpToolHandler):
            server = handler.server
            if (
                handler.tool == "locate_evidence"
                and server.command == sys.executable
                and server.args == ["-m", "app.mcp_server"]
                and server.cwd == str(BACKEND_DIR)
                and server.env is None
            ):
                entry = "app.mcp_server.locate_evidence"
        if not entry:
            raise ImplementationIntegrityError("implementation_binding_mismatch")
        result[key] = Binding(handler=type(handler).__name__, entry=entry)
    return result
