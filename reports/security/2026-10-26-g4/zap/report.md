# ZAPによる時間上限付き部分診断（P5-03g）

2026-10-26、Codex。**自己診断であり第三者診断ではない**。基点 `5db3134abe3b7d44bf1000120820d6452ca0ddfb`。製品イメージ `sha256:776a46f480342fe9f07347471e8ee3a96b4a9a779ba02166cc39808b0681deac`、ZAP `ghcr.io/zaproxy/zaproxy:2.16.1`。製品・契約・依存・D-047の凍結構成は変更なし。G4承認・判定は行わない。

## 実行結果

| 実行 | exit | ZAP表示 | ZAP履歴の採取 | 中/高alert |
|---|---|---|---|---|
| 未認証OpenAPI診断（能動＋受動） | 0 | FAIL 0・WARN 0・PASS 106 | 6,631要求、5xx 0 | 0 |
| 認証付き受動ベースライン | 0 | FAIL 0・WARN 0・PASS 57 | 7要求、5xx 0 | 0 |

PASSはZAPが表示した規則の集計であり、テストケース数や全規則の完了保証ではない。未認証側は54 URLの取り込みをログで確認。JSONの情報alertは「Client Error response」「Authentication Request Identified」の2種類（riskcode 0）。認証付き側のJSON alertは0。CLIのWARN集計と情報alertを区別する。

認証付き側では、**ZAP自身の履歴でCookie付き `GET /api/v1/projects` の200を1件確認**。未認証なら401になる非公開APIへの到達の証拠であり、認証後の全API・全ロール・能動検査の証拠ではない。hookは要求メソッド・パス・状態・Cookie存在の真偽だけを保存し、ヘッダ値・応答本文を保存しない。採取上限10,000件に対し上記件数であり、上限以上の履歴を確認したとはしない。

同じ専用環境で既存のHTTP24項目も再実行し、`checks=24, failed=False, cleanup_failed=False`、全体exit 0。2ユーザーの無効化、API・DBの削除、専用ネットワーク削除、既存コンテナID集合の前後一致を確認した。

## 重要な解析制約

能動検査には **ascan全体4分・規則ごと1分**、スキャナプロセスに10分の上限を設定した。ZAPのactive scan完了状態・規則の省略・上限到達理由は記録していない。したがって **全面診断・全規則の完了は未確認**。exit 0・FAIL 0・PASS件数だけで網羅性を判断しない。今回の成果は有界な実行結果と認証後の限定到達証拠である。

ZAPは既存の固定旧版。安全な隔離のため更新確認・自動ダウンロードを無効化し、外向き接続も遮断した。今回WARN 0でも、G3で記録した「ZAP is Out of Date（10116）」の制約が解消されたとはしない。ツールの最新性・現在の全脆弱性検出を保証しない。規則・アドオンを追加更新した検査は未実行。

## 範囲と隔離

- `http/assess.py` の専用DB・API・HTTP24項目・後始末を再利用。後処理callbackと実行ラベルだけを追加し、以前の結果ファイルは上書きしない。直接実行時の既定値はP5-03fのまま。
- DB名 `easf_p503g_test`、一意なDB/API、DMLロール・非root・read-only・cap-drop ALL。入力文書は既存devの合成PDFだけ。Windows側APIは127.0.0.1限定。
- ZAP用に `easf-p503g-88dab8f3baf6-scan` を `--internal` で作成し、今回のAPIだけを追加接続。スキャナにはこのネットワークだけを付与。`host.docker.internal` を **このAPIの内部IPへ固定対応付け**し、`http://host.docker.internal:8000` のみを対象にした。通常のホスト名解決先や第三者サーバへ診断を向けたものではない。
- 契約のOpenAPIを読み取り、スキャン用コピーのserversだけを上記URLへ変更。元のcontractsは変更なし。未認証診断にはCookieを渡さず、認証付きベースラインだけ一時propertiesでCookie・CSRF・Originを付与。
- 一時領域はOS temp配下に今回専用の接頭辞で作成。スキャナ停止後、解決済み絶対パスが指定temp親直下・専用接頭辞であることを検証して削除。`zap-execution.json` は一時領域削除true、cleanup_errors空。スキャナ用内部ネットワークの切断・削除もexit 0。
- `docker rm --force` のstderrに「No such container」があるのは、`--rm` による既削除後の確認。最終的なコンテナ一覧も前後一致。ログ表示だけで残存の有無を推測しない。

## 証跡とコマンド

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
backend/.venv/Scripts/python.exe reports/security/2026-10-26-g4/zap/run.py
backend/.venv/Scripts/ruff.exe check reports/security/2026-10-26-g4/http/assess.py reports/security/2026-10-26-g4/zap
backend/.venv/Scripts/ruff.exe format --check reports/security/2026-10-26-g4/http/assess.py reports/security/2026-10-26-g4/zap
```

診断はexit 0。固定イメージ内の両スクリプトを `-h` で確認し、`api-help.txt`・`baseline-help.txt` に保存。未認証は `zap-api-scan.py -t /zap/wrk/openapi.json -f openapi -T 3 -J report.json --hook /zap/wrk/evidence_hook.py -z "-configfile /zap/wrk/scan.properties"`。認証付きは `zap-baseline.py --autooff -t http://host.docker.internal:8000/api/v1/projects -m 1` と同じT/J/hook/config指定。設定の秘密値は引数に入れない。

実際のDocker引数・終了コード・秘匿化出力は `zap-execution.json`、DB/API・管理CLI・後始末は `execution.json`。ZAPごとのrun.txt・report.json・counts.json・request-evidence.jsonを併記。生レポートと一時propertiesは提出せず、生成した秘密値を置換したコピーだけを保存した。gitleaks v8.30.1の成果物検査はexit 0・検出0（`gitleaks.json`・`gitleaks.log`）。既存の除外規則は追加・変更していない。

提出前の `git diff --cached --check` は、ZAPのヘルプと整形済みJSONの行末空白で初回exit 2となった。診断値を変えず、テキスト成果物の行末空白・改行を正規化して再確認した。

固定ZAPイメージのコンテナhealthは実行中にunhealthyを観測した。標準healthcheckは `http://localhost:$ZAP_PORT/` を参照し、試しに8090へ接続した結果は拒否だった。実際の診断API待受との対応は未確認であり、health表示だけで診断成功・失敗を判定しない。今回のimport・結果JSON・exit・要求履歴を実行の証拠とする。

## 並行レビューと未実行

読み取り専用の別Codexエージェントが、時間上限・管理CLIのタイムアウト・ログ取得失敗判定の制約を指摘した（`peer-review.md`）。今回の管理CLIは全件正常終了し、API状態とログ取得も個別exit 0を確認。無名管理CLIのタイムアウト回収保証・観測失敗時の終了判定の改善は**未実装・未検証**。正常実行の後始末から一般的保証へ広げない。

全面・認証後全APIの能動診断、HTTPS/Secure Cookie/HSTS、実画面の契約書フロー、別案件/exporterの永続trace、保持削除の全体検証、SAST/SCA/Trivy・ライセンスの全面再診断は今回**未実行**。有界なZAP検査の範囲外であり、既存の証拠と区別する。RV-G3-001は[CC向け変更要求案](../../../review/2026-10-26-version-change-request.md)を準備しただけで未解消。旧評価への影響・semgrep警告・過去setup error等の残事項も維持。

ホールドアウトを開く・生成する・マウントすること、baselineコードの閲覧、有料API、外部公開はしていない。ユーザーはCLIの接続先不明・並行エージェント継続を選択し、別Claude Codeプロセスは起動していない。追加現金支出0円、人の時間は未測定。
