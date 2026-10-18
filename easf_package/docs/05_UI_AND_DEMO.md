# 05 — Japanese UI and Demo Script

## Design language
Professional Japanese enterprise B2B workspace: compact but readable, restrained neutral palette, Ant Design components, accessible contrast, searchable Select, labels placed above fields for density, table sorting/filtering, clear step status and explicit provenance. Avoid flashy dashboard metrics without evidence. Date/yen formatting Japan locale; Japanese business terms reviewed by human.

## Screens
1. `プロジェクト一覧`: scenario, owner, state, updated, evaluation status.
2. `案件概要 / 要件分析`: requirement text, confirmed requirements, AI suggestions, unknowns and risks.
3. `能力カタログ`: capability, immutable version, contract, applicability, evidence, source type (MCP/REST/local).
4. `ソリューション構成`: node graph/list, schema checks, config, version pins, reviewer approval.
5. `実行モニター`: run and node states, elapsed time, redacted traces, mock/real badge.
6. `確認・修正`: document evidence and extracted fields/flags side-by-side, approve/correct/reject.
7. `評価結果`: gold-set metrics, error classes, critical misses, test set version.
8. `再利用実績`: project A/B, reused versions, adaptation work, verified runs and limits.

## First presentation narrative (10–15 min)
0–2 min: business challenge and Factory positioning (not AI Coding wrapper).
2–5 min: invoice scenario, source evidence and human review.
5–8 min: show immutable capability versions and compose contract review scenario with config changes.
8–10 min: run contract review, show evidence and review.
10–12 min: compare traces and actual reused capability versions; changed-requirement test.
12–15 min: measured baseline comparison, costs, risks, business hypothesis and integration boundaries.

## No fake evidence
No simulated 'real' customer logos, fabricated cost savings, fabricated approvals, or fake AI Hub integrations. UI demo may use synthetic data but must clearly label it.
