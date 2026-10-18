"""Adapter interface between the Executor and capability implementations (run_execution.md §5).

An adapter never resolves code or endpoints from contract data: it is bound in code to an allowlisted
implementation key (app/catalog/registry.py, app/executor/handlers.py).
"""

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

AdapterStatus = Literal["ok", "timeout", "error", "invalid_output", "too_large", "unavailable", "budget_exceeded"]
MAX_OUTPUT_BYTES = 1_048_576

# Statuses worth retrying when the capability declares itself idempotent.
TRANSIENT: frozenset[str] = frozenset({"timeout", "error"})


@dataclass
class AdapterResult:
    status: AdapterStatus
    output: dict[str, Any] | None = None
    execution_mode: Literal["real", "mock"] = "real"
    error_code: str | None = None
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0
    cost_jpy: float | None = 0
    llm: dict[str, Any] | None = field(default=None)


class Handler(Protocol):
    """Runs one capability call. Must return within timeout_s (+ a small margin) and never raise."""

    def invoke(self, inputs: dict[str, Any], config: dict[str, Any], timeout_s: float) -> AdapterResult: ...


class UnavailableHandler:
    """For kinds whose adapters are not implemented yet (mcp_tool, rest in Phase 2)."""

    def invoke(self, inputs: dict[str, Any], config: dict[str, Any], timeout_s: float) -> AdapterResult:
        return AdapterResult(status="unavailable", error_code="implementation_unavailable")
