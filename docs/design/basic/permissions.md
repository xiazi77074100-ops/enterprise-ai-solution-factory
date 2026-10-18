# 基本設計：権限表

| 版 | 日付 | 変更内容 | 作成者 |
|---|---|---|---|
| 0.1 | 2026-10-18 | 初版（RV-G0-003） | Claude Code |

正本は `contracts/openapi.yaml` の各操作の `x-easf-roles`。この表はそれを人が読む形にしたもの（`spec-sync`）。認可のテストは OpenAPI の `x-easf-roles` から期待値表を作り、全操作 × 全ロールで確かめる。

## 1. ロールの種類

| 値 | 意味 |
|---|---|
| `public` | 認証不要（健康確認・ログインだけ） |
| `any_authenticated` | ログインしていれば誰でも（一覧は自分が見えるものだけに絞る） |
| `project_member` | 対象の案件のメンバー（ロールは問わない）。メンバーでなければ 404 |
| `solution_lead`・`solution_architect`・`qa_evaluator`・`business_reviewer` | 対象の案件で、そのロールを持つメンバー。メンバーでなければ 404、ロールが違えば 403 |
| `admin` | 全体の管理者（案件に属さなくてよい）。業務の承認・確認の決定はできない |

- 案件に属さない操作（Capability・Rule pack の登録）の `solution_architect` は「どれかの案件でそのロールを持つ人」。
- 利用者の作成・無効化は API にせず、管理用の CLI（`python -m app.admin`）で行う（RV-G0-006、ADR-006）。
- 案件を作った人は、その案件の `solution_lead` メンバーになる（`admin` が作った場合も同じ。最初の案件はこの方法で作る）。メンバーの登録・変更は `putProjectMembers`（自分の `solution_lead` は外せない）。
- 要件の版の自己承認の禁止は DB の制約（`ck_requirement_no_self_approval`）でも守る（保険的対策）。

## 2. 追加の規則（ロール以外）

| 操作 | 規則 |
|---|---|
| `approveSolution` | 作成者本人は承認できない（403） |
| `approveRequirementRevision` | 作成者本人は承認できない（403） |
| `decideReviewTask` | 割り当てられた確認者だけ。決定済みは 409、同じ冪等キーは最初の結果を返す |
| `login` | CSRF トークンは無いが `Origin` の照合は必須（ログイン CSRF 対策） |
| 状態を変える全操作 | `X-CSRF-Token` と `Origin` の照合 |

## 3. 操作ごとの許可

| operationId | 許可 |
|---|---|
| getHealth・getReady・login | public |
| getSession・logout・listProjects・listCapabilities・getCapabilityVersion・listRulePacks・getRulePackVersion・getReuseSummary・listLlmProfiles | any_authenticated |
| createProject | solution_lead・admin |
| getProject・listRequirementRevisions・listDocuments・downloadDocument・getSolution・listSolutions・listRuns・getRun・listNodeRuns・getRunTrace・getReviewTask・getEvaluation・listEvaluations・getProjectReuseEvidence・getProjectMembers | project_member |
| createRequirementRevision | solution_lead・solution_architect |
| approveRequirementRevision | solution_lead |
| uploadDocument | solution_lead・solution_architect・qa_evaluator |
| registerCapabilityVersion・validateCapabilityContract・registerRulePackVersion | solution_architect・admin |
| createSolution・updateSolutionDraft・validateSolution | solution_architect |
| approveSolution | solution_lead |
| startRun | solution_lead・solution_architect・qa_evaluator |
| exportRunResult | solution_lead・qa_evaluator・business_reviewer |
| listReviewTasks | solution_lead・business_reviewer |
| decideReviewTask | business_reviewer |
| listDatasetVersions | solution_lead・qa_evaluator |
| startEvaluation | qa_evaluator |
| createReuseRecord | solution_lead・qa_evaluator |
| putProjectMembers | solution_lead |
