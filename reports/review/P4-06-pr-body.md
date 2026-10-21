# security(g3): P4-06 自己診断と独立レビュー

P4-06：G3前の自己診断と独立レビューを提出する。自己診断であり第三者診断ではない。マージ・G3承認は行っていない。

## 範囲・変更ファイル

最新main `2b87f6f` から `codex/P4-06-g3-review` を作成。実装・診断のコミットは `c717f54c352696f4083917280888a423c306bc24`。

- `reports/security/2026-10-21-g3/`：report.md、全項目のmanual.md、道具のログ、再確認・秘匿化の補助スクリプト。
- `reports/review/2026-10-21-g3.md`：必須5観点すべての結論と指摘票。
- `backend/app/evaluation/score_outputs.py`：負の根拠位置を受理する不備の1行修正。不正な位置は従来の引用文検索で実位置を確定する。
- `backend/tests/security/test_g3_scoring.py`：armの対称性、捏造引用、負の添字、集計時の詳細除去のテスト。
- 本ファイル：PR説明の確定案。変更はすべて引き渡し書の許可パス内。

D-047の凍結対象・契約・所有者専用パスは `git diff --exit-code 71abf10 -- <対象>` 終了0。ホールドアウトを開かず・生成せず、ベースラインのコードも読んでいない。既存の集計JSONは変更なし。

## 実行したコマンド・結果

完全なコマンド・版・ログ・初回失敗は自己診断報告を参照する。

| コマンド・検査 | 終了・結果 |
|---|---|
| `ruff check backend/app --select S --output-format json`、`python -m bandit -r backend/app -f json` | 各0、検出0 |
| `python -m pip_audit -f json`、`npm audit --omit=dev --json` | 各0、既知脆弱性0 |
| gitleaks 8.30.1（`--config /repo/.gitleaks.toml --gitleaks-ignore-path /repo/.gitleaksignore`） | 履歴・ソース・提出物の最終検査0。ログ初回34件はURL30・公開GPG鍵ID4の誤検知として保持。相対パスで再検査0 |
| trivy 0.76.0 config / 再構築APIのimage | 各0、Dockerfile指摘0、脆弱性・秘密情報0 |
| 固定版 `ghcr.io/zaproxy/zaproxy:2.16.1` のAPIスキャン（未ログイン／認証付き） | 各0、FAIL0・PASS114・WARN1（ZAPの版）。情報アラートも記録。認証後200を確認、HTTP5xx0 |
| assessment APIへの手動HTTP確認 | 再実行0。CSRF、入口閉鎖、偽装415、パス名、添付ダウンロード、CORS、TRACE等。未実行項目も全IDに記載 |
| Linux Dockerの `uv sync --locked && uv run pytest -q`（easf_test専用） | **終了1：282 passed・1 error、1551.16秒** |
| `test_authorization_matrix[listCapabilities]` だけのLinux再実行 | 0、1 passed、17.50秒。全件実行の失敗は取り消さない |
| 修正後の採点・評価対象の `pytest -q` | 0、9 passed・1 skipped（WindowsにTesseractなし） |
| `npm run lint`、`npm run typecheck`、`npm run build`、`npx vitest run` | 各0、vitest10件成功 |
| mypy、最終ruff check / format --check、契約検査、skill同期、集計値照合 | 各0 |
| semgrep 1.180.0、同じ5規則 | **未完了**。通常・OSS・実験エンジン・ローカル規則で結果が得られず各コンテナ停止（137）。検出0とは扱わない |
| `git diff --cached --check`、変更パス検査、commit / push | 各0 |

Linuxの1エラーは認可試験の共通fixtureで確認タスクを取得できないStopIteration（test_openapi_contract.py:348）。本体は未実行。単独では再現せず、原因は不明（要確認）。失敗ログのDB接続値は秘匿化済み。

## 未実行・制約

- semgrep未完了。SAST全ツールの完了を主張しない。
- 契約書の実画面の確認・修正と画面DASTは未実行。模擬APIのE2Eを実画面確認と数えない。
- 実LLM・外部接続は保留、公開TLSは対象外。ホールドアウト再評価・ベースラインのコードレビューは指示により未実行。
- 最終コミットのCI結果は未確認。ローカルLinux全件の記録と区別する。
- 人の時間は未測定。許可パス外の台帳は更新していない。人がarm=shared / task_id=P4-06を記録する必要がある。

## リスク・引き渡し

無条件のG3承認は推奨しない。

1. RV-G3-001：同じCapability版の実装が変わる既知の制約。IDの不変性だけでは過去実装の再現性を証明しない。
2. RV-G3-002：負の根拠位置は修正済み。ただし修正前のホールドアウト集計への影響は不明。集計を書き換えず、人がG3での扱いを判断する。
3. RV-G3-003：再利用テストは同一案件の2 Workflowで4ノードの版IDを比較しており、別案件・exporterまでの証跡とは区別する。
4. 全件回帰の1セットアップエラーとsemgrep未完了。OCR環境差、12件・比較1回、M1推定、根拠網羅0.784等の既存の限界も維持。

追加現金支出0円、有料APIなし。診断用利用者は無効化、一時認証情報は削除、今回起動したAPIは停止済み。CCが確認・統合し、人がG3を判定する。
