# 03 — Acceptance Criteria & Experiment Protocol

## Gates
G0: scope, architecture ADR, security/IP clearance, schemas and baseline protocol approved; no coding before this gate.
G1: real Catalog/Composer/Executor, version-pinned run and trace, contract tests green.
G2: invoice scenario runs with review and gold evaluation.
G3: contract scenario runs using same capability versions; reuse evidence and changed-requirement regression recorded.
G4: independent frozen tests and safety gates pass, reproducible report generated.
G5: baseline vs Factory comparison and business presentation evidence; limitations disclosed.

## Functional acceptance IDs
AC-01 project/requirement versions and explicit approval.
AC-02 catalog supports versioned immutable contracts, applicability and search.
AC-03 workflow graph is configured, validated and executed (not hardcoded scenario switch).
AC-04 same capability version invoked in both scenario projects, supported by trace IDs.
AC-05 invoice: parse/extract/validate/review/export.
AC-06 contract: parse/extract/rule-check/evidence/review/report.
AC-07 review correction is persisted and visible in result and trace.
AC-08 evaluation references frozen dataset version and gold labels; detailed errors reported.
AC-09 critical errors flagged, not silently accepted; fail closed where appropriate.
AC-10 changed requirement can be addressed through configuration/adapter with regression proof.
AC-11 reuse report distinguishes unchanged, config-only, adapter modification and new code.
AC-12 Japanese UI complete for core flows and failures.
AC-13 real vs mock execution visually and programmatically distinguishable.
AC-14 security, permission and data retention checks pass.

## Quality evaluation (proposed gates to freeze before holdout)
For each scenario >=30–50 synthetic labeled documents with train/dev/holdout split. Recommend >=10 holdout documents per scenario as a minimum POC sanity check, not a statistically strong claim. Stratify normal, missing, ambiguous, contradiction, layout/noise and adversarial text. Do not tune on holdout; freeze hashes before implementation tuning.
- Extraction: per-field exact/normalized match, macro averages, critical-field miss rates; retain confusion examples.
- Rule checking: precision, recall and severity-weighted false negatives; each finding must reference explicit rule ID.
- Evidence: correct source page/span, verifiable text hash; missing evidence explicitly 'unverified'.
- Review: state transitions, reviewer corrections and audit completeness.
- Reliability: malformed files, timeout, provider failure, rate limit, replay and safe retry tests.
- Safety: no silent acceptance of critical invoice amount/bank details or critical contract risk flags. Unknown/low confidence escalates to human review. No fabricated legal certainty.
- Numerical acceptance thresholds other than 'no silent critical errors' MUST be signed off in G0, before seeing holdout results; avoid claiming universal 90% accuracy.

## Fair comparison protocol
Compare: (A) expert Claude Code/Codex + conventional organized repo and reusable open-source libs, no Factory-specific catalog/evidence tooling; (B) same tools and developer skill plus Factory. Identical frozen requirements, acceptance criteria, test data, environment, model budget policy. Record total human minutes for analysis, prompting, code review, debugging, test design, integration, QA, reporting; AI API/tool fees; wall-clock separately. Avoid giving Factory arm access to gold holdout. Counterbalance order where practical, or use a second blinded evaluator; if impossible explicitly report learning effect and limited sample size. Compare second-project marginal labor and separately total program cost (Factory build + maintenance + all project costs). Include setup, integration and adapter work; no free uncounted labor.

## Success interpretation
Primary target: >=30% lower comparable second-project total human labor **and** non-inferior quality with critical safety gates satisfied. Report absolute hours, uncertainty, and scenario limitations. Calculate breakeven projects = ceil((Factory build + maintenance incremental costs)/(per-project avoided costs)) only if denominator positive and assumptions justified. If no meaningful gain, choose component library + delivery playbook rather than platform escalation. Even technical success does not prove group sales adoption.

## Required evidence artifacts
`reports/gate_G*.md`, `reports/test_manifest.json`, `reports/evaluation_invoice.json`, `reports/evaluation_contract.json`, `reports/reuse_evidence.csv`, `reports/baseline_comparison.csv`, `reports/cost_ledger.csv`, `reports/security_review.md`, `reports/limitations.md`, `reports/demo_script.md`. Generate only after actual execution, include commands, timestamps and commit SHA.
