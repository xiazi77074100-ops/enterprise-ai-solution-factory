# COPY TO EITHER CC OR CODEX — INDEPENDENT GATE REVIEW

Act as an adversarial independent architecture/security/QA reviewer of the current EASF phase. Read the entire spec kit and current code/diffs. Do not assume the implementing agent is correct.

1. Identify current phase and gate; enumerate its acceptance IDs and concrete evidence paths.
2. Run feasible build, lint, typecheck, unit, integration, security and contract tests. Report actual commands, output and environment limitations; do not claim a pass when unexecuted.
3. Inspect whether core engine is generic and truly executes registered immutable versions; detect scenario-specific hardcoding, mock-as-real behavior, schema bypass, untraceable evidence or silent critical failures.
4. Check uploaded document prompt-injection, SSRF, secrets, arbitrary execution, auth, logs, retention and licensing.
5. Check evaluation leakage, dataset freeze, baseline fairness, cost and human time accounting.
6. List BLOCKER / MAJOR / MINOR findings with exact file/line, repro steps, fix suggestion and retest criteria.
7. Produce a GATE REPORT with PASS / FAIL / BLOCKED, never fabricate results. If evidence missing, mark BLOCKED. Do not advance without human approval.
