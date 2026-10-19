# 基本設計：画面一覧・画面遷移

| 版 | 日付 | 変更内容 | 作成者 |
|---|---|---|---|
| 0.1 | 2026-10-18 | 初版（P1-03：ログイン・プロジェクト・能力カタログ） | Claude Code |
| 0.2 | 2026-10-18 | 解決策・実行・確認の画面（P2-03） | Claude Code |
| 0.3 | 2026-10-19 | 文書の一覧・登録・ダウンロード、実行の文書の入力、結果の出力（P3-01d） | Claude Code |

画面の規約は `ui-design` skill。全体の画面構成は `easf_package/docs/05_UI_AND_DEMO.md`。この表は **実装済みの画面だけ** を書く。

## 1. 画面一覧

| 画面 | パス | 使う API（operationId） | 主な操作 | 権限 |
|---|---|---|---|---|
| ログイン | `/login` | login・getSession | ログイン（入力が正しくなるまで押せない） | 公開 |
| プロジェクト一覧 | `/projects` | listProjects・createProject | 検索・並び替え・ページ送り・新規作成（ダイアログ） | ログイン済み（一覧は参加している案件だけ）。作成は admin か solution_lead |
| プロジェクト詳細 | `/projects/:projectId` | getProject・getProjectMembers・listRequirementRevisions・createRequirementRevision・approveRequirementRevision | 要件の版の登録・承認（確認ダイアログ）・メンバーの表示 | project_member。登録は solution_lead・solution_architect、承認は solution_lead（作成者以外） |
| プロジェクト詳細（文書） | `/projects/:projectId` の「文書」 | listDocuments・uploadDocument・downloadDocument | ファイル名（合成データのバッジ・SHA-256 の先頭 12 桁）・形式・ページ・大きさ・登録日時、ページ送り。登録（ファイルを選ぶダイアログ）、ダウンロード（ブラウザのダウンロード） | 一覧・ダウンロードは project_member。登録は solution_lead・solution_architect・qa_evaluator |
| プロジェクト詳細（解決策） | `/projects/:projectId` の「解決策」 | listSolutions・validateSolution・approveSolution・startRun | 検証（下書き）・承認（確認ダイアログ）・実行（入力のダイアログ → 確認ダイアログ。冪等キーはダイアログごとに 1 つ） | 一覧は project_member。検証は solution_architect、承認は solution_lead（作成者以外）、実行は solution_lead・solution_architect・qa_evaluator |
| プロジェクト詳細（実行） | `/projects/:projectId` の「実行」 | listRuns | 実行番号・状態・方式（実行／模擬（MOCK）／一部模擬（MOCK））・開始・終了、ページ送り | project_member |
| 実行の詳細（実行モニター） | `/runs/:runId` | getRun・listNodeRuns・getRunTrace・listReviewTasks・exportRunResult | 受付・実行中の間は 3 秒ごとに自動更新。処理ごとの状態・方式・試行・時間・結果（値は出さず件数だけ）、失敗の理由、確認待ちの案内と確認画面への導線、記録（トレース）のページ送り。成功し出力のノードがある実行は「CSV で出力」「JSON で出力」 | project_member（確認画面への導線は確認タスクを一覧できる人だけ。出力は solution_lead・qa_evaluator・business_reviewer、ほかはサーバが 403） |
| 確認タスク | `/reviews` | listReviewTasks | 自分に割り当てられた確認（確認待ち／決定済み）、ページ送り | どれかの案件で solution_lead か business_reviewer（ほかは案内を表示） |
| 確認 | `/runs/:runId/reviews/:reviewId` | getReviewTask・decideReviewTask | 項目ごとに確認前の値・出所（AI 下書き／抽出）・根拠（照合済み／未確認）・確認後の値、ルールの判定（該当あり／該当なし／不明・rule_id・重大度）。承認（修正なしのとき）・修正して承認（修正 1 件以上）・却下（コメントありのとき）、いずれも確認ダイアログ | 決定は割り当てられた business_reviewer だけ。ほかのメンバーは閲覧のみ |
| 能力カタログ | `/catalog` | listCapabilities | 検索・接続方式で絞り込み・ページ送り | ログイン済み |
| 能力の版の詳細 | `/catalog/:capabilityId/:version` | getCapabilityVersion | 概要・入出力・設定の契約（JSON をテキストで表示） | ログイン済み |

共通：ヘッダに「検証用（本番利用不可）」、ログアウト。API の待ちは画面上端の線、結果は画面中央の通知（成功は 4 秒で閉じる、失敗は閉じない・trace_id を表示）。

## 2. 入力チェック（画面とサーバで同じ条件）

| 画面 | 項目 | チェック | 文言 |
|---|---|---|---|
| ログイン | ユーザー ID | 必須、64 文字以内 | ユーザー IDを入力してください。／ユーザー IDは64文字以内で入力してください。 |
| ログイン | パスワード | 必須、128 文字以内 | パスワードを入力してください。 |
| プロジェクトの作成 | プロジェクト名 | 必須、100 文字以内 | プロジェクト名を入力してください。 |
| プロジェクトの作成 | 業務区分 | 必須、50 文字以内 | 業務区分を入力してください。 |
| プロジェクトの作成 | 説明 | 1000 文字以内 | 説明は1000文字以内で入力してください。 |
| 要件の版 | 新しい要件 | 必須、20000 文字以内 | 要件を入力してください。 |

ログインに失敗したときの文言は 1 種類（「ユーザー ID またはパスワードが正しくありません。」、サーバの文言）。

| 画面 | 項目 | チェック | 文言 |
|---|---|---|---|
| 解決策の実行 | 文字列の入力 | 必須、10000 文字以内 | 入力「{名前}」を入力してください。 |
| 解決策の実行 | 整数の入力 | 必須、整数 | 入力「{名前}」の形式が正しくありません（例：120）。 |
| 解決策の実行 | 文書の入力 | 必須。案件の文書から選ぶ（新しい順に 200 件まで） | 入力「{名前}」の文書を選択してください。 |
| 文書の登録 | ファイル | 必須。拡張子が pdf・png・jpg・jpeg、空でない、10 MB 以内（サーバは先頭のバイト・ページ数・暗号化なども確かめる。`docs/design/detail/documents.md` §2） | ファイルを選択してください。／PDF・PNG・JPEG のファイルを選択してください。／ファイルが空です。／ファイルの大きさは 10 MB 以内にしてください。 |
| 確認 | 確認後の値 | 元の値と同じ形式（数値・はい／いいえ） | 元の値と同じ形式で入力してください（数値・はい／いいえ）。 |
| 確認 | コメント | 2000 文字以内。却下のときは必須 | コメントは2000文字以内で入力してください。 |

## 3. 既知の制約（G1a で報告）

- メンバーの編集画面はない（利用者を探す API が契約 v1 にないため。v1.1 で `GET /users?q=` を検討）。
- 能力カタログの接続方式の絞り込みは 1 つだけ（契約 v1 の `kind` が単一の値のため）。`ui-design` の「一覧の絞り込みは MultiSelect」からの逸脱。
- 要件の版の承認ボタンは、自分が作成した版にも表示される（契約 v1 の応答に作成者がないため）。押すとサーバが 403 で止める。
- 処理の流れ（Workflow）の作成・編集の画面はない（API で登録する）。G1b で報告。
- 確認の決定後、修正の内容（修正前後の値）は画面に出ない（契約 v1 の `ReviewTask` に修正の項目がないため）。修正は実行の結果とトレース（項目名とハッシュ）に残る。
- 実行・確認の画面の E2E は API を模擬して確かめる。同じ流れのサーバ側は `backend/tests/integration/test_runs.py`・`test_invoice_workflow.py`（請求書の Workflow を本番の部品で端から端まで）で実際に動かしている。
- 実行の文書の入力は通常の選択（`select`）。案件の文書が 200 件を超えると古いものは選べない（`ui-design` の SearchSelect は未作成）。
