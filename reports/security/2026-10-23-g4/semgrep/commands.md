# 実行コマンド（PowerShell）

リポジトリルートから実行。対象コミットは `e0d9250271fccfe5fcd0ea197c3e2c5adcf4ddf1`。Dockerの標準出力・標準エラーを同名の `.log` に保存した。以下のコンテナはすべて `--rm`、CPU上限1。規則取得だけネットワークを使用し、検査は `--network none`。

```powershell
$root = (Get-Location).Path
$out = "${root}/reports/security/2026-10-23-g4/semgrep"
docker image inspect semgrep/semgrep:1.180.0 --format '{{.Id}} {{.Architecture}}'

docker run --rm --name easf-p503a-smoke-cli --network none --cpus 1 -v "${out}/smoke:/smoke:ro" -v "${out}:/out" --entrypoint sh semgrep/semgrep:1.180.0 -c 'timeout -k 5 40 semgrep scan --oss-only --disable-version-check --no-trace --metrics off --jobs 1 --debug --json --output /out/smoke-cli.json --config /smoke/rule.yml /smoke/input.py; code=$?; echo "$code" > /out/smoke-cli.exit; exit "$code"'

docker run --rm --name easf-p503a-rules --cpus 1 -v "${out}:/out" --entrypoint sh semgrep/semgrep:1.180.0 -c 'mkdir -p /out/rules; for pack in python owasp-top-ten react typescript secrets; do wget -T 20 -O /out/rules/$pack.yml https://semgrep.dev/c/p/$pack || exit 1; done; sha256sum /out/rules/*.yml'

docker run --rm --name easf-p503a-source --network none --cpus 1 -v "${root}/backend/app:/src/backend/app:ro" -v "${root}/frontend/src:/src/frontend/src:ro" -v "${out}:/out" -w /src --entrypoint sh semgrep/semgrep:1.180.0 -c 'timeout -k 5 180 semgrep scan --oss-only --disable-version-check --no-trace --metrics off --jobs 1 --debug --json --output /out/source.json --config /out/rules/python.yml --config /out/rules/owasp-top-ten.yml --config /out/rules/react.yml --config /out/rules/typescript.yml --config /out/rules/secrets.yml backend/app frontend/src; code=$?; echo "$code" > /out/source.exit; exit "$code"'

docker run --rm --name easf-p503a-smoke-pack --network none --cpus 1 -v "${out}:/out" --entrypoint sh semgrep/semgrep:1.180.0 -c 'timeout -k 5 40 semgrep scan --oss-only --disable-version-check --no-trace --metrics off --jobs 1 --debug --json --output /out/smoke-pack.json --config /out/rules/python.yml /out/smoke/input.py; code=$?; echo "$code" > /out/smoke-pack.exit; exit "$code"'
```

最後の切り分け試験は製品検査の実行中に開始したため、厳密な性能比較ではない。CPU1は各コンテナの上限であり、専用CPUの予約ではない。公開規則の取得URLは可変であるため、再取得したものは `rules-download.log` のSHA-256と照合する。規則本体は再配布せず、この実行で取得した5ファイルのみ診断後に削除した。
