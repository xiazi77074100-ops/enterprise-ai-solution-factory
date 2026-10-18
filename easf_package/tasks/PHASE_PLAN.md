# Phased Execution Plan — NO SKIPPING GATES

## Phase 0 — Architecture and experiment freeze (CC lead, Codex review)
Deliver: `ADR-001..008`, module ownership, contract v1, threat model, fixture plan, baseline protocol, estimates and cost ledger template. Compare at least two workflow approaches and document tradeoffs. Gate G0: human approval, all blocking unknowns resolved, no implementation before approval.

## Phase 1 — Core foundation (CC: backend/catalog; Codex: UI shell and contract tests)
Tasks: repo scaffold, migrations, auth skeleton, capability contract validation, versioned Catalog, project CRUD, OpenAPI, CI. Gate G1a: API contract tests, security basics, real persistence.

## Phase 2 — Workflow and observability (CC: executor; Codex: UI and tests)
Tasks: typed DAG Composer, run state machine, safe adapter interfaces, local capability execution, traces, pause/resume human review, failure recovery. Gate G1b: reproducible end-to-end trace, negative tests, no scenario-specific branching in executor.

## Phase 3 — Invoice POC (CC: reusable components; Codex: independent tests + UI)
Tasks: synthetic invoice fixtures, document parsing, extraction, rules, evidence, human review, structured export. Gate G2: scenario complete with real component execution, gold scoring and error visibility.

## Phase 4 — Contract POC and reuse proof (Codex: domain config/rule pack; CC: integration/reuse registry)
Tasks: reuse SAME immutable capability versions, distinct contract rules, evidence citations, reviewer report; record adaptation hours and version-pinned runs. Changed-requirement experiment. Gate G3: no copied hardcoded pipeline; reuse and regression evidence.

## Phase 5 — Evaluation, security and baseline (Codex: baseline experiment; CC: Factory evaluation; independent cross-review)
Tasks: frozen holdout, severity tests, prompt injection/SSRF/secret tests, baseline and Factory work logs, cost comparison, limitations. Gate G4: quality and safety; G5: honest >=30% test outcome or pivot recommendation. Avoid contamination: separate branches/repos and agents' context.

## Phase 6 — Demo and business evidence (CC: packaging; Codex: independent audit)
Tasks: Japanese demo, runbook, architecture, test results, reuse evidence, cost ledger, executive 10–15 minute narrative, caveats and group integration hypotheses. Gate: reproducible from clean environment, no fake metrics, explicit human approval before external sharing.

## Scheduling guidance
Target 8 weeks, adjust to measured progress. Parallelize only independent files/tasks; interface contracts and DB migrations single-owner. Do not assume parallel AI agents remove review/integration labor. Weekly review of budget (JPY 10,000 initial incremental cap) and scope.

## Gate template
Each gate report must include commit SHA, changes, commands executed, pass/fail, screenshots where applicable, dataset manifest SHA, security notes, labor/cost log, unresolved risks, and human approval checkbox. Failed gates block next phase.
