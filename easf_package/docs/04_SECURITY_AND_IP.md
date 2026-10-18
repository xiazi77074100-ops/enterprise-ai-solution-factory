# 04 — Security, Privacy, Legal/IP Boundary

## Source restrictions
Independent POC must use synthetic/publicly licensed/explicitly authorized data and code. No MCT/SBI proprietary project code, documents, credentials, internal API definitions or client personal information without permission. Verify employment agreement, invention/IP, side-work policy, and use of employer equipment/accounts/work time. Personal subscription does not automatically authorize use of company infrastructure. Preserve source licenses and attribution. Do not impersonate group companies or suggest endorsement.

## Runtime controls
- Require basic authenticated sessions and project roles for POC; prohibit anonymous workflow execution.
- Enforce file type, size, page count, content safety and retention policy; isolate uploads.
- Reject arbitrary user code, shell execution, arbitrary URLs, SSRF/private-network calls, unrestricted MCP tool invocation, and unsafe file paths.
- Use allowlisted connectors and egress, least-privilege secrets, environment-specific configuration, and no secrets in logs.
- Bound timeouts, token/cost budgets, retries, concurrency and output sizes.
- Treat document text and MCP responses as untrusted; never follow embedded instructions that request tool actions, secret disclosure or policy bypass.
- Human review before any external action; in POC no payment execution, legal filing or real posting.
- Store hashed/redacted traces; restrict raw document access; define deletion and cleanup procedures.
- Dependency license, security scan, SBOM where feasible, no known critical unresolved issues at demo gate.

## Evaluation safety
Invoice bank account/amount mismatch => flag review, no silent approval. Contract uncertain or missing clause => state uncertainty with evidence; no unsupported legal opinion. Report false negatives by severity. Ensure human reviewer identity and edits tracked.

## External integration
Real MCP/REST endpoints only with explicit authorization. Distinguish real/mock adapters in reports. Future enterprise gateway/IAM/AI Hub interfaces remain hypotheses; no invented implementation details.

## Sign-off checklist
[ ] ownership/resources confirmed; [ ] data provenance documented; [ ] synthetic fixtures reviewed; [ ] secret scanning; [ ] dependency/license scan; [ ] access control; [ ] log redaction; [ ] egress restrictions; [ ] critical-error safety tests; [ ] external-demo content approval.
