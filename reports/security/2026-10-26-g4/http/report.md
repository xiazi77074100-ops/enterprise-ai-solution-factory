# 専用環境でのHTTP API自己診断（P5-03f）

2026-10-26、Codex。**自己診断であり第三者診断ではない**。対象ソースは `a0fe780dff1b63f9a1a6b128cdda9124421e8410`、製品イメージは `sha256:776a46f480342fe9f07347471e8ee3a96b4a9a779ba02166cc39808b0681deac`（P5-03eのキャッシュなし再ビルド）。製品・依存・契約・D-047の凍結構成は変更なし。G4判定・承認は行わない。

## 結論と証拠

最終実行は **24検査成功、exit 0、後始末成功**。モックやASGI直呼びではなく、Uvicornと実PostgreSQLを使用したローカルHTTP診断。`http-summary.json` に結果・案件ID・文書ID・dev PDFのSHA-256、`execution.json` に実行コマンド・終了コード・秘匿化した出力・起動待ち・後始末を保持。HTTP応答本文・Cookie・CSRFトークン・パスワードは証跡へ保存していない。

| 観点 | 実測結果 |
|---|---|
| 起動・DB接続 | health / ready 200。アプリはeasf_appロールで接続 |
| 開発情報 | docs・redoc・openapi.json・.env・.git/config は404 |
| 認証 | 未認証の案件一覧401、診断ユーザー2人のログイン200、認証後一覧200 |
| CSRF | トークンなし403、異なるOrigin403、正規の案件作成201 |
| 案件認可 | 無関係な利用者からの案件参照404、一覧にも当該IDなし |
| 文書 | HTMLをPDFと偽装した登録415。既存dev合成PDFを `../../probe.pdf` の表示名で登録201、認可付き取得200・元バイト列と一致・attachment。他利用者の取得404 |
| HTTP境界 | TRACE 405、異なるOriginへのCORS許可なし。検査応答にnosniff・DENY・trace_id、Serverなし、APIはno-store |
| セッション | CookieはHttpOnly・SameSite=Lax。ログアウト204、以後の案件一覧401 |

24件は検査項目数で、API操作数や全面的な権限表の網羅数ではない。検査24件で5xxなし。起動待ちでは初めの24回がRemoteProtocolError、その次のhealthが200だった。この待機中の接続エラーを、診断成功件数に含めない。

## 環境と後始末

- Docker Serverの版は `execution.json` のversionコマンドに記録。ホストはPython 3.12.12 / httpx2 2.14.0（`client-version.txt`）。
- 一意なネットワーク `easf-p503f-e161408bee58` に、専用DBとAPIだけを接続。DB名 `easf_p503f_test`。PostgreSQLはtmpfs、外部公開ポートなし。マイグレーションはこのDBの所有者ロールだけで実施し、APIはDMLロールを使用。
- APIはイメージ既定の非root、読み取り専用、cap-drop ALL、no-new-privileges、CPU 1・メモリ512 MiB。文書と一時領域は専用tmpfs。空きポートをOSで確認後、127.0.0.1限定で明示。クライアントは `trust_env=False` で環境変数のプロキシを使用しない。
- bridgeネットワークは外向き通信を遮断する設定ではない。本スクリプトのHTTP接続先は127.0.0.1だけ。ネットワーク全体のパケット監視は未実行。
- 2ユーザーを作成成功後に記録し、finallyで両方の無効化を確認。自分が作成したAPI・DBを削除し、専用ネットワークも削除。既存のEASF・他案件DBのコンテナID集合が前後一致。
- 秘密はメモリとプロセス環境で生成・受渡し。Dockerの引数には環境変数名だけを指定し、SQLの秘密値は標準入力へ渡して本文は記録しない。出力を既知の生成秘密値で秘匿化してからJSONへ保存する。
- 論理的な後始末の確認であり、メモリ・swap・ホストの物理的消去を保証するものではない。全体の保持・削除方針は残事項。

## 失敗した実行と切り分け

| 実行 | 結果・保持した証跡 |
|---|---|
| 1 | internalネットワーク・自動ポートで `docker port` exit 1。24検査未着手、全体exit 1。`initial-execution.json` |
| 小さな再現 | DB・秘密なしのhttp.serverでもrunning、HostConfigにはHostPort 0、NetworkSettings.Portsは空。公開ポートなしを確認。`network-probe.txt` |
| 2 | bridge・自動ポートではportコマンドexit 0だが出力が空。安全側に停止、24検査未着手、全体exit 1。`bridge-dynamic-execution.json` |
| 明示ポートの再現 | DB・秘密なしのhttp.serverで127.0.0.1:62153へのHTTP 200、ポート情報一致。`network-explicit-probe.txt` |
| 3 | bridge・明示ポートで公開を確認したが、health 200の待機上限30回に到達。24検査未着手、全体exit 1。`explicit-startup-execution.json`。起動待ち個々の応答は当時保存しておらず不明 |
| 4（最終） | ローカルのプロキシ利用を明示的に無効化、待機上限120回・起動状態とログの取得を追加。healthはattempt 24で200、その後24検査成功。`execution.json`。取得時APIはrunning・exit 0・OOM false、正常な起動ログ |

失敗3回とも2ユーザーの無効化・当該資源の削除・既存コンテナID維持を確認。切り分け用2コンテナとネットワークもfinallyで削除した。自動ポートの空出力と起動時間の根本原因は**不明（要確認）**。待機上限とプロキシ設定を同時に変えたため、成功をどちらか単一の効果と断定しない。ホストのHTTP_PROXY / HTTPS_PROXYの存在だけを確認した結果はいずれもfalseで、プロキシが原因だったとは主張しない。

3回目の後にログ取得を試した時点では既にAPIが削除されており、`api-observation.txt` はNo such containerの記録で、起動ログの証拠ではない。最終実行の後の独立health確認も削除後で未成立。どちらもHTTP成功へ数えない。最終実行はスクリプト自身が削除前に状態とログを取得した。

## コマンドと結果

リポジトリ直下のPowerShell。診断は既存venvだけを使用し、新しい依存を追加しない。

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
backend/.venv/Scripts/python.exe reports/security/2026-10-26-g4/http/assess.py
backend/.venv/Scripts/ruff.exe check reports/security/2026-10-26-g4/http/assess.py
backend/.venv/Scripts/ruff.exe format --check reports/security/2026-10-26-g4/http/assess.py
```

診断の最終出力は `checks=24, failed=False, cleanup_failed=False`、exit 0。ruff check / format最終ともexit 0。初回の検査補助にはBLE001（広い例外捕捉）と整形要求があり、明示した例外型と整形へ訂正してから実行した。実際のDocker引数・各終了コードは各execution JSONのcommandsを参照。生成したSQL本文と秘密値は再現コマンドに含めない。

## 未実行と残事項

- 成果物のgitleaks v8.30.1検査はexit 0・検出0（`gitleaks.json`、`gitleaks.log`）。実行は `docker run --rm --network none -v "${outDir}:/scope" zricethezav/gitleaks:v8.30.1 dir /scope --no-banner --redact --report-format json --report-path /scope/gitleaks.json`。`$outDir` は本ディレクトリの絶対パス。既存の除外設定を追加・変更していない。
- 全面ZAP APIスキャン・認証付きZAPベースラインは**未実行**。本タスクは専用環境と限定24項目のHTTP診断であり、自動スキャナの網羅を代用しない。
- HTTPS・Secure Cookie・HSTS、セッション固定/期限切れ/ロック、全ロールの認可表、サイズ超過や全危険PDF形式、プロンプトインジェクションは今回**未実行**。ローカルHTTPと限定項目を対象にしたため。既存の試験・診断と混同しない。
- 実画面・契約書Workflowの実行・確認修正・根拠・出力、別案件でexporterまでの再利用traceは**未実行**。API境界の診断であり、業務の一連の証拠ではない。
- SAST・SCA・Trivy・ライセンスの全面再診断、ローカル全件pytestは今回**未実行**。製品・依存を変えていないため、本タスクの局所検査と後続CIを区別。10月23日のイメージ検査を10月26日の最新脆弱性検査とは呼ばない。
- RV-G3-001の版と実装の不変性、RV-G3-002の旧評価への影響、semgrep警告・過去のsetup error・来歴・配布表示・全体の保持削除は未解消。ホールドアウト・baselineコードにはアクセスせず、G4の証拠不足という結論を維持する。

追加現金支出0円、人の実時間は未測定。AIの実行時間を人の工数へ換算しない。
