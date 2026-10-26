# 契約書の実画面試験（P5-03l）

2026-10-26、Codex。基点 `65e0a2124486b0a3f0d50b63e8a7205a99528b88`、ブランチ `codex/P5-03l-contract-ui`。**一連フローは失敗。AC-07/12/13の完了証拠にはできない。** 自己診断であり第三者診断ではない。G4は未承認のまま。

## 実行結果

既存Chromeの新規コンテキスト、1440×900、ja-JP、Asia/Tokyoで、APIの差替えなしにUvicorn・独立worker・Viteへ接続した。専用の `easf_p503l_test` DB、合成利用者2名、既存dev `con-0001.pdf` だけを使用。要件と解決策の登録・別人承認はAPIで事前準備し、ブラウザーでログイン・文書登録・実行を行った。

| 実行 | 結果 | 証拠 |
|---|---|---|
| 初回 | exit 1。試験用Vite設定の相対パス誤り。ブラウザー未実行 | `attempt-1/` |
| 2回目 | exit 1。試験用設定のCommonJS/ESM読込不整合。`.mts`へ修正 | `attempt-2/` |
| 3回目 | E2E exit 1、24.9秒。ログイン後の遷移を5秒で確認できず。ブラウザーからのPOSTはAPIログになく、原因未確定 | `attempt-3/playwright.log` |
| 4回目 | E2E exit 1、約3.5分。ログイン応答を待つ手順でログイン・SVG拒否・PDF登録・実行開始まで到達。独立worker停止により確認待ちに到達せず | `playwright.log`、`worker.log`、`execution.json` |

4回目は登録201、実行202。文書の合成データ表示・SHA一致、未選択時の登録/実行ボタン無効、SVG拒否を試験内で確認した。画面の証拠は [文書登録後](01-document-registered.png)。目視で日本語の案件名・文書名・承認済み解決策・合成データ/検証用表示を確認した。全体の横はみ出しは登録後の撮影時に0。画面全般の合格とはしない。

専用DBから本文・認証情報を含まないメタデータだけを別途採取した。

- 実行ID：`f9bd3f88-7de0-416c-b7e7-367d94191724`
- 案件ID：`be09a5fc-cd64-4cfd-9458-c929a1063b65`
- trace ID：`41f95f57ffbf4e2d894a2e05a7c9c90a`
- 実行状態：`pending`、6ノードすべて`pending`、確認タスク0件、イベント1件。`execution_mode=real`は予定した方式であり、実処理が完了した証拠ではない。
- 採取結果：`partial-db-run.json`、`partial-db-nodes.json`。

## 指摘 RV-G4-UI-001：独立workerのモデル登録不足（高・機能阻害）

`python -m app.executor.worker` は起動するが、実行の取得時に `NoReferencedTableError` で停止した。`run.created_by` の `app_user.id` 参照をPython側のSQLAlchemy metadataで解決できない。DB上の表不存在と同一視しない。

DBに接続しない新規Pythonプロセスでも、workerだけのimport後に`app_user`への未解決外部キー12件を再現した。診断プロセス内だけで `app.auth.models` を追加importすると0件になる（`model-repro.json`）。これは修正候補の切分けであり、製品修正・workerの実行成功ではない。

既存のTestClient統合試験はAPI入口のimportを通じて認証モデルを同じプロセスへ登録する。その後でExecutorを直接動かすため、独立workerのimport不足を覆い隠し得る。P5-03kの成功を撤回するものではないが、独立workerまで動いた証拠として拡張しない。

workerはCC所有であり、D-053の限定代行範囲にも含まれない。今回の許可パス外なので未修正。[変更要求](change-request.md)に最小候補と回帰試験を記載した。D-047・契約・manifest・業務実装は変更していない。

## コマンドと検証

リポジトリ直下から実行。PowerShellのパス表記は省略していない。

| コマンド | 結果 |
|---|---|
| `.\backend\.venv\Scripts\python.exe reports/review/2026-10-26-contract-ui/run.py` | 4実行ともexit 1。各回のDocker・migration・利用者作成のコマンド/終了コードは各`execution.json`。秘密は環境変数/SQL標準入力で渡し、ログは秘匿化 |
| `npm.cmd run typecheck`（cwd `frontend`） | 初回exit 1（Workflow型変換）、修正後exit 0。診断追加後もexit 0 |
| `.\backend\.venv\Scripts\ruff.exe check reports/review/2026-10-26-contract-ui/*.py` | 初回import整列/noqa指摘は修正。最終exit 0 |
| `.\backend\.venv\Scripts\bandit.exe -q reports/review/2026-10-26-contract-ui -r -s B404,B603` | exit 0。固定コマンド/引数配列と所有PIDを手動確認し、subprocess import/実行の2規則は明示除外 |
| `.\backend\.venv\Scripts\python.exe reports/review/2026-10-26-contract-ui/model_repro.py` | exit 0、未解決12件→診断import後0件。DB未接続 |
| `docker exec <今回の専用コンテナ> psql -U easf_owner -d easf_p503l_test -Atc <固定SELECT>` | exit 0、run/ノード状態・件数のみ採取。SQL対象を専用DBに限定 |

後始末：全4回で専用DBコンテナ・専用一時領域を削除、前後の既存コンテナ一覧は一致。2回目にAPI/worker停止コマンド非ゼロを記録し、追加のプロセス一覧で残存なしを確認。3回目もAPI停止255だが親停止、4回目のcleanup_errorsは空。既存DBの内容を網羅比較したという意味ではない。個人Chromeプロファイルは開いていない。

最終のruff・bandit・DB未接続再現・TypeScript検査はすべてexit 0（`validation.json`と各`validation-*.log`）。manifest・worker・凍結設定・dev PDF・E2EのSHAも同JSONに保持。Gitleaks v8.30.1の新規成果物ディレクトリ検査はexit 0・漏えい0件（`gitleaks.json/log`）。新規ログの改行と行末空白だけを整え、失敗内容は保持した。これらの静的検査成功をE2E成功に読み替えない。

## 未実行とリスク

- **修正承認・コメント2001文字拒否・根拠位置/照合済み表示・JSON/CSV出力の照合は未実行**。worker停止により未到達。テストコードを書いたことを成功に数えない。
- 6ノードの完了、修正後trace、出力内容、最終ページのエラー件数0も未確認。`evidence.json`や成功時のexportファイルは生成されていない。
- モバイル・他ブラウザー・原文ビューアー・全入力型は未実行。対象はデスクトップChrome1サイズ、既存UIには原文ビューアーの操作がない。
- 全面DAST・第三者診断・品質評価・ホールドアウト再評価・baselineコード確認は未実行。今回の目的外であり、禁止されたデータ/コードは開いていない。
- 既存CIが成功しても独立worker入口の問題は残る。AC-12、RV-G3-001/002、保持・配布来歴など他のG4残事項は未解消。

追加サービス購入0円。人の時間とモデルの追加請求は未測定。失敗を保持したまま、次は別範囲のworker修正と独立プロセス回帰・同じUIシナリオの再実行が必要。
