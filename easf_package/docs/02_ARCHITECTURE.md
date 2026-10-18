# 02 — System Architecture Design (SAD)

## Architecture style
Modular monolith for POC. React/TypeScript/Vite/Ant Design client; FastAPI Python server; PostgreSQL metadata; local or S3-compatible file storage; asynchronous worker only if needed; Docker Compose. Exact engines/libraries are **proposals pending ADR**. No distributed microservices.

## Modules / ownership
1. `project`: project, requirement versions, solution lifecycle.
2. `catalog`: capability ID/version metadata, contract validation, compatibility, provenance.
3. `composer`: typed workflow DAG, configuration, compatibility checks, version pinning.
4. `executor`: graph traversal, typed data, status, retries/timeouts, pause/resume human review.
5. `adapters`: local/REST/MCP Tool/LLM adapters, bounded capabilities and allowlists.
6. `domain`: six reusable document capabilities, rule packs and evidence locators.
7. `evaluation`: dataset registry, gold labels, scoring, severity and report.
8. `observability`: run/node traces, cost and error records, redaction.
9. `reuse`: project-to-capability-version usage, adaptation effort and evidence.
10. `api/ui`: Japanese user journeys and access control.

## Key rule: Factory is NOT the Agent runtime
It composes and validates a small DAG using stable capability contracts. External Agent Runtime, model gateway, IAM, and upstream requirements Agent are replaceable adapters, not dependencies on proprietary APIs. A mock adapter must be labeled MOCK in UI and reports; mock execution cannot count as real external integration.

## Core entities
Project(id, owner, domain, created_at); RequirementRevision(id, project_id, content, approved_by); Solution(id, project_id, revision, state, workflow_hash); Capability(id, owner, category); CapabilityVersion(id, capability_id, semver, contract, provenance, immutable); WorkflowNode(id, solution_id, capability_version_id, config_hash); WorkflowRun(id, solution_id, input_hash, status, started_at, finished_at); NodeRun(id, workflow_run_id, node_id, status, input_ref, output_ref, duration_ms, cost); ReviewTask(id, run_id, status, reviewer, decisions); DatasetVersion(id, scenario, manifest_hash, split, frozen); EvaluationRun(id, run_id, dataset_version_id, metrics, critical_failures); ReuseRecord(id, project_id, capability_version_id, reuse_kind, adaptation_hours, evidence_run_id).

## Contract invariants
- CapabilityVersion immutable; modifications require a new version.
- All workflow nodes pin a specific capability version.
- Input/output JSON schemas validated at registration, composition, and execution.
- No 'success' state when required node is failed, review pending, or critical guard fails.
- Source evidence refers to immutable document id, page/section, span and text hash; missing provenance is reported, never invented.
- Replay must specify solution hash, dataset version, model/provider version where available, seed if supported; non-deterministic outcomes acknowledged.
- Cost ledger distinguishes model API, infrastructure, developer labor, Factory construction, and experiment setup.

## Workflow execution
Validate graph -> resolve pinned versions -> validate input -> create run/trace -> execute ready nodes -> validate output -> record artifacts -> if review node, pause until approved -> continue -> compute result -> evaluate separately -> export. Retries only on safe/idempotent operations; enforce max retries, timeouts, and run budget. Avoid unsafe dynamic Python eval, unrestricted shell and user-uploaded executable code.

## Suggested module interfaces (language-neutral)
- `Catalog.register(contract, implementation_ref) -> capability_version`
- `Catalog.resolve(capability_id, version) -> contract`
- `Composer.validate(workflow) -> errors/warnings`
- `Executor.start(solution_id, input_refs) -> run_id`
- `Executor.resume(run_id, review_decision) -> state`
- `Evaluator.score(run_id, gold_dataset_version) -> evaluation_id`
- `Reuse.record(run_id, capability_version_id, adaptation_kind, effort) -> evidence_id`

## UI
Routes: `/projects`, `/projects/:id`, `/catalog`, `/solutions/:id/builder`, `/runs/:id`, `/evaluations/:id`, `/reuse`, `/settings`. Japanese labels, compact professional layout, searchable selects, clear review states and error messages. No cosmetic fake charts or fake production metrics.

## Decisions to verify in phase 0
Workflow engine candidate comparison (lightweight own DAG vs maintained library), MCP SDK/license, file parser choice and Japanese OCR limits, local model/remote LLM provider, object storage option, cost telemetry, database migration tool. Use ADR and license/security checks before adoption.

## Future-proofing
Adapter ports for enterprise IAM, model gateway, MCP registry, external Agent Runtime and upstream engineering Agent. Do not implement unsupported real SBI/AI Hub endpoints or assume access.
