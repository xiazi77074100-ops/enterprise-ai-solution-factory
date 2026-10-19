# 基本設計：権限表

| 版 | 日付 | 変更内容 | 作成者 |
|---|---|---|---|
| 0.1 | 2026-10-18 | 初版（RV-G0-003） | Claude Code |
| 0.2 | 2026-10-18 | 解決策の承認の条件、ロールで制限する操作の 403（契約 1.0.2、D-025） | Claude Code |
| 0.3 | 2026-10-18 | 実行の開始・確認の一覧・確認の決定の規則（P2-02） | Claude Code |
| 0.4 | 2026-10-19 | 文書の登録・ダウンロードの規則、`startRun` の文書の入力（P3-01a） | Claude Code |

正本は `contracts/openapi.yaml` の各操作の `x-easf-roles`。この表はそれを人が読む形にしたもの（`spec-sync`）。認可のテストは OpenAPI の `x-easf-roles` から期待値表を作り、全操作 × 全ロールで確かめる（`backend/tests/contract/test_openapi_contract.py`：未ログイン 401、非メンバー 404〔案件に属する操作〕／403〔全体の操作〕、ロールのないメンバー 403、ロールのあるメンバーは成功。全応答を契約の応答スキーマで検証）。

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
| `approveSolution` | 作成者本人は承認できない（403）。検証に合格した（`validated`）解決策で、要件の版が承認済みのときだけ（それ以外は 409） |
| `updateSolutionDraft` | `If-Match` が最新の ETag と一致（違えば 412）。承認済みは 409 |
| ロールで制限する全操作 | ロールのないメンバー・利用者には 403（契約 1.0.2 で宣言をそろえ、契約テストで全件を確認） |
| `approveRequirementRevision` | 作成者本人は承認できない（403） |
| `decideReviewTask` | 割り当てられた確認者だけ（ほかの確認者・ロールのない人は 403、案件外は 404）。決定済みは 409、同じ冪等キーと同じ内容は最初の結果を返す。修正は `/fields/<名前>` だけ（ほかは 422） |
| `startRun` | 解決策が承認済み（`requires_human_approval: false` なら検証済みでも可）。実装のない Capability を含むと 409。同じ利用者・同じ冪等キーは最初の Run を返し、内容が違えば 409。`document_ref` の入力は同じ案件の文書だけ（他の案件の文書は無い文書と同じ 422） |
| `uploadDocument` | 形式・大きさ・ページ数・ファイル名のチェックは `docs/design/detail/documents.md` §2 |
| `downloadDocument` | 文書の案件のメンバーだけ（それ以外は文書が無いときと同じ 404） |
| `listReviewTasks` | どれかの案件で solution_lead か business_reviewer でなければ 403。`assigned_to_me=false` のときは、そのロールを持つ案件の確認タスク |
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
