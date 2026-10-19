# ゲート報告 G2（Phase 3、請求書の POC）

| 項目 | 内容 |
|---|---|
| コミット | main `1e4709e`（P3-01d まで）＋ `cc/P3-03-eval-g2`（本報告・評価・診断・VA-G2-001 の修正） |
| 作成日 | 2026-10-19 |
| 作成 | Claude Code（統合責任者） |
| 判定（自己） | **PASS（人の承認待ち）**。ホールドアウト（12 件、1 回）で ADR-007 の必須の閾値をすべて満たした（§2・`reports/eval/holdout/report.md`）。独立レビューはなし（D-024）。初版（同日）では AC-08 が未完了のため BLOCKED（一部）としていた |
| 人の承認 | [x] 承認　承認者：プロジェクト責任者　日付：2026-10-19（D-037） |

G2 の条件（`docs/phase3/PHASE3_PLAN.md` §1）：**請求書の業務が実際の部品の実行・確認・正解での評価まで動き、誤りが見える。** AC-05（解析・抽出・検証・確認・出力）、AC-08（凍結したデータの版と正解で評価）、AC-09（重大な誤りを黙って通さない）。

## 1. 成果物

| タスク | 内容 | 証跡 | コミット | 状態 |
|---|---|---|---|---|
| P3-00 | Phase 3 計画（D-027・D-028） | `docs/phase3/PHASE3_PLAN.md` | 35df32a | 完了 |
| P3-02a | 請求書の合成データの生成器、dev 28 件、manifest、Rule pack `invoice@1.1.0`（D-029） | `fixtures/` | 17cd360・e80e8be | 完了（ホールドアウトは人の作業待ち） |
| P3-01a | 文書の API（登録・一覧・ダウンロード）と保存、`startRun` の文書の入力 | `backend/app/{api/documents.py,documents/}`、`docs/design/detail/documents.md` | 0adf6ea | 完了 |
| P3-01b | 解析・規則ベースの抽出・LLM 抽出（mock）・ルールの検証、`project_context`、子プロセスのメモリ上限（D-030） | `backend/app/capabilities/`、`backend/app/adapters/resources.py`、`docs/design/detail/capabilities.md` | f932e81 | 完了 |
| P3-01c | 根拠の照合（自作のローカル MCP サーバ）、結果の出力と `exportRunResult`（D-031） | `backend/app/{mcp_server.py,adapters/mcp.py,capabilities/evidence.py,capabilities/result_exporter.py}` | b4c3a8e・cb070c7 | 完了 |
| P3-01d | 請求書の Workflow（設定だけ）を本番の部品で端から端まで、文書と出力の画面 | `fixtures/workflows/invoice-v2.json`、`backend/tests/integration/test_invoice_workflow.py`、`frontend/src/features/documents/` | 1e4709e | 完了 |
| P3-03 | dev の評価、G2 前の診断（VA-G2-001 を修正）、本報告（D-032） | `reports/eval/2026-10-19-dev/`、`reports/security/2026-10-19-g2/` | 本ブランチ | 一部（ホールドアウト待ち） |

## 2. 受入条件

| 条件 | 確かめ方 | 結果 | 証跡 |
|---|---|---|---|
| AC-05 解析・抽出・検証・確認・出力 | 合成の請求書をアップロード → 解析 → 規則ベースの抽出 → ルール（invoice@1.1.0）→ 根拠の照合（ローカル MCP、stdio）→ 人の確認（承認）→ CSV の出力を、本番の実装の表・実 PostgreSQL・実ワーカーで実行 | **PASS**。全ノード `real`、請求書番号の根拠の位置が正解ラベルと一致、CSV に確認後の値 | test_invoice_workflow_end_to_end（Windows・Linux） |
| AC-08 凍結したデータの版と正解で評価、誤りの詳細 | 凍結した manifest（D-035）の全ファイルのハッシュを照合し、最終の版（v3）でホールドアウト 12 件を人が 1 回評価。dev の誤りは全件記録、ホールドアウトは集計値だけ AI に | **PASS**。ホールドアウト：重大な誤りの黙認 0、重大ルールの再現率 1.0（5 件）、根拠の位置 1.0（98 範囲）、OCR の根拠はすべて未確認、項目 0.908（目安 0.85）。dev（v3）：項目 0.961 | `reports/eval/holdout/report.md`・`result.json`、`reports/eval/2026-10-19-dev-v3/` |
| AC-09 重大な誤りを黙って通さない | 同じ請求書の 2 回目は INV-006（案件内の重複）が fail で確認へ。値が無い・比べられない・未知の演算子は pass にしない。Workflow は全件を人の確認へ（`route_when: always`）。確認待ち・却下は成功にならない | **PASS** | test_second_run_on_the_same_invoice_is_flagged_as_duplicate、test_rule_results、test_operators、dev の重大ルールの見逃し 0 |
| AC-13 実行と模擬の区別 | LLM の抽出（mock）を使う実行は `mixed`。MCP はローカルのサーバと明記（外部連携として数えない） | PASS | test_llm_extractor_is_mock_and_marks_the_run_mixed、capabilities.md §7 |
| 業務ごとの分岐がない | エンジン（catalog・composer・executor・adapters・evaluation）に業務名なし。請求書の違いは Workflow の設定（見出し・field_spec）と Rule pack だけ | PASS | `scripts/validate_contracts.py`（CI） |
| AC-12（一部） | 文書・実行・出力の画面、1440px・390px、横スクロールなし、コンソールエラーなし | PASS（模擬 API） | `reports/gate_G2_screens/`、e2e/documents.spec.ts |

## 3. 実行したコマンドと結果

2026-10-19 に実行。

| コマンド | 終了コード | 結果の要点 | ログ |
|---|---|---|---|
| `python scripts/validate_contracts.py`（jsonschema・pyyaml・openapi-spec-validator を一時的に入れて） | 0 | schemas=5 capabilities=7 rule_packs=2 workflows=2 openapi=valid、業務名の検査も合格 | — |
| `python scripts/sync_skills.py --check` | 0 | ずれなし | — |
| `uv run ruff check . ../fixtures` / `ruff format --check` / `mypy app tests` / `bandit -q -r app` / `pip-audit` | 0 | 問題なし（mypy 92 ファイル） | `reports/security/2026-10-19-g2/sast/`・`sca/` |
| `uv run pytest -q`（Linux：Docker の `uv:python3.12-bookworm-slim`、実 PostgreSQL の `easf_test`） | 0 | **248 passed**（25 分） | `reports/gate_G2_logs/pytest-linux.log` |
| `npm run lint` / `npm run typecheck` / `npm run build` | 0 | 警告 0 / 型エラー 0 / 成功 | — |
| `npx vitest run` | 0 | **10 passed** | — |
| `E2E_BASE_URL=http://localhost:5174 npx playwright test e2e/documents.spec.ts e2e/runs.spec.ts` | 0 | **4 passed**（模擬 API、1440px・390px） | `reports/gate_G2_screens/` |
| `python -m app.evaluation.offline …`（dev） | 0 | §2 の値 | `reports/eval/2026-10-19-dev/` |
| GitHub Actions（ci） | 成功 | 0adf6ea・f932e81・cb070c7・1e4709e で成功。b4c3a8e は失敗（契約テストの準備。cb070c7 で修正）。各タスクは CI の成功を確かめてから main に入れた | GitHub の Actions 画面 |

未実行：
- ホールドアウトの評価（未生成・未凍結。人の作業待ち）。
- Windows でのバックエンドの全テストの一括実行：この端末の CPU が 90% 前後（ほかのプロジェクトの処理）で、子プロセスの起動を待つ試験用の Capability のテストが時間切れになった（8 件、`timeout`）。同じコミットは Linux（Docker・CI）で全件成功。Windows では変更した部分のテストを個別に実行して成功。
- 実バックエンドに対する Playwright（`e2e/smoke.spec.ts`）：E2E 用の利用者とバックエンドの起動が必要なため今回は実行していない。
- 独立レビュー（D-024）。画面の DAST。

## 4. 試験成績

| 区分 | 件数 | 成功 | 失敗 | 主な観点 |
|---|---|---|---|---|
| バックエンド 単体（tests/unit） | 87 | 87 | 0 | 値の読み取り（和暦・金額）、規則ベースの抽出、ルールの 3 値・演算子・入れ子、根拠の照合、CSV の無害化、MCP のツール、Catalog のツールのスキーマ照合、オフライン評価 |
| バックエンド 結合（tests/integration、実 DB） | 107 | 107 | 0 | 文書の API 33、業務の Capability 4、出力と MCP 4、請求書の端から端まで 2 ほか |
| バックエンド 契約（tests/contract） | 40 | 40 | 0 | 実装済み 38 操作の認可の全件表（文書 3・出力 1 を追加）、応答スキーマ |
| バックエンド 診断の再発防止（tests/security） | 7 | 7 | 0 | VA-001・VA-003〜VA-005・VA-G2-001 |
| 合成データの生成器（tests/fixtures） | 7 | 7 | 0 | P3-02a |
| 画面 単体（vitest） | 10 | 10 | 0 | ファイルの事前チェックを追加 |
| 画面 E2E（Playwright、模擬 API） | 4 | 4 | 0 | 文書・実行・出力、解決策・実行・確認 × 1440px・390px |
| **合計** | **262** | **262** | **0** | |

バックエンドは Linux で 248 件（87＋107＋40＋7＋7）。

## 5. セキュリティ

G2 前の自己診断（`reports/security/2026-10-19-g2/report.md`）：新しい指摘は **中 1 件（VA-G2-001、対応済み）**、情報 3 件。読み取り専用のコンテナで 1 MB を超えるアップロードが 500 になっていた（multipart の一時ファイル）→ `/tmp` に tmpfs（64 MB）を付けて修正し、再発防止テストを追加、再診断で解消。アップロードの必須項目 E-01〜E-04 はすべて問題なし。SAST（ruff S・bandit・semgrep）・SCA（pip-audit・npm audit）・trivy（イメージ・設定）・gitleaks（履歴・ソース）は 0 件。ZAP（未ログイン・認証付き）は失敗 0・合格 114、サーバの 500 は 0。

ゲート条件（高・中の未対応 0 件、SCA の高・重大 0 件、秘密情報 0 件）を満たす。自己診断であり、第三者・独立診断の代わりではない。

## 6. データ

| データセット | 版 | manifest の SHA-256 | 分割 | 凍結日 |
|---|---|---|---|---|
| 請求書（合成） | 生成器 0.1.0、`invoice@1.1.0` | `bbbae8e47c7c497ec0bc453645b57b1cff17143a8ce2ce10a9b37c24332d41a3`（`fixtures/manifest.json`） | dev 28 件（リポジトリ内） | 2026-10-19（D-035） |
| 請求書（合成） | 同上 | `9439de443027be16f9d2e5dc54a24a3f1ab65506a3ca29a64bab8314ac622ac6`（`fixtures/manifest.holdout.json`、ハッシュだけ） | ホールドアウト 12 件（リポジトリ外、暗号化 ZIP） | 2026-10-19（D-035） |

dev の結果を見て抽出・ルールを直すことはしていない（凍結前の調整を避けるため）。

## 7. 時間と費用（実績）

| 区分 | 今回 | 累計 | 上限 |
|---|---|---|---|
| 人の時間（分） | **未記録** | **未記録** | — |
| 追加現金支出（円） | 0 | 0 | 10,000 |

有料の API・サービスは使っていない（LLM は mock、MCP はローカル）。

## 8. 既知の問題・未解決のリスク

1. ~~ホールドアウトが未生成・未凍結~~ → 2026-10-19 に凍結（D-035）・評価済み（末尾の追記）。ホールドアウトは評価に使ったので、版を変えて再評価するなら新しいホールドアウトが要る。
2. ~~スキャン画像は OCR 未対応~~ → Tesseract を導入（D-034）。OCR の値は uncertain、根拠は unverified で、確認者が必ず見る。
3. **合成データは 1 つの生成器から**。抽出の見出しは Workflow の設定に書いており、実在の請求書の多様さは表していない。dev の高い値をそのまま実力とみなさない。
4. **実 LLM の抽出は未評価**（D-004）。mock は全項目 uncertain を返すだけ。
5. **独立レビューなし**（D-024）。実装・テスト・診断・評価がすべて同じ CC。
6. **この端末の環境**：開発用 DB のコンテナとデータが消えていたため 55433 番で作り直した（55432 番はほかのプロジェクトが使用中）。開発用の管理者（admin など）は無く、診断用に `assess_admin` を作った（パスワードはリポジトリ外）。CPU の負荷が高く、Windows での時間に敏感なテストが時間切れになる。
7. **ワーカーはコンテナにしていない**。コンテナで動くのは API だけ。
8. **画面の制約**：実行の文書の入力は通常の選択（200 件まで）。Workflow の作成・編集の画面はない。

## 9. 次の作業の提案（承認を求めること）

| 作業 | 内容 | 担当 |
|---|---|---|
| ホールドアウトの生成と凍結 | `fixtures/HOLDOUT.md` の手順（秘密の種、リポジトリの外にラベル）。manifest のハッシュを DECISIONS に記録 | 人 |
| ホールドアウトの評価 | 凍結後、人が `app.evaluation.offline` 相当を実行し、AI には集計値だけ（easf-eval-integrity） | 人（CC は手順書を用意できる） |
| G2 の判定 | ホールドアウトの集計値で ADR-007 の閾値を判定し、本報告に追記 | CC → 人 |
| （任意）抽出の改善 | 凍結後に dev の誤りを見て直す（OCR を入れるかを含む） | CC（承認後） |

Phase 4（契約書）は G2 の承認まで着手しない。

## 10. 人に決めていただきたいこと

1. ホールドアウト 12 件の生成・凍結の実施（または、その時期）。
2. G2 の扱い：ホールドアウトの評価を待って判定するか、AC-08 を残して条件付きで承認するか。
3. スキャン画像の OCR（Tesseract の導入。費用 0 円、コンテナが大きくなる）を Phase 3 で行うか。
4. 人の作業時間（`HUMAN_TIME_LOG.csv`）の記入（任意。G5 の工数比較で使う）。

### 回答（2026-10-19、D-033）

1. ホールドアウト：今すぐ人が生成・凍結する（OCR の調整より前）。手順 4 を修正済み（ラベルを編集しない）。
2. G2：ホールドアウトの評価を待って判定する（条件付きの承認はしない）。評価は OCR を入れた最終の版で 1 回。
3. OCR：Phase 3 で行う（P3-04）。
4. 人の作業時間：後で決める。

### 進捗（2026-10-19）

- ホールドアウト 12 件を人が生成・凍結（D-035。manifest の SHA-256 は dev `bbbae8e4…`、holdout `9439de44…`）。
- OCR（P3-04、D-034）を入れ、凍結の後に dev で評価・調整（D-036）：項目 0.961、重大ルールの再現率 1.0、根拠の位置 1.0、重大項目の誤った found 0、OCR の根拠はすべて unverified（`reports/eval/2026-10-19-dev-v3/report.md`）。
- **最終の版は `fixtures/workflows/invoice-v3.json`。** ホールドアウトの評価は人が `scripts/eval_holdout.ps1` で 1 回実行する（`fixtures/HOLDOUT.md`「評価のとき」）。結果の集計値（`reports/eval/holdout/result.json`）で §2 の AC-08 と ADR-007 の閾値を判定し、本報告を更新する。

### ホールドアウトの評価（2026-10-19）

人が `scripts/eval_holdout.ps1` で 1 回実行（終了コード 0）。結果は `reports/eval/holdout/report.md`。ADR-007 の必須の閾値（重大な誤りの黙認 0、重大ルールの再現率 1.0、根拠の位置 0.9 以上、照合できない根拠は未確認）をすべて満たし、項目抽出も目安（0.85）を上回った（0.908）。確認の記録の完全さは結合テストで確認している。**G2 の判定（自己）を PASS に更新し、人の承認を求める。**

