# タスクの状態（TASK_STATUS）

| タスク | 担当 | 状態 | ブランチ | 証跡 | 更新日 |
|---|---|---|---|---|---|
| P0-00 skill 一式と共通規則 | CC | 完了 | `cc/P0-00-skills` | `AGENTS.md`、`.claude/skills/`、`python scripts/sync_skills.py --check` exit 0 | 2026-10-18 |
| P0-01 ADR とエンジン比較 | CC | 完了（ADR-001〜009 承認済み。D-010） | `cc/P0-01-adr` | `docs/adr/` | 2026-10-18 |
| P0-02 G0 レビュー（自己レビュー、D-011・D-012） | CC | 完了（BLOCKER 0・MAJOR 7・MINOR 8・質問 3） | `cc/P0-02-g0-review` | `reviews/G0_REVIEW.md` | 2026-10-18 |
| P0-03 契約 v1 | CC | レビュー待ち（凍結は G0） | `cc/P0-03-contracts` | `contracts/`、`python scripts/validate_contracts.py` exit 0（陰性試験 6 種も検出） | 2026-10-18 |
| P0-04 合成データ計画・事前登録 | CC（D-011） | 完了（事前登録は G0 で承認待ち） | `cc/P0-04-fixture-and-prereg` | `docs/design/fixture_plan.md`、`docs/experiment/preregistration.md` | 2026-10-18 |
| P0-05 脅威モデル・基本設計・見積・台帳 | CC | レビュー待ち | `cc/P0-05-design` | `docs/design/`、`docs/phase0/estimates.md`、台帳 5 種 | 2026-10-18 |
| P0-06 レビュー指摘の反映 | CC | 完了（15 件すべて反映） | `cc/P0-06-review-fixes` | `reviews/G0_REVIEW.md` §5 | 2026-10-18 |
| G0 ゲート報告 | CC | 完了・**承認済み**（D-014） | — | `reports/gate_G0.md` | 2026-10-18 |
| P1-01 FastAPI・PostgreSQL の雛形（健康確認・マイグレーション・CI） | CC | 完了 | `cc/P1-01-scaffold` | pytest 15 passed（実 PostgreSQL）、ruff・mypy strict・bandit・pip-audit 問題なし | 2026-10-18 |
| P1-02 Capability Catalog（不変の版・検証） | CC | 完了 | `cc/P1-02-catalog` | pytest 44 passed（見本 6 件の登録・冪等・409・外部 $ref・実装の許可リスト・DB トリガー・Rule pack）、静的検査問題なし | 2026-10-18 |
| P1-03 日本語 UI の枠と共通部品 | CC | 完了 | `cc/P1-03-ui-shell` | lint・typecheck・vitest 6 passed・build（ソースマップなし）・npm audit 0 件・Playwright 2 passed（1440px・390px、横スクロールなし、想定外のコンソールエラーなし） | 2026-10-18 |
| P1-04 契約テスト・否定テスト | CC | 完了 | `cc/P1-04-contract-tests` | 実装と契約の一致、x-easf-roles からの認可の全件表（実装済み 20 操作）、全応答の応答スキーマ検証。pytest 65 passed。契約の欠落 1 件を検出し 1.0.1 で修正（D-022） | 2026-10-18 |
| P1-05 認証・セッション・案件・メンバー・要件の版 | CC | 完了 | `cc/P1-05-auth-projects` | pytest 30 passed（ログイン・固定化・列挙・ロック・CSRF/Origin・IDOR・一括代入・自己承認を含む）、ruff・mypy・bandit・pip-audit 問題なし | 2026-10-18 |
| G1a 前の脆弱性自己診断 | CC | 完了 | `cc/G1a-vuln-assessment` | 高 0・中 1・低 4（すべて対応・再診断済み）。SAST・SCA・gitleaks・trivy 0 件、ZAP（未ログイン・認証付き）失敗 0。pytest 71 passed。報告書 `reports/security/2026-10-18/report.md` | 2026-10-18 |
| G1a ゲート報告 | CC | 完了・**承認済み**（D-024） | `cc/G1a-gate-report` | `reports/gate_G1a.md` | 2026-10-18 |
| P2-00 Phase 2 計画・詳細設計・テスト専用 DB | CC | 完了 | `cc/P2-00-plan` | `docs/phase2/PHASE2_PLAN.md`、`docs/design/detail/run_execution.md`。テストは `easf_test` だけを使い、`_test` 以外の DB 名では停止。pytest 71 passed、開発用 DB の利用者数は実行前後で同じ | 2026-10-18 |
| P2-01 Composer と Solution の API | CC | 完了 | `cc/P2-01-composer` | Composer の検査 13 種（見本の Workflow 2 件は合格、誤り 14 種を検出）、Solution の API 6 操作（ETag・If-Match・承認の規則・DB トリガーで凍結）、認可の全件表に追加。契約 1.0.2（D-025）。pytest 102 passed | 2026-10-18 |
| P2-02 Executor・アダプタ・Run と確認の API・トレース | CC | 完了 | `cc/P2-02-executor` | 状態機械・DB をキューにしたワーカー・子プロセスでのローカル実行・LLM は mock のみ・人の確認（割り当て・決定・再開・却下）・ハッシュ連鎖のトレース、API 8 操作。試験用 Capability（testkit）で端から端まで、再現性（同じ入力で同じハッシュとイベントの並び）、mock の `mixed`、予算超過。pytest 124 passed | 2026-10-18 |
| P2-04 Executor の敵対的テスト | CC | 完了 | `cc/P2-04-adversarial` | 13 件：無限ループの強制終了、例外は型名だけ（入力値が漏れない）、不正な出力は再試行しない、出力の上限、子プロセスの異常終了とワーカーの継続、冪等なら再試行・そうでなければしない、予算による時間切れは budget_exceeded、ノードの入力スキーマ違反、ワーカーの異常終了からの回復、2 つのワーカーの取り合い、別の実行の確認タスク。pytest 137 passed | 2026-10-18 |
| P2-03 実行・確認の画面 | CC | 完了 | `cc/P2-03-run-ui` | 解決策（検証・承認・実行）、実行の一覧、実行モニター（自動更新・処理の流れ・トレース）、確認タスク、確認（AI 下書き・根拠・3 値の判定・修正前後）。lint・typecheck・vitest 6・build・npm audit 0 件・Playwright 4 passed（模擬 API の流れ＋実バックエンドの既存の流れ、1440px・390px） | 2026-10-18 |
| G1b 前の脆弱性の再診断 | CC | 完了 | `cc/G1b-gate` | 新しい指摘は高・中・低 0 件、情報 3 件。SAST・SCA・trivy・gitleaks（誤検知を除外）0 件、ZAP（未ログイン・認証付き、45 操作）失敗 0・500 なし。`reports/security/2026-10-18-g1b/report.md` | 2026-10-19 |
| G1b ゲート報告 | CC | 完了・**承認済み**（D-027） | `cc/G1b-gate` | `reports/gate_G1b.md`。pytest 137・vitest 6・Playwright 4 passed、静的検査・SCA 問題なし | 2026-10-19 |
| P3-00 Phase 3 計画 | CC | 完了 | `cc/P3-00-plan` | `docs/phase3/PHASE3_PLAN.md`、D-027・D-028 | 2026-10-19 |
| P3-02a 請求書の生成器・dev・manifest | CC | 完了（ホールドアウトは人の作業待ち） | `cc/P3-02a-fixtures` | `fixtures/generator/`、dev 28 件、`fixtures/manifest.json`、Rule pack `invoice@1.1.0`、生成器のテスト 7 件（Windows・Linux とも成功）。ホールドアウト 12 件は `fixtures/HOLDOUT.md` の手順で人が生成 | 2026-10-19 |
| P3-01a 文書の API | CC | 完了 | `cc/P3-01a-documents` | 登録・一覧・ダウンロード、`document` 表（0006）、子プロセスでの構造の確認、`startRun` の `document_ref`。文書のテスト 33 件（形式の偽装 9・危険な内容 8・大きさ・項目・ファイル名・他案件・CSRF）、契約テストに 3 操作を追加（39 件）。ruff・mypy・bandit・pip-audit 問題なし | 2026-10-19 |
| P3-01b 解析・抽出・検証の Capability | CC | 完了（dev の結果による抽出の調整はしていない。ホールドアウトの凍結待ち） | `cc/P3-01b-capabilities` | `document_parser.v1`・`rule_based_extractor.v1`・`structured_extractor.v1`（mock）・`rule_validator.v1` を結び付け、`project_context`、子プロセスのメモリ上限（POSIX）。単体テスト 40 件（値の読み取り・抽出・ルールの 3 値・入れ子の上限）、結合テスト 4 件（アップロード → 解析 → 抽出 → 検証を実際に実行、mock は mixed、画像、参照の解決失敗）。D-030 | 2026-10-19 |
| P3-01c 根拠（MCP）・出力 | CC | 完了 | `cc/P3-01c-evidence-export` | 自作のローカル MCP サーバ（stdio）と MCP アダプタ、根拠の照合、`result_exporter.v1`、`exportRunResult`（CSV インジェクション対策・内容の照合）。単体テスト 14 件、結合テスト 4 件（実際の stdio の MCP 呼び出し・CSV/JSON・ロール・409・改ざんの検出）、契約テストに `exportRunResult` を追加。D-031 | 2026-10-19 |
| P3-01d 請求書の端から端まで・画面 | CC | 完了 | `cc/P3-01d-invoice-e2e` | 請求書の Workflow（`fixtures/workflows/invoice-v2.json`、設定だけ）を本番の部品で端から端まで（全ノード real、根拠の位置が正解ラベルと一致、CSV 出力、2 回目の同じ請求書は INV-006 が fail）。画面：文書の一覧・登録・ダウンロード、実行の文書の入力、結果の出力。vitest 10・Playwright 4 passed（模擬 API、1440px・390px） | 2026-10-19 |
| P3-03 評価・凍結・診断・G2 報告 | CC | 完了（G2 の承認待ち） | `cc/P3-03-eval-g2`・`cc/P3-03-g2-judgement` | dev の評価（v2・v3）、凍結（D-035）、ホールドアウトの評価（人が 1 回、必須の閾値をすべて満たす）、G2 前の診断、`reports/gate_G2.md`（自己判定 PASS） | 2026-10-19 |
| P3-04 スキャン画像の OCR（Tesseract） | CC | 完了 | `cc/P3-04-ocr`・`cc/P3-04-ocr-tuning` | OCR の実装、凍結（D-035）後の dev 評価 v3：項目 0.961・重大ルールの再現率 1.0・根拠の位置 1.0。OCR の後処理（D-036）。ホールドアウトの評価の道具 `scripts/eval_holdout.ps1`（偽のホールドアウトで動作確認） | 2026-10-19 |
| G2 ゲート報告 | CC | 完了・**承認済み**（D-037） | — | `reports/gate_G2.md` | 2026-10-19 |
| P4-00 Phase 4 計画 | CC | 完了・**承認済み**（D-038） | `cc/P4-00-plan` | `docs/phase4/PHASE4_PLAN.md` | 2026-10-20 |
| P4-01 契約書の合成データ | CC | 完了（ホールドアウトは人の作業待ち） | `cc/P4-01-contract-fixtures` | `fixtures/generator/{contract,render_contract}.py`、dev 28 件・正解ラベル・CR-1 の正解（別ファイル）・manifest、`fixtures/contract/HOLDOUT.md`、生成器のテスト 7 件（Windows・Linux で同じバイト列） | 2026-10-20 |
| P4-02 ベースラインの要件パッケージ | CC | 完了 | `cc/P4-02-baseline-bundle` | `experiment/baseline_bundle/`、`experiment/build_bundle.py`、SHA-256 `fe394a9d…`（D-039） | 2026-10-20 |
| P4-03 Factory で契約書 | CC | 完了 | `cc/P4-03-contract` | 抽出 1.1.0、検証・根拠の実装の修正、Workflow contract-v2、dev 評価（項目 0.924・重大 1.0・根拠 1.0）、請求書の回帰（変化なし）、端から端までと再利用のテスト（Linux で 4 件成功）。D-043 | 2026-10-21 |
| P4-04 要件変更 CR-1・再利用の証拠 | CC | 完了 | `cc/P4-04-cr1-factory` | CR-1 を設定だけで（Workflow v3・Rule pack contract@1.1.0）、dev で CON-006 の検出 6/6、端から端までのテスト（版が v2 と同じ・CON-006 fail）、請求書と契約書で同じ capability_version_id（P4-03 のテスト）。D-046 | 2026-10-21 |
| P4-05 両 arm のホールドアウトの評価・G3 | CC・人 | 完了（G3承認D-051、元集計を維持） | `cc/P4-05-scoring`・`cc/P4-05-holdout-result` | 共通の採点の道具、評価のスクリプト、`reports/eval/contract-holdout/`、`reports/gate_G3.md`。D-047〜D-051 | 2026-10-23 |
| P4-06 G3 前の診断・独立レビュー | Codex | 成果物統合済み（未完了検査・残事項はG3報告） | `codex/P4-06-g3-review` | c717f54・d97a556、`reports/security/2026-10-21-g3/`、`reports/review/2026-10-21-g3.md` | 2026-10-23 |
| G3 ゲート報告・承認記録 | Codex（人の継続指示） | **承認済み（D-051）**、記録更新 | `codex/G3-approval-record` | `reports/gate_G3.md`。検査・レビューの残事項は維持 | 2026-10-23 |
| Phase 5 移行準備 | Codex（人の継続指示） | 計画整理済み、P5-03aの有界診断を実施 | `codex/G3-approval-record`（計画）、`codex/P5-03a-semgrep-diagnostics`（診断） | `docs/phase5/PHASE5_PLAN.md` | 2026-10-23 |
| P5-03a semgrep実行条件の独立確認 | Codex | 有界調査の成果物作成済み。製品semgrepは未完了・原因不明 | `codex/P5-03a-semgrep-diagnostics` | `handoffs/P5-03a.md`、`reports/security/2026-10-23-g4/report.md`。最小1件検出exit 0、製品検査180秒でexit 143 | 2026-10-23 |
| P5-03b 依存ライセンス・出所・安全境界 | Codex | 一覧・独立レビュー作成済み、配布表示・来歴・ログと保持の不足を継続 | `codex/P5-03b-license-review` | `handoffs/P5-03b.md`、`reports/security_review.md`、`reports/security/2026-10-23-g4/licenses/` | 2026-10-23 |
| P5-03a2 semgrep分割実行の補完 | Codex | 5規則集の製品検査完了、指摘0・errors 0。テイント解析timeout警告2実行で残存 | `codex/P5-03a2-semgrep-copy` | `handoffs/P5-03a2.md`、`reports/security/2026-10-23-g4/semgrep-followup/`。対象集合98件一致、原因不明は維持 | 2026-10-23 |
| P5-03c 例外ログの合成値混入の確認 | Codex | 診断・隔離修正案を作成。製品未修正、共有処理への適用承認待ち | `codex/P5-03c-error-log-review` | `handoffs/P5-03c.md`、`reports/security/2026-10-23-g4/error-log/`。製品3/3混入exit 1、隔離案3/3非混入exit 0。VA-G4-001暫定中 | 2026-10-23 |
| P5-03d VA-G4-001の本体修正・再診断 | Codex | D-052により個別適用。修正・本体3ケース再診断済み | `codex/P5-03d-error-log-fix` | `handoffs/P5-03d.md`、`reports/security/2026-10-23-g4/error-log-fix/`。3失敗→3成功、型・trace_idと500応答を保持。全件CIはコミット履歴で確認 | 2026-10-23 |
| P5-02a 既存評価の独立照合・証拠索引 | Codex | 7集計・比較表16セルを照合。G4の証拠不足を整理。再評価は未実行 | `codex/P5-02a-evaluation-index` | `handoffs/P5-02a.md`、`reports/evaluation_index.md`、`reports/eval/2026-10-23-index/`、`reports/review/2026-10-23-g4-readiness.md` | 2026-10-23 |
| P5-03e 修正後イメージの自己診断 | Codex | コードSHA一致・例外3ケース・認証前ASGI7経路成功。初回musl系2検出→キャッシュなしビルド後0件。HTTP/認証後DAST未実行 | `codex/P5-03e-runtime-reassessment` | `handoffs/P5-03e.md`、`reports/security/2026-10-23-g4/runtime/report.md`。製品・既存DB・旧タグは変更なし | 2026-10-23 |
| P5-03f 専用環境でのHTTP API自己診断 | Codex | HTTP24項目成功、exit 0、後始末成功。起動・ポートの初回3失敗を保持。全面ZAP・実画面は未実行 | `codex/P5-03f-http-assessment` | `handoffs/P5-03f.md`、`reports/security/2026-10-26-g4/http/report.md`。製品・凍結構成・既存DBは変更なし | 2026-10-26 |
| P5-03g 有界ZAP・CC向け変更要求 | Codex・読み取り専用の並行エージェント | 未認証PASS 106・認証付き受動PASS 57、両exit 0、中/高alert 0。時間上限による全面性未確認。CCへの変更要求案を準備、実装未着手 | `codex/P5-03g-zap-review` | `handoffs/P5-03g.md`、`reports/security/2026-10-26-g4/zap/`、`reports/review/2026-10-26-version-change-request.md`。後始末成功、凍結構成は変更なし | 2026-10-26 |
