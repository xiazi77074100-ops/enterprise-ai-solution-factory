"""Allowlist of implementation keys per capability kind (easf-capability-contract §2).

`implementation.ref` is never imported or resolved as a path; it must be one of these keys. The Executor
(Phase 2) binds keys to code. `available=False` means the key is declared but its code is not implemented yet,
so a registered version cannot run until it is (registration is allowed so contracts can be reviewed early).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ImplementationKey:
    kind: str
    ref: str
    available: bool


IMPLEMENTATIONS: dict[tuple[str, str], ImplementationKey] = {
    (k.kind, k.ref): k
    for k in (
        ImplementationKey("local", "document_parser.v1", available=False),
        ImplementationKey("llm", "structured_extractor.v1", available=False),
        ImplementationKey("local", "rule_based_extractor.v1", available=False),
        ImplementationKey("local", "rule_validator.v1", available=False),
        ImplementationKey("mcp_tool", "easf_local_mcp:locate_evidence", available=False),
        ImplementationKey("local", "human_review.v1", available=True),  # handled by the Executor (P2-02)
        ImplementationKey("local", "result_exporter.v1", available=False),
    )
}


def is_allowed(kind: str, ref: str) -> bool:
    return (kind, ref) in IMPLEMENTATIONS
