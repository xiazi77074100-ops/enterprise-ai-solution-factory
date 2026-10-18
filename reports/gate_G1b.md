# ゲート報告 G1b（Phase 2）

| 項目 | 内容 |
|---|---|
| コミット | abb027e（main。本報告・診断・証跡のコミットはこの次） |
| 作成日 | 2026-10-19 |
| 作成 | Claude Code（統合責任者） |
| 判定（自己） | **PASS（人の承認待ち）**。独立レビューはなし（D-024 により自己レビュー）。業務の Capability は Phase 3 のため、端から端までの確認は試験用の Capability と本物の人の確認で行った（§2） |
| 人の承認 | [x] 承認　承認者：プロジェクト責任者　日付：2026-10-19（D-027） |

G1b の条件（`easf_package/tasks/PHASE_PLAN.md`）：**再現できる端から端までのトレース、否定テスト、Executor に業務ごとの分岐がないこと。**

## 1. 成果物

| タスク | 内容 | 証跡 | コミット | 状態 |
|---|---|---|---|---|
| P2-00 | Phase 2 計画、詳細設計（状態機械・実行の流れ・確認・トレース・表）、テスト専用 DB（`easf_test`。`_test` 以外の DB 名ではテストが止まる） | `docs/phase2/PHASE2_PLAN.md`、`docs/design/detail/run_execution.md` | 82a379c | 完了 |
| P2-01 | Composer（Workflow の静的検証 13 種）と Solution の API 6 操作（ETag・承認・DB トリガーで凍結）。契約 1.0.2（D-025） | `backend/app/composer/`、`backend/app/api/solutions.py` | 0ff8b19 | 完了 |
| P2-02 | Executor（状態機械・DB をキューにしたワーカー・再試行・予算・異常終了からの回復）、アダプタ（local は子プロセス、LLM は mock だけ）、人の確認、ハッシュ連鎖のトレース、実行・確認の API 8 操作 | `backend/app/executor/`、`backend/app/adapters/`、`backend/app/api/runs.py` | 36a8912 | 完了 |
| P2-04 | Executor の敵対的テスト 13 件 | `backend/tests/integration/test_executor_adversarial.py` | 88061ae | 完了 |
| P2-03 | 解決策・実行・確認の画面（実行モニター・確認タスク・修正して承認） | `frontend/src/features/{solutions,runs,reviews}/` | 4a7e9ab | 完了 |
| — | 画面の見た目を sales-assistant の UI に合わせる（D-026） | `frontend/src/styles/theme.css` ほか | abb027e | 完了 |
| — | G1b 前の脆弱性の再診断 | `reports/security/2026-10-18-g1b/report.md` | 本報告のコミット | 完了 |

## 2. 受入条件

| 条件 | 確かめ方 | 結果 | 証跡 |
|---|---|---|---|
| G1b：端から端までのトレース | 試験用の Capability（テストの中だけで登録・実装を結び付ける。本番の許可リストには入れない）と本物の `review.human` の Workflow を、検証 → 承認 → 実行 → 確認で一時停止 → 修正して承認 → 再開 → 成功まで、実 PostgreSQL・実ワーカーで流す。イベントの並び・ハッシュ連鎖・修正の記録を確認 | 成功 | test_run_pauses_for_review_and_succeeds_with_corrections |
| G1b：再現できる | 同じ入力で 2 回実行し、入力のハッシュ・各ノードの入出力のハッシュ・イベントの並びが一致 | 一致 | test_same_input_reproduces_hashes_and_trace |
| G1b：否定テスト | 却下・確認者なし・予算超過・入力違反・時間切れ・例外・不正な出力・巨大な出力・異常終了・二重起動・確認の横取り・別の実行の確認・冪等キーの衝突・承認されていない解決策 | すべて成功にならない（正しい状態で止まる）か、正しく再試行 | `test_runs.py`（13）、`test_executor_adversarial.py`（13） |
| G1b：業務ごとの分岐がない | `backend/app/{composer,executor,adapters}` に業務名（請求書・契約書など）がないことを検査。Executor の振る舞いは Workflow と契約のデータだけで決まる | 検出なし | `scripts/validate_contracts.py`（CI）。確認項目の作り方も業務を知らない一定の規則（`review_items`） |
| AC-03（基盤） | Workflow の構成・検証・実行（業務の分岐でなくデータ） | 成功（見本の Workflow 2 件は検証に合格。実行は Phase 3 の Capability の実装後） | test_example_workflows_are_valid、test_mistakes_are_reported |
| AC-07（基盤） | 確認の修正が結果とトレースの両方に残る（修正者・時刻・項目名・ハッシュ） | 成功 | test_run_pauses_for_review_and_succeeds_with_corrections |
| AC-09（基盤） | 失敗・却下・確認待ち・予算超過を成功にしない | 成功 | §2 の否定テスト |
| AC-13 | 実行と模擬の区別（API の execution_mode、画面のバッジ） | 成功（mock の LLM のノードは `mock`、Run は `mixed`、画面は「一部模擬（MOCK）」） | test_mock_llm_node_marks_the_run_mixed、e2e/runs.spec.ts |
| AC-12（一部） | 日本語 UI（解決策・実行・確認）、1440px・390px、横スクロールなし、コンソールエラーなし | 成功（API を模擬した E2E と、実バックエンドの既存の流れ） | `reports/gate_G1b_screens/` |

## 3. 実行したコマンドと結果

2026-10-19、main の abb027e（作業ツリーは同じ）で実行。ログは `reports/gate_G1b_logs/`。

| コマンド | 終了コード | 結果の要点 | ログ |
|---|---|---|---|
| `python scripts/validate_contracts.py` | 0 | schemas=5 capabilities=6 rule_packs=2 workflows=2 openapi=valid。業務名の検査も合格 | validate_contracts.log |
| `python scripts/sync_skills.py --check` | 0 | ずれなし | sync_skills.log |
| `uv run ruff check .` / `ruff format --check .` | 0 / 0 | 問題なし / 69 ファイル整形済み | ruff.log、ruff_format.log |
| `uv run mypy app tests` | 0 | 63 ファイル問題なし（strict） | mypy.log |
| `uv run bandit -q -r app` | 0 | 検出なし | bandit.log |
| `uv run pip-audit` | 0 | 既知の脆弱性なし | pip_audit.log |
| `uv run pytest -q`（実 PostgreSQL、`easf_test`） | 0 | **137 passed**（7 分 40 秒） | pytest.log |
| `npm audit --omit=dev` | 0 | 0 件 | npm_audit.log |
| `npm run lint` / `npm run typecheck` | 0 / 0 | 警告 0 / 型エラー 0 | lint.log、typecheck.log |
| `npm test`（vitest） | 0 | **6 passed** | vitest.log |
| `npm run build` | 0 | 成功、ソースマップ 0 件 | build.log |
| `npx playwright test`（1440px・390px） | 0 | **4 passed**（模擬 API の解決策 → 実行 → 確認、実バックエンドのログイン → 案件 → 要件 → カタログ） | playwright.log、画面は `reports/gate_G1b_screens/` |
| GitHub Actions（ci） | 成功 | Phase 2 の全 6 コミット（82a379c・0ff8b19・36a8912・88061ae・4a7e9ab・abb027e）で成功。各タスクは CI の成功を確かめてから main に入れた（G1a §8-2 の対策） | GitHub の Actions 画面 |

未実行：独立レビュー（D-024）。画面の DAST。

## 4. 試験成績

| 区分 | 件数 | 成功 | 失敗 | 主な観点 |
|---|---|---|---|---|
| バックエンド 単体（tests/unit） | 31 | 31 | 0 | ヘッダ・エラー、Composer の検査 19、許可リストと実装の一致 |
| バックエンド 結合（tests/integration、実 DB） | 64 | 64 | 0 | 認証・案件・Catalog に加え、Solution 5、実行 13、Executor の敵対的 13 |
| バックエンド 契約（tests/contract） | 36 | 36 | 0 | 実装と契約の一致、実装済み 34 操作の認可の全件表、応答スキーマ、ロールで制限する操作の 403 の宣言 |
| バックエンド 診断の再発防止（tests/security） | 6 | 6 | 0 | VA-001・VA-003〜VA-005 |
| 画面 単体（vitest） | 6 | 6 | 0 | API クライアント、フォームの約束 |
| 画面 E2E（Playwright） | 4 | 4 | 0 | 2 つの流れ × 1440px・390px |
| **合計** | **147** | **147** | **0** | |

バックエンドの区分は `pytest --collect-only` でディレクトリごとに数えた（31＋64＋36＋6＝137）。

## 5. セキュリティ

再診断（`reports/security/2026-10-18-g1b/report.md`）：新しい指摘は高・中・低とも 0 件、情報 3 件（字体の OFL、診断報告の gitleaks の誤検知、実行・確認の画面の E2E は模擬 API）。ZAP（未ログイン・認証付き、契約の全 45 操作）は失敗 0、サーバの 500 は 0。SAST・SCA・trivy・gitleaks（誤検知を理由付きで除外後）は 0 件。Executor のサービス拒否・情報漏えい・任意コード実行・状態の飛ばし・確認の横取りは自動テストで確認。前回の VA-001〜VA-005 は対応済みのまま。

ゲート条件（高・中 0 件、低は対応済み、SCA の高・重大 0 件、秘密情報 0 件）を満たす。自己診断であり、第三者・独立診断の代わりではない。

## 6. データ

| データセット | 版 | manifest の SHA-256 | 分割 | 凍結日 |
|---|---|---|---|---|
| — | — | — | — | — |

Phase 2 は合成データ・正解ラベルを使わない（Phase 3 から）。

## 7. 時間と費用（実績）

| 区分 | 今回 | 累計 | 上限 |
|---|---|---|---|
| 人の時間（分） | **未記録** | **未記録** | — |
| 追加現金支出（円） | 0 | 0 | 10,000 |

- 費用：有料の API・サービスは使っていない（LLM は mock だけ、D-004）。字体は無料（OFL）。
- 人の時間：`HUMAN_TIME_LOG.csv` は空のまま（G1a §10-3 も未回答）。G5 の工数比較に使うため、推定でも記入をお願いしたい。

## 8. 既知の問題・未解決のリスク

1. **独立レビューがない**（D-024）。実装・テスト・診断がすべて同じ CC。
2. **本番で実行できる業務の Capability がまだない。** 実行の端から端までは試験用の Capability で示した。業務の Capability（文書の解析・抽出・ルール・根拠・出力）は Phase 3。
3. **Windows での子プロセスの起動が遅い。** 1 ノード数百ミリ秒〜1 秒。バックエンドの全テストが 7〜8 分（G1a の約 6 倍）。Phase 3 で文書の処理が増えたら測り、必要なら子プロセスの再利用を ADR で検討する。
4. **画面の制約**（`docs/design/basic/screens.md` §3）：Workflow の作成・編集の画面はない（API で登録）。確認の決定後、修正の内容は画面に出ない（契約 v1 の `ReviewTask` に項目がない）。実行・確認の画面の E2E は API を模擬。
5. **契約を 1.0.2 に上げた**（D-025、エラー応答の追記だけで後方互換）。止まらずに進めた判断を報告で知らせる。
6. **見た目を sales-assistant に合わせた**（D-026）。配色・ロゴは EASF のもので、製品名・会社名・著作権表示・業務用語・データは使っていない。
7. **人の作業時間が未記録**（§7）。

## 9. 次のフェーズの提案（承認を求めるタスク ID）

Phase 3（請求書の POC）、ゲート G2（請求書の業務が確認と正解での評価まで動く）。

| タスク | 内容 | 担当（提案） | 証跡 |
|---|---|---|---|
| P3-01 | 請求書の業務の Capability（文書の解析・規則ベースの抽出〔D-015〕・LLM の抽出〔mock〕・ルール・根拠・出力）、文書のアップロード、出力の API | CC | 実 Workflow の実行、出力 |
| P3-02 | 請求書の合成データ・正解ラベルと独立したテスト | CC（D-024。Codex に渡さない） | 正解ラベル、テスト |

着手の前提：G1b の承認。P3 では文書のアップロード（第三者診断の頻出項目）を扱うため、G2 前の診断はアップロードの項目（checklist E-01〜E-04）を必須にする。

## 10. 人に決めていただきたいこと

1. G1b の承認、または差し戻し。
2. Phase 3（P3-01・P3-02）の承認。
3. 人の作業時間（`HUMAN_TIME_LOG.csv`）の記入（任意。G5 の工数比較で使う）。
