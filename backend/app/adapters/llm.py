"""LlmPort (ADR-002). Phase 2 enables only the mock provider (D-004): no network, execution_mode "mock".

Capabilities never name a provider; the node config carries a profile name only. Real providers are added
after D-004 is lifted, behind the same port and the same server-side output validation.
"""

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from app.adapters.base import MAX_OUTPUT_BYTES, AdapterResult, AdapterStatus

LlmStatus = Literal["ok", "invalid_output", "refused", "timeout", "rate_limited", "provider_error", "budget_exceeded"]


@dataclass(frozen=True)
class LlmRequest:
    profile: str
    instructions: str
    documents: list[dict[str, Any]]
    output_schema: dict[str, Any]
    max_output_tokens: int
    timeout_ms: int
    temperature: float | None = 0


@dataclass(frozen=True)
class LlmResult:
    status: LlmStatus
    output: dict[str, Any] | None
    provider: str
    model: str
    execution_mode: Literal["real", "mock"]
    input_tokens: int
    output_tokens: int
    cost_jpy: float | None
    latency_ms: int
    raw_output_sha256: str


class LlmPort(Protocol):
    def generate_structured(self, request: LlmRequest) -> LlmResult: ...


MockResponder = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
"""Deterministic (inputs, config) -> output, written per implementation key (never from gold labels)."""


class MockLlm:
    """Deterministic stand-in for a provider. Token counts are a fixed function of the payload size."""

    def __init__(self, responder: MockResponder) -> None:
        self.responder = responder

    def generate_structured(self, request: LlmRequest) -> LlmResult:
        started = time.monotonic()
        inputs = request.documents[0] if request.documents else {}
        output = self.responder(inputs, {"profile": request.profile})
        raw = json.dumps(output, ensure_ascii=False, sort_keys=True).encode()
        return LlmResult(
            status="ok",
            output=output,
            provider="mock",
            model="mock",
            execution_mode="mock",
            input_tokens=len(json.dumps(request.documents, ensure_ascii=False)) // 4,
            output_tokens=len(raw) // 4,
            cost_jpy=0,
            latency_ms=int((time.monotonic() - started) * 1000),
            raw_output_sha256=hashlib.sha256(raw).hexdigest(),
        )


class LlmHandler:
    """Adapter from a capability call to the LlmPort. The provider is chosen by profile, not by the capability."""

    def __init__(self, port: LlmPort, instructions: str) -> None:
        self.port = port
        self.instructions = instructions

    def invoke(self, inputs: dict[str, Any], config: dict[str, Any], timeout_s: float) -> AdapterResult:
        result = self.port.generate_structured(
            LlmRequest(
                profile=str(config.get("llm_profile", "default")),
                instructions=self.instructions,
                documents=[inputs],
                output_schema={},
                max_output_tokens=4096,
                timeout_ms=int(timeout_s * 1000),
            )
        )
        llm = {
            "provider": result.provider,
            "model": result.model,
            "usage": {"input_tokens": result.input_tokens, "output_tokens": result.output_tokens},
            "cost_jpy": result.cost_jpy,
            "latency_ms": result.latency_ms,
            "raw_output_sha256": result.raw_output_sha256,
        }
        status: AdapterStatus = "ok"
        error_code: str | None = None
        output = result.output
        if result.status != "ok" or output is None:
            status, error_code, output = (
                ("timeout" if result.status == "timeout" else "error"),
                f"llm_{result.status}",
                None,
            )
        elif len(json.dumps(output, ensure_ascii=False).encode()) > MAX_OUTPUT_BYTES:
            status, error_code, output = "too_large", "output_too_large", None
        return AdapterResult(
            status=status,
            output=output,
            execution_mode=result.execution_mode,
            error_code=error_code,
            llm_input_tokens=result.input_tokens,
            llm_output_tokens=result.output_tokens,
            cost_jpy=result.cost_jpy,
            llm=llm,
        )
