# 01 — Product Requirements Document (PRD)

## 1. Product thesis
EASF enables AI consulting/presales/solution delivery teams to turn enterprise needs into demonstrable, evaluated POCs using versioned reusable capabilities. Business objective: lower presales POC cost, increase reusable delivery capacity, and eventually support more group-company AI adoption. Commercial conversion remains unverified.

## 2. Users and roles
- Solution Lead: opens project, accepts business constraints, approves solution and evidence.
- Solution Architect: selects capability versions, configures workflow, reviews contracts and adapters.
- QA/Evaluator: curates gold data, runs eval, reviews critical failures and cost.
- Business Reviewer: confirms invoice or contract findings, records corrections and decisions.
- Administrator (POC only): manages basic users, allowlists, credentials and execution limits.

## 3. Core user journey
Create Project -> input requirements -> AI-assisted analysis (clearly labeled suggestions) -> review recommended capabilities -> compose version-pinned workflow -> validate compatibility -> human approval -> execute on synthetic docs -> human review -> evaluate against frozen gold set -> export result and reuse evidence.

## 4. Functional requirements
- FR-01 Projects: create/list/detail; business domain, owner, requirements, versioned solution configurations.
- FR-02 Requirements: paste text or upload authorized docs; summarize goals, fields, rules, risks, unknowns; require human confirmation.
- FR-03 Catalog: register/list/filter/detail; immutable capability versions; input/output JSON schema; dependencies; applicability; provenance; evaluation profile.
- FR-04 Composer: add nodes and typed edges, pin versions, validate schemas, detect cycles (unless explicit bounded loop support), store configuration snapshot.
- FR-05 Executor: deterministic execution of registered real implementations; per-node status, timeouts, safe retries, failure state, idempotency boundaries; no arbitrary untrusted code execution.
- FR-06 Human Review: pause and resume with reviewer identity, decisions, corrections and timestamps.
- FR-07 Evaluation: compare output to versioned gold set, measure field/rule/evidence/critical misses; reproducible reports.
- FR-08 Trace: trace_id/run_id, input/output hashes or redacted summaries, node version, latency, token/yen cost if available, errors, reviewer action.
- FR-09 Reuse: evidence of same immutable capability version executed in two projects; classify unchanged/config-only/adapter/code modification; record incremental integration hours.
- FR-10 Delivery: Japanese demo workspace, report export with caveats, non-production label.
- FR-11 Adapters: minimum one real MCP Tool invocation, one REST/local capability path if feasible; capability contract stays transport neutral; Resources/Prompts keep MCP semantics.

## 5. Business scenario A: 請求書処理
Upload synthetic Japanese invoice PDF/image -> parse -> extract vendor, invoice number, invoice date, due date, amount, tax, qualified invoice registration number, bank destination -> validate totals, missing fields, account/amount anomalies using explicit rules -> show source evidence -> reviewer approve/correct -> structured JSON/CSV export. No actual transfer, accounting posting, or bank file production requirement.

## 6. Business scenario B: 契約書レビュー
Upload synthetic Japanese contract -> parse -> extract parties, term, renewal, liability cap, confidentiality, termination -> check against pre-defined policy rules -> cite source passages/page -> human approve/correct -> review report. Must distinguish 'missing', 'uncertain', and 'present'; no definitive legal advice.

## 7. Shared capability candidates
DocumentParser, StructuredExtractor, RuleValidator, EvidenceLocator, HumanReview, ResultExporter. The *same version* should be callable from both projects with distinct configs/rule packs. Platform services Catalog, Composer, Executor, Evaluator, Trace and Reuse Tracker are separate from the six domain capabilities.

## 8. Non-goals
Production multi-tenancy, payment execution, real banking integration, legal opinion issuance, fully autonomous code generation, group identity platform, production-grade marketplace, billing, complete Agent runtime, enterprise-wide deployment, integration to undocumented SBI AI Hub.

## 9. Outcomes and limits
Target >=30% reduction in comparable second-project total labor with no quality degradation, versus expert AI Coding baseline. Do not equate target with evidence. Demonstrate two real business POCs, reusable versions, evaluation, traces, cost and caveats. Document that two document-heavy scenarios do not establish generality for non-document use cases.

## 10. Constraints
1–2 calendar months, parallel CC/Codex, JPY 10,000 initial incremental cash cap, Japanese UI. Human review and legal/security/IP clearance before external presentation.
