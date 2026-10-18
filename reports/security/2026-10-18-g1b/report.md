# 脆弱性診断報告書（自己診断・G1b 前の再診断）

| 項目 | 内容 |
|---|---|
| 対象 | EASF `abb027e`（main）。前回（`reports/security/2026-10-18/report.md`）からの追加：Solution の API 6、実行の API 5、確認の API 3、Executor（子プロセスでの実行）、実行・確認の画面、見た目の変更（D-026） |
| 環境 | ローカル Docker Compose（`--profile app`）、`EASF_ENV=assessment`、API は 127.0.0.1:8001。Windows 11、Docker Desktop 28.5.1 |
| 期間 | 2026-10-18 23:15 〜 2026-10-19（JST） |
| 実施者 | Claude Code（自己診断。独立診断は未実施、D-024） |
| 基準 | IPA「安全なウェブサイトの作り方」、ウェブ健康診断仕様、OWASP ASVS 4.0.3 L2、OWASP Top 10 for LLM 2025 |
| 評価方法 | CVSS v3.1 基本値 → 高・中・低・情報 |
| 対象外 | ファイルアップロード・文書・出力（exportRunResult）・評価・再利用・実 LLM / MCP / REST の接続（Phase 3 以降）、メール機能（なし）、TLS（ローカル環境）、画面の DAST |

## 1. 総評

高・中・低の新しい指摘は 0 件。追加した 14 操作を含む契約の全 45 操作に対する ZAP（未ログイン・認証付き）は失敗 0、サーバの 500 は 0。SAST・SCA・コンテナ・秘密情報も 0 件（gitleaks の 32 件は前回の報告ファイル内の誤検知で、理由を付けて除外）。Executor の危険な振る舞い（無限ループ・例外・不正な出力・巨大な出力・異常終了・予算超過・二重起動）は自動テストで確認済み。**ゲート条件（高・中 0 件、低は対応済み、SCA の高・重大 0 件、秘密情報 0 件）を満たす。**

## 2. 件数

| 重大度 | 新規 | 対応済み | 受容 | 未対応 |
|---|---|---|---|---|
| 高 | 0 | — | — | — |
| 中 | 0 | — | — | — |
| 低 | 0 | — | — | — |
| 情報 | 3 | — | — | — |

前回の VA-001〜VA-005 はすべて対応済みのまま（再発防止のテストが成功）。

## 3. 実施した検査

| 段 | 道具（版） | 結果ファイル | 結果 |
|---|---|---|---|
| SAST | ruff `--select S`（app） | sast/ruff-s.json | 0 件 |
| SAST | bandit 1.9.4 | sast/bandit.json | 0 件 |
| SAST | semgrep（p/python・p/owasp-top-ten・p/react・p/typescript・p/secrets） | sast/semgrep.json | semgrep 1.180.0、76 ファイル。0 件、エラー 0（1 回目は実行の途中で止まったため再実行） |
| SAST | ESLint（localStorage・dangerouslySetInnerHTML・eval の禁止） | CI | 0 件 |
| SCA | pip-audit 2.10.1 | sca/pip-audit.json | 既知の脆弱性なし |
| SCA | npm audit `--omit=dev` | sca/npm-audit.json | 0 件 |
| ライセンス | package-lock.json | sca/licenses-node-prod.json | 本番依存 38 件。37 件は MIT・ISC・Apache-2.0・BSD、追加した字体 `@fontsource/noto-sans-jp` は OFL-1.1（I-06） |
| 秘密情報 | gitleaks 8.30.1（履歴） | secrets/gitleaks-history.json | 32 件、すべて誤検知（前回コミットした ZAP 報告の URL `http://api:8000/…` の `api:` と、ベースイメージ履歴の公開の GPG 鍵の指紋）。`.gitleaksignore` に指紋と理由を書いて除外し、再実行で 0 件（I-07） |
| コンテナ | trivy 0.76.0 image（Alpine 3.24.2） | container/trivy-image.json | 0 件（全重大度・秘密情報なし） |
| コンテナ | trivy 0.76.0 config（Dockerfile） | container/trivy-config.json | 0 件（27 項目合格） |
| DAST | OWASP ZAP 2.16.1 API スキャン（未ログイン、契約 1.0.2 の全 54 URL） | dast/zap-api.json | 失敗 0・合格 114。警告は「ZAP is Out of Date」のみ（D-023） |
| DAST | OWASP ZAP 2.16.1 API スキャン（認証付き〔admin〕、Cookie・CSRF・Origin を付与、ログアウトを除く） | dast/zap-api-auth.json | 失敗 0・合格 114。サーバのログに 500 なし |
| 手動 | curl（§7） | — | 新しい操作の否定の確認 13 件、すべて拒否（422・404） |
| 全テスト | pytest | — | 137 件成功（P2-04 時点。Executor の敵対的テスト 13 件を含む） |

## 4. 指摘一覧

| ID | 重大度 | 項目 | 状態 |
|---|---|---|---|
| I-01〜I-05 | 情報 | 前回のとおり（ローカルの HTTP、`__Host-` なし、psycopg の LGPL、ZAP の版、健康確認のキャッシュ） | 変わらず |
| I-06 | 情報 | 字体 Noto Sans JP は OFL-1.1（同梱・改変なしで配信。フォントの再配布は OFL で許可） | 一覧に残す |
| I-07 | 情報 | 診断報告のファイルが gitleaks の汎用規則に当たる（誤検知）。報告をコミットするたびに指紋の確認が必要 | 運用（毎回 gitleaks の結果を見る） |
| I-08 | 情報 | 実行・確認の画面の E2E は API を模擬して確かめた（本番で実行できる業務の Capability は Phase 3 から） | 制約として報告 |

## 5. 新しい機能の診断の要点

| 対象 | 確かめたこと | 根拠 |
|---|---|---|
| Solution の API | 一括代入（`state` などの追加）を 422、承認済みは DB トリガーで変更・削除を拒否、自己承認を 403、`If-Match` の不一致を 412 | test_full_lifecycle、test_database_rejects_changes_to_approved_solution、test_update_requires_current_etag_and_returns_to_draft、curl |
| 実行の開始 | 冪等キー（同じ内容は同じ Run、違う内容は 409）、入力は宣言どおりの型だけ（オブジェクト・余分な項目は 422）、実装のない Capability は 409 | test_idempotency_key、test_start_preconditions、test_capability_without_code_cannot_start、curl |
| 任意コード実行（T14） | 実装は許可リストのキーに結び付けた関数だけ。契約の文字列から import しない。許可リストと実装の表の一致をテスト | test_available_keys_match_bound_code、`app/executor/handlers.py` |
| サービス拒否（T12・T13） | 無限ループは時間切れで子プロセスを強制終了、出力は 1 MiB まで、処理時間・トークン・円の予算で失敗、ワーカーは異常終了後も処理を続ける | test_endless_loop_is_killed_at_the_timeout、test_huge_output_is_refused、test_llm_token_budget_fails_the_run、test_timeout_caused_by_the_duration_budget_is_reported_as_budget、test_child_process_exit_is_a_failure |
| 情報漏えい（T09） | 例外のメッセージ（入力値を含む）を返さず型名だけ、トレース・ノードの要約に値を出さない（ハッシュと件数だけ） | test_exception_reports_only_its_type、test_run_pauses_for_review_and_succeeds_with_corrections |
| 確認の横取り（C-03） | 割り当てられた確認者だけが決定、別の確認者・ロールなしは 403、案件外・別の実行の確認は 404、決定済みは 409、同じ冪等キーは同じ結果 | test_review_decision_rules、test_review_of_another_run_is_not_found |
| 状態の飛ばし（C-04・T06・H-01） | 確認待ち・却下・失敗の Run は成功にならない。却下で以降のノードは skipped、出力なし | test_rejected_review_stops_the_run、test_no_reviewer_fails_the_run |
| 改ざん・否認（T05・T07・H-03） | トレースは追記だけ（DB トリガー）、ハッシュ連鎖を検証、修正は確認者・時刻・項目名・ハッシュを記録 | test_trace_is_append_only、test_run_pauses_for_review_and_succeeds_with_corrections |
| 模擬の区別（G-06・AC-13） | mock の LLM のノードは `mock`、Run は `mixed`。画面は「一部模擬（MOCK）」 | test_mock_llm_node_marks_the_run_mixed、e2e/runs.spec.ts |
| 二重起動（H-04） | 2 つのワーカーが同じ Run を取らない、異常終了で残ったノードは冪等なら再試行 | test_two_workers_never_claim_the_same_run、test_worker_crash_mid_call_is_recovered |

## 6. 受容した指摘

なし。

## 7. 手動診断の結果（今回の差分）

前回 §7 から変わった項目だけを書く。ほかは前回のとおり。

| ID | 結果 | 根拠 |
|---|---|---|
| A-07 | 問題なし | Solution・実行・確認の API に余分な項目（`state`・`status`）を足すと 422（curl） |
| A-10 | 問題なし | 実行の入力にオブジェクト、修正値にオブジェクト、不正な冪等キー・`project_id`・`status` を送ると 422（curl）。ノードの入力の上限超えは invalid_input で失敗 |
| C-03 | 問題なし | §5 の「確認の横取り」 |
| C-04 | 問題なし | §5 の「状態の飛ばし」、承認されていない解決策の実行は 409 |
| C-06 | 問題なし | 実行の一覧・トレース・確認タスクの一覧に他案件が混ざらない（test_isolation_and_review_list_permissions） |
| G-05 | 問題なし | 予算超過は failed（budget_exceeded）、成功にならない |
| G-06 | 問題なし | §5 の「模擬の区別」 |
| H-01 | 一部確認 | 確認なしで成功にならないことは確認。重大項目の判定は Phase 3（ルールの実装後） |
| H-03 | 問題なし | §5 の「改ざん・否認」 |
| H-04 | 一部確認 | 二重起動・再試行は確認。費用の二重計上の確認は実 LLM の利用開始後 |

修正の項目のパスの検査（`/fields/<名前>` 以外を 422）は、curl では確認タスクを用意できなかったため 404 で止まった。自動テスト（test_review_decision_rules の invalid_correction_path）で確認している。

## 8. 制約・注意

- 自己診断であり、第三者診断・独立診断の代わりではない（D-024 で独立レビューは行わないと決定）。
- ZAP は API だけを対象にした。画面の DAST は未実施。
- 実行・確認の流れを ZAP は契約の例の ID でしか叩けない（多くは 404）。状態を持つ流れの確認は自動テストと §5 の根拠による。
- 本番の許可リストで実行できる業務の Capability はまだない（Phase 3）。子プロセスでの実行の安全性は試験用の Capability で確認した。
