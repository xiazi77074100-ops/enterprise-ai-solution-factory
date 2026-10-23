# P5-03b 実行記録

2026-10-23、対象 `97e7c727ccc30b1b37caf3335be6db8c162c5696`。PowerShell、リポジトリルート。製品のテスト・診断結果と、今回の抽出スクリプトの検査を区別する。

| コマンド・照会 | 終了コード・結果 |
|---|---|
| `git fetch origin main` → `git merge --ff-only origin/main` → `git switch -c codex/P5-03b-license-review` | 各0、97e7c72から作成 |
| `backend/.venv/Scripts/python.exe reports/security/2026-10-23-g4/licenses/inventory.py` | 0、inventory.json・summary.jsonを生成。整形後にも再実行し0 |
| `backend/.venv/Scripts/ruff.exe format reports/security/2026-10-23-g4/licenses/inventory.py` | 0、1ファイル整形 |
| `backend/.venv/Scripts/ruff.exe check --select E,F,I,B,UP,S,SIM,N reports/security/2026-10-23-g4/licenses/inventory.py` | 初回1（日本語scopeのE501）、短くして再実行0 |
| `backend/.venv/Scripts/ruff.exe format --check reports/security/2026-10-23-g4/licenses/inventory.py` | 0 |
| `backend/.venv/Scripts/python.exe scripts/sync_skills.py --check` | 0 |
| `docker image inspect easf-backend:local --format '{{.Id}}'` | 0、backend-image.txt |
| `docker run --rm --name easf-p503b-os --network none --read-only --entrypoint sh easf-backend:local -c 'awk ''/^[PVL]:/ {print} /^$/ {print}'' /lib/apk/db/installed'` | 0、os-packages.txt、78項目 |
| 下記Python配布メタデータ取得 | 0、image-python.json |
| `Get-FileHash -Algorithm SHA256`（asset-hashes.jsonに記載した9パス） | 成功、現物ハッシュ。取得時の来歴は別 |

```powershell
docker run --rm --name easf-p503b-python --network none --read-only --entrypoint python easf-backend:local -c 'import importlib.metadata as m,json; print(json.dumps([{ "name":d.metadata["Name"],"version":d.version,"license_expression":d.metadata.get("License-Expression"),"license":d.metadata.get("License"),"license_classifiers":[c for c in d.metadata.get_all("Classifier",[]) if c.startswith("License ::")] } for d in m.distributions()],ensure_ascii=True,indent=2))'
```

読み取り時の不成功：PowerShellでBash形式の波括弧展開を書いた初回コマンドは構文エラーexit 1（実行前）で、個別パスへ修正して再実行した。また、存在しない `adapters/rest.py`・`registry.py`・`project/repository.py`・`frontend/src/index.css` を照会してエラーとなった。`rg --files` で実際の配置を確かめ直した。これらを検査成功に数えていない。

ライセンス本文の参照はローカルの配布内のファイルから行い、外部リポジトリ・会社資産を読んでいない。抽出スクリプトは標準ライブラリのみ、ネットワークなし・インストールなしで動く。イメージを作り直さず、特権化・他プロジェクトの操作・コンテナ再起動をしていない。

提出前に、今回のlicensesディレクトリとレビュー文書のみをgitleaksで検査した。exit 0、検出0件。`submission-secrets.json`・`.log` に結果を保存。全製品・履歴の再診断ではない。

```powershell
$root = (Get-Location).Path
docker run --rm --name easf-p503b-submission --network none -v "${root}/reports/security/2026-10-23-g4/licenses:/report/licenses:ro" -v "${root}/reports/security_review.md:/report/security_review.md:ro" -v "${root}/reports/security/2026-10-23-g4/licenses:/out" zricethezav/gitleaks:v8.30.1 dir /report --redact --report-format json --report-path /out/submission-secrets.json
```

`git diff --check` はexit 0。ruff check・formatの最終再確認も各0。コミットとCIの結果はGit・Actions履歴から追跡する。
