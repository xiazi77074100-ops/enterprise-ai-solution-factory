# 道具とコマンド例

版によってオプションが変わる。**実行前に `--help` で確かめ、実際に使った版とコマンドを報告書に書く。** 出力は `reports/security/<YYYY-MM-DD>/` に保存する。

## 静的解析（SAST）

```sh
ruff check backend --select S --output-format json > sast/ruff-s.json
bandit -r backend/app -f json -o sast/bandit.json            # 重大度で絞るなら -ll
semgrep scan --config p/python --config p/owasp-top-ten --config p/react --config p/typescript \
  --json -o sast/semgrep.json backend frontend/src
npx eslint frontend/src -f json -o sast/eslint.json          # react/no-danger, no-eval などをエラーに
```

## 依存関係（SCA）・ライセンス

```sh
pip-audit -f json -o sca/pip-audit.json                       # 仮想環境の中で、またはロックから出した requirements を -r で
npm audit --omit=dev --json > sca/npm-audit.json              # frontend/ で
osv-scanner scan source -r . --format json > sca/osv.json     # v2 系。v1 系は `osv-scanner -r .`
pip-licenses --format=json > sca/licenses-python.json
npx license-checker --production --json > sca/licenses-node.json
```

## 秘密情報

```sh
gitleaks git --redact -v --report-path secrets/gitleaks-history.json     # v8.19 以降。旧版は `gitleaks detect`
gitleaks dir . --redact -v --report-path secrets/gitleaks-worktree.json
```

## コンテナ・設定

```sh
trivy image --severity HIGH,CRITICAL --format json -o container/backend.json easf-backend:assessment
trivy config --format json -o container/config.json .
```

## 動的診断（OWASP ZAP、Docker）

診断用の環境を起動し、テスト用アカウントでログインした Cookie と CSRF トークンを用意する（ZAP の認証設定、または `-z` でヘッダを付ける設定）。

```sh
# OpenAPI（ビルド時に出力したファイル）を元に API を診断
docker run --rm -v "$PWD/reports/security/<日付>/dast:/zap/wrk:rw" ghcr.io/zaproxy/zaproxy:stable \
  zap-api-scan.py -t /zap/wrk/openapi.json -f openapi -O http://host.docker.internal:8000 \
  -r zap-api.html -J zap-api.json

# 画面（受動スキャン中心のベースライン）
docker run --rm -v "$PWD/reports/security/<日付>/dast:/zap/wrk:rw" ghcr.io/zaproxy/zaproxy:stable \
  zap-baseline.py -t http://host.docker.internal:8000/ -r zap-baseline.html -J zap-baseline.json
```

- 能動スキャン（`zap-full-scan.py`）はデータを書き換えるので、捨ててよい合成データの環境でだけ行う。
- 対象は `host.docker.internal`（自分の PC）だけ。他のホストを `-t` に入れない。

## ヘッダの簡易確認

```sh
curl -sI http://localhost:8000/ | tee dast/headers-root.txt
curl -sI http://localhost:8000/api/v1/projects | tee dast/headers-api.txt
curl -s -X TRACE -o /dev/null -w "%{http_code}\n" http://localhost:8000/
```

## 自動テストへの組み込み

手動で見つけた指摘は、直す前に再現テスト（pytest / Playwright）を書き、`tests/security/` に置く。次の診断からは自動で確かめられるようにする。認可（C-01〜C-06）・CSRF（D-01）・ヘッダ（F-02）・開発用の入口（F-03）は最初から自動テストにする。
