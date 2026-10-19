"""Implementation keys bound to code (run_execution.md §5). The only place where a key becomes executable.

`human_review.v1` is handled by the Executor itself (it pauses the run). app/catalog/registry.py marks exactly
these keys (plus human review) as available; a test checks it. Handlers that need stored resources (documents,
Rule packs) read them in the worker and pass them to the child process (app/adapters/resources.py).
"""

from app.adapters.llm import LlmHandler, MockLlm
from app.adapters.local import LocalHandler
from app.adapters.mcp import McpToolHandler
from app.adapters.resources import RulePackHandler, StoredDocumentHandler
from app.capabilities import mock_extractor
from app.capabilities.document_parser import parse_document
from app.capabilities.result_exporter import export_result
from app.capabilities.rule_extractor import extract_by_labels
from app.capabilities.rule_validator import validate_rules
from app.core.config import Settings
from app.core.db import make_session_factory
from app.executor.engine import HandlerTable


def production_handlers(settings: Settings) -> HandlerTable:
    session_factory = make_session_factory(settings)  # connects lazily
    return {
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
