# 06 — Decision Log and Risk Register

## Approved product decisions
- Audience: AI consulting/presales/architect/delivery team, not subsidiaries self-service.
- Product: capability-driven Solution Factory, not new group AI base, not an AI Coding wrapper.
- Two scenarios: Japanese invoice processing and contract review; real runnable workflow.
- Core: ~6 shared domain capabilities plus minimal Catalog, Composer, Executor, Evaluation, Trace and Reuse.
- Architecture: API-first, transport-neutral capability contract, MCP/REST/local adapters, optional upstream engineering Agent.
- Human-in-loop, immutable capability versions, quality and reuse evidence.
- Fair AI Coding baseline, >=30% labor reduction target without quality loss; stop/reconsider if no incremental value.
- CC/Codex parallel development, Japanese UI, 1–2 months target, initial JPY 10k incremental cash cap.
- POC first, then discuss with future executive; no claim of his endorsement.

## ADRs pending phase-0 decision
ADR-001 workflow engine/library and licensing.
ADR-002 model provider, pricing, data handling and reproducibility.
ADR-003 Japanese PDF/OCR parsing solution and fallback.
ADR-004 database/storage and migrations.
ADR-005 MCP SDK and adapter contract mapping.
ADR-006 auth for POC and secret management.
ADR-007 quality numeric thresholds and holdout split.
ADR-008 baseline experiment execution order.

## Risk register
R1 Factory duplicates existing tools -> compare vs AI Coding + component repo; pivot if no added value.
R2 Document-heavy scenarios overstate generality -> report scope explicitly; defer cross-domain claim.
R3 Parallel agents introduce conflicts -> separate file ownership, frozen contracts, branch-based integration.
R4 AI output false certainty -> evidence + human review + severity gates.
R5 Unknown future group AI base APIs -> adapter ports only; no fake real integration.
R6 Cost/time overrun -> weekly gates, stop rule, budget ledger, cut noncore UI/features first.
R7 IP/employment conflict -> authorization before using employer assets; synthetic-only default.
R8 Evaluation contamination/learning effect -> frozen holdout, reproducible manifests, honest limitations.
R9 Prompt injection in documents -> treat document text as data, tool allowlists, no external side effects.
R10 UI polished but backend mocked -> trace-linked real execution required to pass gate.

## Change control
Any scope expansion requires change request: business rationale, impact on schedule/budget, acceptance and owner. No silent change to frozen contract, gold holdout or success threshold.
