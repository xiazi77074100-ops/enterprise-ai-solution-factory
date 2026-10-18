# ゲート報告 G1a（Phase 1）

| 項目 | 内容 |
|---|---|
| コミット | e54782a（main。本報告と証跡のコミットはこの次） |
| 作成日 | 2026-10-18 |
| 作成 | Claude Code（統合責任者） |
| 判定（自己） | **PASS（人の承認待ち）**。ただし独立レビュー（Codex）は未実施で、すべて自己レビュー（§8-1）。また P1-02〜P1-03 の 3 コミットは CI が失敗したまま main に入っていた（§8-2、現在は解消） |
| 人の承認 | [ ] 承認  [ ] 差し戻し　承認者：＿＿＿　日付：＿＿＿ |

G1a の条件（`easf_package/tasks/PHASE_PLAN.md`）：**API の契約テスト、セキュリティの基本、実際の永続化。**

## 1. 成果物

| タスク | 内容 | 担当（計画 → 実際） | 証跡 | コミット | 状態 |
|---|---|---|---|---|---|
| P1-01 | FastAPI・PostgreSQL の雛形、健康確認、マイグレーション、CI | CC → CC | `backend/`、`.github/workflows/ci.yml` | （P1-01）、4a09d16（alembic の修正） | 完了 |
| P1-05 | 認証・セッション・CSRF・案件・メンバー・要件の版、管理用 CLI | CC → CC | `backend/app/{auth,project,api}`、`backend/tests/integration/test_auth_projects.py` | d0c9e1a | 完了 |
| P1-02 | Capability Catalog と Rule pack（不変の版・RFC 8785 の内容ハッシュ・DB トリガー） | CC → CC | `backend/app/catalog/`、`backend/tests/integration/test_catalog.py` | 5fe5bf8 | 完了 |
| P1-03 | 日本語 UI の枠と共通部品、ログイン・プロジェクト・能力カタログの画面 | Codex → **CC**（D-011） | `frontend/`、`docs/design/basic/screens.md`、`reports/gate_G1a_screens/` | 72d9cce | 完了 |
| P1-04 | 契約テスト・否定テスト（実装と契約の一致、認可の全件表、応答スキーマ） | Codex → **CC**（D-011） | `backend/tests/contract/test_openapi_contract.py` | 2f22521 | 完了 |
| — | G1a 前の脆弱性自己診断とバックエンドのコンテナ | CC | `reports/security/2026-10-18/report.md`、`backend/Dockerfile` | 815a5b0、e54782a | 完了 |

## 2. 受入条件

G1a で示せる範囲だけを書く。AC-03 以降（Workflow・実行・評価など）は Phase 2 以降の対象。

| AC | 確かめ方 | 結果 | 証跡 |
|---|---|---|---|
| G1a：契約テスト | 実装の OpenAPI と `contracts/openapi.yaml` の operationId・メソッド・パスの一致。`x-easf-roles` から作った認可の全件表（実装済み 20 操作 × 未ログイン・非メンバー・ロールなし・ロールあり）。全応答を契約の応答スキーマで検証 | 成功。契約の欠落 1 件（login の 403）を検出し、契約 1.0.1 で修正（D-022） | `backend/tests/contract/`、`reports/gate_G1a_logs/pytest.log` |
| G1a：セキュリティの基本 | 脆弱性自己診断（SAST・SCA・秘密情報・コンテナ・ZAP・手動） | 高 0・中 1・低 4、すべて対応・再診断済み | `reports/security/2026-10-18/report.md` |
| G1a：実際の永続化 | 実 PostgreSQL 17 でのテスト、マイグレーションの upgrade → downgrade → upgrade、アプリのロールが DDL を実行できないこと、登録済みの版の変更を DB トリガーが拒否すること | 成功 | test_migrations_upgrade_downgrade_upgrade、test_application_role_cannot_run_ddl、test_database_rejects_mutation_of_registered_versions |
| AC-01（一部） | 案件・要件の版・明示の承認（作成者以外の責任者だけが承認できる） | API・画面とも成功 | test_requirement_revision_approval_rules、E2E（要件の版の登録） |
| AC-02（一部） | 不変の版・契約の検証・適用範囲・検索 | 成功（見本 6 件の登録・冪等・同じ版の別内容は 409・外部 `$ref` の拒否・検索と絞り込み） | `backend/tests/integration/test_catalog.py` |
| AC-12（一部） | 日本語 UI（ログイン・プロジェクト・能力カタログ）、1440px・390px、横スクロールなし、想定外のコンソールエラーなし | 成功 | `reports/gate_G1a_screens/`、`reports/gate_G1a_logs/playwright.log` |
| AC-14（一部） | 権限（認可の全件表）・セキュリティ診断 | 成功。データ保持は Phase 1 の対象外 | 上の 2 行 |

## 3. 実行したコマンドと結果

2026-10-18、main の e54782a（作業ツリーは同じ）で実行。ログは `reports/gate_G1a_logs/`。

| コマンド | 終了コード | 結果の要点 | ログ |
|---|---|---|---|
| `python scripts/validate_contracts.py` | 0 | schemas=5 capabilities=6 rule_packs=2 workflows=2 openapi=valid | validate_contracts.log |
| `python scripts/sync_skills.py --check` | 0 | ずれなし | sync_skills.log |
| `uv run ruff check .` / `ruff format --check .` | 0 / 0 | 問題なし / 45 ファイル整形済み | ruff.log、ruff_format.log |
| `uv run mypy app tests` | 0 | 41 ファイル問題なし（strict） | mypy.log |
| `uv run bandit -q -r app` | 0 | 検出なし | bandit.log |
| `uv run pip-audit` | 0 | 既知の脆弱性なし | pip_audit.log |
| `uv run alembic upgrade head` | 0 | 最新 | alembic.log |
| `uv run pytest -q`（実 PostgreSQL） | 0 | **71 passed** | pytest.log |
| `npm ci` / `npm audit --omit=dev` | 0 / 0 | 脆弱性 0 件 | npm_ci.log、npm_audit.log |
| `npm run lint` / `npm run typecheck` | 0 / 0 | 警告 0 / 型エラー 0 | lint.log、typecheck.log |
| `npm test`（vitest） | 0 | **6 passed** | vitest.log |
| `npm run build` | 0 | 成功、ソースマップ 0 件 | build.log |
| `npx playwright test`（1440px・390px） | 0 | **2 passed** | playwright.log、画面は `reports/gate_G1a_screens/` |
| GitHub Actions（ci：contracts-and-skills・backend・frontend） | 成功 | e54782a・815a5b0・2f22521 で成功。5fe5bf8・4a09d16・72d9cce は失敗（§8-2） | GitHub の Actions 画面 |

未実行：Codex による独立レビュー・独立テスト（§8-1）。osv-scanner（pip-audit・npm audit・trivy で代替、診断報告 §8）。

## 4. 試験成績

| 区分 | 件数 | 成功 | 失敗 | 未実行 | 主な観点 |
|---|---|---|---|---|---|
| バックエンド 単体（tests/unit） | 11 | 11 | 0 | 0 | セキュリティヘッダ・エラーの形・情報漏えい・要求サイズ・TRACE |
| バックエンド 結合（tests/integration、実 DB） | 33 | 33 | 0 | 0 | ログイン・固定化・列挙・ロック・CSRF/Origin・IDOR・一括代入・自己承認・Catalog の不変性・マイグレーション |
| バックエンド 契約（tests/contract） | 21 | 21 | 0 | 0 | 実装と契約の一致、認可の全件表、応答スキーマ |
| バックエンド 診断の再発防止（tests/security） | 6 | 6 | 0 | 0 | VA-001・VA-003〜VA-005 |
| 画面 単体（vitest） | 6 | 6 | 0 | 0 | API クライアント（CSRF・エラー）、フォームの 3 つの約束 |
| 画面 E2E（Playwright） | 2 | 2 | 0 | 0 | ログイン → 案件 → 要件 → カタログ（1440px・390px） |
| **合計** | **79** | **79** | **0** | **0** | |

バックエンドの区分は `pytest --collect-only` でディレクトリごとに数えた（11＋33＋21＋6＝71、pytest の結果と一致）。

## 5. セキュリティ

自己診断（`reports/security/2026-10-18/report.md`）の総評：高 0 件。中 1 件（VA-002：コンテナの依存）、低 4 件（VA-001：本番の Secure Cookie、VA-003：CORP ヘッダ、VA-004：NUL 文字で 500、VA-005：Host ヘッダ・インジェクション）を検出し、すべて修正・再診断済み。最終のイメージで trivy 0 件、ZAP（未ログイン・認証付き）の失敗 0 件。受容した指摘はなし。情報 5 件（ローカルの HTTP など）は報告書に一覧。

ゲート条件（高・中 0 件、低は対応済み、SCA の高・重大 0 件、秘密情報 0 件）を満たす。自己診断であり、第三者診断・独立診断の代わりではない。

## 6. データ

| データセット | 版 | manifest の SHA-256 | 分割 | 凍結日 |
|---|---|---|---|---|
| — | — | — | — | — |

Phase 1 は合成データ・正解ラベルを使わない（Phase 3 から）。Catalog の見本は `contracts/examples/`（契約 v1.0.1 の一部）。

## 7. 時間と費用（実績）

| 区分 | 今回 | 累計 | 上限 |
|---|---|---|---|
| 人の時間（分） | **未記録** | **未記録** | — |
| 追加現金支出（円） | 0 | 0 | 10,000 |

- 費用：有料の API・サービスは使っていない。診断の道具（semgrep・gitleaks・trivy・ZAP）は無料のコンテナ。`COST_LEDGER.csv` に Phase 1 の行を追加した。
- 人の時間：`HUMAN_TIME_LOG.csv` は空のまま。Claude Code は人の作業時間を測れないため、**記入をお願いしたい**（§10）。工数比較（G5）に使うので、推定で書く場合は note に「推定」と書く。

## 8. 既知の問題・未解決のリスク

1. **独立レビューがない。** P1-03・P1-04 は計画では Codex の担当だったが、D-011 により CC が代行した。実装したのも、テストを書いたのも、診断したのも同じ CC であり、見落としが相殺されない。Phase 2 の着手前か並行で、Codex（または人）による独立レビューを推奨する。
2. **CI が失敗したまま main に入れたコミットがあった。** 5fe5bf8（P1-02）・4a09d16・72d9cce（P1-03）で、`validate_contracts.py` の業務名の検査が「契約」（Capability の契約の意味）に反応して失敗していた。手元の検査だけを見て、CI の結果を確かめずに main へ進めていた。2f22521（P1-04）で検査を「契約書」に絞って解消し、以後は成功。バックエンド・画面の CI ジョブはこの間も成功。**対策：今後はタスクごとに CI の成功を確かめてから「完了」にする**（本報告から適用）。
3. **テストと開発用の API が同じ DB を使う。** 全テストの実行で開発用のデータ（利用者を含む）が消える。テスト専用の DB を分けることを Phase 2 の最初に提案する。
4. **画面の既知の制約**（`docs/design/basic/screens.md` §3）：メンバーの編集画面がない（契約 v1 に利用者の検索 API がない）、能力カタログの接続方式の絞り込みが 1 つだけ、自分が作成した版にも承認ボタンが出る（押すとサーバが 403）。いずれも契約 v1.1 の候補。
5. **診断の道具の版。** 最新の ZAP イメージがこの端末で壊れていたため 2.16.1 に固定した（D-023）。CI にはまだ SAST・SCA の一部（semgrep・gitleaks・trivy）を入れていない。
6. 自己診断で未実施の項目（画面の DAST、B-07 セッション ID の乱数性、F-04、F-07 など。診断報告 §7・§8）。

## 9. 次のフェーズの提案（承認を求めるタスク ID）

Phase 2（Workflow と観測）、ゲート G1b（再現できる端から端までのトレース、否定テスト、Executor に業務ごとの分岐がないこと）。

| タスク | 内容 | 担当（提案） | 証跡 |
|---|---|---|---|
| P2-01 | Composer（型付き DAG）と構成の検証 | CC | グラフ検証のテスト |
| P2-02 | Executor とアダプタ（実行の状態遷移・安全な失敗・ローカル実行） | CC | 実ノードの実行、失敗時の扱い |
| P2-03 | 実行・確認（review）の画面 | Codex（使えなければ CC、D-011） | トレースと確認の画面 |
| P2-04 | Executor の敵対的テスト（時間切れ・不正な形式・危険な入力） | Codex（使えなければ CC、D-011） | 自動テスト |

着手の前提：G1a の承認、§8-3（テスト専用 DB）の扱い、§8-1（独立レビュー）の扱い。

## 10. 人に決めていただきたいこと

1. G1a の承認、または差し戻し。
2. 独立レビュー（§8-1）を Phase 2 の前に行うか、並行にするか、省略して自己レビューのまま進めるか。
3. Phase 1 の人の作業時間（`HUMAN_TIME_LOG.csv`）の記入。
4. Phase 2 のタスク P2-01〜P2-04 の承認と、P2-03・P2-04 を Codex に渡すかどうか。
