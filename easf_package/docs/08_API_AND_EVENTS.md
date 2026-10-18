# 08 — API Surface and Event Contract (Proposed)

## REST endpoints (versioned `/api/v1`)
- POST/GET `/projects`; GET `/projects/{project_id}`.
- POST `/projects/{project_id}/requirements`; POST `/requirements/{revision_id}/approve`.
- POST/GET `/capabilities`; GET `/capabilities/{id}/versions/{version}`; POST `/capabilities/validate`.
- POST `/solutions`; POST `/solutions/{id}/validate`; POST `/solutions/{id}/approve`.
- POST `/solutions/{id}/runs`; GET `/runs/{run_id}`; GET `/runs/{run_id}/nodes`; GET `/runs/{run_id}/trace`.
- POST `/runs/{run_id}/reviews/{review_id}/decision` (idempotency key required).
- POST `/evaluations`; GET `/evaluations/{id}`.
- GET `/projects/{id}/reuse-evidence`; GET `/reports/{report_id}`.
- GET `/health` and `/ready`.

## General API rules
OpenAPI schema generated from code; request/response examples; consistent error object `{code,message,trace_id,details}`; pagination; timestamps ISO-8601 UTC in API, JST UI; UUID IDs; ETag or optimistic concurrency on solution updates; auth and role checks on every non-health endpoint; safe upload size and MIME controls.

## Events / trace
`project.created`, `requirement.approved`, `capability.registered`, `solution.validated`, `run.started`, `node.started`, `node.completed`, `node.failed`, `review.requested`, `review.completed`, `run.completed`, `evaluation.completed`, `reuse.recorded`. Include `event_id`, `trace_id`, `run_id`, `timestamp`, `actor`, `capability_version_id` when relevant, `status`, `redacted_metadata` and `schema_version`. No full sensitive document payloads in event log.

## Contract verification
Consumer-driven tests between UI/API, executor/adapters, and domain capabilities. Versioned sample payloads in `schemas/` and `examples/`. Breaking changes require explicit version increment and all consumers passing.
