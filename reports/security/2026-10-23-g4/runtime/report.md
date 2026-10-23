# 修正後イメージの自己診断（P5-03e）

2026-10-23、Codex。基点 `147584220ce7c2eff3e4bfac0c77ce0cf71f3cae`。**自己診断であり第三者診断ではない**。G4の合格・承認は行わない。追加支出0円、人の時間は未測定。

## 結論

VA-G4-001の修正を含む製品イメージで、通常・連鎖・SQLAlchemyの合成例外3ケースは成功。実装ファイルのSHA-256は現行ソースと一致し、UID 10001で動作した。キャッシュありの初回ビルドではmusl系2パッケージに同一CVEを検出した。Dockerfileを変更せずキャッシュなしで再ビルドすると修正版へ更新され、TrivyのOS・Python検出はともに0件。失敗・初回結果も保持する。

| 項目 | 初回 p503e | キャッシュなし p503e-refresh |
|---|---|---|
| イメージID（manifest list） | `sha256:1c0396d6636f824ba193da20cf29f6aee5803276a00a577b6b35c8c82ceeecc5` | `sha256:776a46f480342fe9f07347471e8ee3a96b4a9a779ba02166cc39808b0681deac` |
| 構成 | linux/amd64、USER easf | 同左 |
| ミドルウェアSHA-256 | `4c5d424d0259dd26d14227dbd9a78aac361b8f10688a6db4d132e81f5b4837aa` | 同左 |
| 合成例外診断 | 3成功、exit 0 | 3成功、exit 0 |
| musl / musl-utils | 1.2.6-r2 | 1.2.6-r3 |
| Trivy 0.76.0 | OS 2件、Python 0件、exit 1 | OS 0件、Python 0件、exit 0 |

旧 `easf-backend:local` は `sha256:ac856a1f1e82b43f4d3dae608646281f3e39225dcecbf52214ecdff44b9e5e2c` のまま。新タグへの置換・既存APIへのデプロイはしていない。イメージIDは実行環境の識別であり、同じGitコミットから同じOS依存が再現される保証ではない。

## 初回指摘と再診断

初回は `CVE-2026-107891`、musl・musl-utils、修正版1.2.6-r3、重大度UNKNOWN。Trivyには「詳細なし、CVEが却下された可能性もある」とする一般的な警告があり、却下されたと断定しない。詳細な攻撃条件・CVSSは**不明（要確認）**。CVSS v3.1の値・ベクトルを推測で補わない。

[Alpine v3.24 mainの公式データ](https://secdb.alpinelinux.org/v3.24/main.json)をPowerShellで取得し、muslのsecfixesに同じCVEと1.2.6-r3が登録されていることを照合した（`alpine-musl.json`）。Web閲覧ツールでは公式CVEページ・Alpine JSONとも取得できなかった。公式JSONのHTTP取得は成功。初回build.logではapk実行レイヤーを再利用、build-refresh.logではmusl・musl-utilsのr2→r3更新を確認。再診断JSONにもr3を記録。コード変更や例外登録による検出抑制はしていない。

検出は2パッケージ・1CVEであり、独立した脆弱性2種類とは数えない。診断対象の新イメージでは対応を確認したが、旧タグ・他の配布物の解消やCVEの詳細な危険性判断を主張しない。以後のビルドではapk実行レイヤーの鮮度を確認し、古いキャッシュを使った結果を最新依存の検査としない。CIやDockerfileの変更要求は本タスクでは実装しない。

## 動作確認

`check_image.py` は既存 `error-log/check_logs.py` の3ケースを再利用し、製品イメージ内の実装を読み込む。ホストのappやDB・環境ファイルはマウントしない。ログ・応答への合成値混入なし、例外オブジェクト添付なし、型・trace_idのテキストと構造化表示・応答一致・コンテキスト復元を確認。`cached-result.json` が初回、`candidate-result.json` が再ビルド後。candidateというラベルは既存ヘルパーの出力名であり、隔離した製品コピーへのパッチ適用ではない。

`check_routes.py` は実際の `create_app(Settings(env="assessment"))` をASGIとして呼び出し、health 200、docs・redoc・openapi.json・.env・.git/config 404、案件一覧401を確認。7経路でnosniff・DENY・trace_id、APIでno-store。外部通信なし・未使用のテストDB URL・一時生成した秘密鍵だけを使用。認証依存やDBを差し替えてはいない。初回補助スクリプトはhealthにもno-storeを要求してexit 1となった。既存仕様ではAPIだけに付くため検査側を訂正し、7経路exit 0。`routes-initial-check.log` に失敗を保持。製品は変更していない。

## 実行コマンドと結果

リポジトリ直下のPowerShell。`$outDir` は本ディレクトリの絶対パス、`$checksDir` は `reports/security/2026-10-23-g4/error-log` の絶対パス。

```powershell
docker build --progress=plain -f backend/Dockerfile -t easf-backend:p503e .
docker run --rm --network none aquasec/trivy:0.76.0 image --help
docker image inspect easf-backend:p503e --format '{{.Id}} {{.Config.User}} {{.Os}}/{{.Architecture}}'
docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges --tmpfs /tmp:size=64m -e PYTHONPATH=/app/backend -v "${checksDir}:/checks:ro" -v "${outDir}:/out" easf-backend:p503e python /out/check_image.py
docker run --rm --mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock,readonly -v "${outDir}:/out" aquasec/trivy:0.76.0 image --timeout 5m --scanners vuln --exit-code 1 --format json --output /out/trivy-image.json easf-backend:p503e
Invoke-RestMethod -TimeoutSec 30 -Uri 'https://secdb.alpinelinux.org/v3.24/main.json'
docker build --no-cache --progress=plain -f backend/Dockerfile -t easf-backend:p503e-refresh .
```

上記はTrivyの初回検出exit 1以外exit 0。再ビルド後はinspectとcheck_imageのタグを `p503e-refresh` に変更して再実行（exit 0）。Trivyも同タグに変更、`--no-progress` を追加し出力を `trivy-refresh.json` に変更（exit 0）。同じ診断用制限・マウントで `python /out/check_routes.py` を実行（上記の初回1→訂正後0）。

`docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges easf-backend:p503e-refresh apk info -v musl musl-utils` は終了したが、ネットワークなしでAPKINDEXのDNS警告が出て版を表示しなかった。`musl-refresh.txt` を版の証拠に使わず、build-refresh.logとTrivyのパッケージ一覧で照合した。ruff checkは初回B023を検査補助で訂正し最終0、formatは初回整形要求1→整形後0。対象は本ディレクトリのPython2ファイル。

## 範囲・制約・未実行

- 成果物の秘密情報検査：`docker run --rm --network none -v "${outDir}:/scope" zricethezav/gitleaks:v8.30.1 dir /scope --no-banner --redact --report-format json --report-path /scope/gitleaks.json` はexit 1、4件。すべてTrivyの2つのJSON内のPython基底イメージの `ENV GPG_KEY`（公開鍵の40桁フィンガープリント、各JSONの履歴・環境に同値2箇所）で、秘密鍵・API認証情報ではないと分類した。設定・除外規則は変更せず、伏字付き指摘JSONを保持。未分類0件、実秘密の確認0件。「gitleaks検出0」とは書かない。最初の `/dev/stdout` 指定はexit 1・指摘4件のログを出したがホストJSONが空だったため、ファイル出力へ訂正して再実行した。
- Trivyは `--scanners vuln`。秘密・設定・Dockerfileの再診断は**未実行**（別検査として区別）。脆弱性DBは各実行で取得し、JSONの作成時刻・ログを保持。全重大度が対象、ignore-unfixedや例外抑制は使わない。
- Dockerソケットの読み取り専用マウントはマウント先の変更抑止であり、Docker API自体の権限制限ではない。固定した既存Trivyイメージによる指定イメージの検査だけに使用した。
- HTTPサーバ越しのDAST・認証後API・DB接続/readiness・アップロード・業務実行・画面操作は**未実行**。専用DB・文書領域と診断ユーザーの環境が必要で、既存データへの能動スキャンを避けた。ASGI7経路をZAPやHTTP経由の成功とは呼ばない。
- 全件pytest・SAST・フロントエンド検査のローカル再実行は**未実行**。製品ソースを変更していないため、今回の局所確認と後続CIを区別する。過去のsetup error、semgrep警告、保持・削除・ライセンスの残事項は未解消。
- 一時コンテナは `--rm`、実行中の既存DB2台と旧タグを維持。専用DB・永続ボリューム・診断ユーザー・API公開ポートは作成していない。新しい診断用イメージ2タグだけを保持した。ホールドアウト・baselineコード・D-047の構成にはアクセス・変更していない。
