# P5-03d 実行コマンド

2026-10-23、リポジトリルート、PowerShell。基点fce7ee9から専用ブランチを作成（fetch・ff更新・switch各0）。

```powershell
backend/.venv/Scripts/python.exe -m pytest -q backend/tests/security/test_error_logging.py --tb=short -p no:cacheprovider
```

最初は修正前の本体で実行し、合成値の混入を3ケースすべて検出してexit 1、before-pytest.log。次の提示済み差分を適用（exit 0）した後、同じテストがexit 0、3 passedとなった。合成DB URLを明示した最終再確認も3 passed（0.24秒）、after-pytest.log。テストの時間を製品の処理性能の測定値とはしない。

```powershell
git apply reports/security/2026-10-23-g4/error-log/proposed-fix.patch
```

以下はbackendディレクトリから実行、最終はすべてexit 0。初回ruffはLogRecordの定数getattrに対するB009が2件でexit 1だったため、値が欠落した場合も試験で検出できるよう既定値Noneを明示し、再確認した。

```powershell
.venv/Scripts/ruff.exe check . ../fixtures
.venv/Scripts/ruff.exe format --check . ../fixtures
.venv/Scripts/mypy.exe app/core/middleware.py tests/security/test_error_logging.py
.venv/Scripts/bandit.exe -q -r app
```

出力はruff.log・format.log・mypy.log・bandit.log。最終の合成URL明示後も変更2ファイルのruff・formatと3ケースのpytestを確認した。全体のmypy・DBを使う全件pytest・契約試験は当該コミットのCIで確認し、未実行のローカル検査と区別する。

CIには既存の契約・skill、backendのruff・format・mypy・bandit・pip-audit・全件pytest、frontendの検査がある。CI設定は変更していない。コミットと結果はGit・Actions履歴から追跡する。

提出前：`python scripts/sync_skills.py --check`、`git diff --check` は各0。contracts、D-047のWorkflow・Rule pack・Capability、Catalog・Composer・Executor・アダプタを指定した `git diff --exit-code -- <対象パス>` も0。今回の提出物のみを下記で検査しexit 0・検出0、submission-secrets.json・.logへ保存した。全履歴・全製品のgitleaks再診断ではない。提出ログの行末はLFに統一し、末尾空白だけを除去する。

```powershell
$root = (Get-Location).Path
docker run --rm --name easf-p503d-submission --network none -v "${root}/reports/security/2026-10-23-g4/error-log-fix:/report:ro" -v "${root}/reports/security/2026-10-23-g4/error-log-fix:/out" zricethezav/gitleaks:v8.30.1 dir /report --redact --report-format json --report-path /out/submission-secrets.json
```
