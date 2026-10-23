# P5-02a 実行記録

2026-10-23、PowerShell、リポジトリルート、基点9801b90。作業対象は既存の集計・報告・台帳だけ。

| コマンド・確認 | 結果 |
|---|---|
| `git switch -c codex/P5-02a-evaluation-index` | 初回の非昇格実行は.git refのlock作成権限で失敗。個別のGit終了コードは未保存（後続の読取コマンドが終了0でも作成成功と数えない）。昇格して同じswitchを行いexit 0・作成成功 |
| `backend/.venv/Scripts/ruff.exe format reports/eval/2026-10-23-index/check_aggregates.py` | 0、1ファイル整形 |
| `backend/.venv/Scripts/ruff.exe check --select E,F,I,B,UP,S,SIM,N reports/eval/2026-10-23-index/check_aggregates.py` | 0 |
| `backend/.venv/Scripts/python.exe reports/eval/2026-10-23-index/check_aggregates.py` | 0、run.logは空、checked.jsonに集計7件・入力SHA-256・丸め照合16セル・旧集計に対する4条件と制約を保存 |

このスクリプトは明示した7集計JSONと契約書報告・事前登録・工数/費用台帳だけを読む。出力は選択した集計のスカラーと来歴メタデータに限り、元の入力は書き換えない。採点器・生成器をimportせず、新しい評価やホールドアウトの生成・アクセス・再採点を行わない。baselineリポジトリも参照しない。

ローカルの製品回帰・実画面・DAST・再評価は未実行（本タスクは文書と集計照合のみ、製品変更なし）。直前の製品修正9801b90のCI全件成功は確認済みであり、この索引の照合結果とは分ける。当該文書コミットのCIは別途確認し、Git・Actions履歴で追跡する。追加支出0円、人の時間は未測定。

提出前の再確認：照合スクリプト、ruff・format、skill同期・差分検査は各exit 0。索引・準備レビューの相対リンク24件を確認し欠落0（links.log）。初回のリンク確認の表示はPythonの標準出力の文字コードが合わず読みにくかったため、UTF-8を明示して記録し直した。製品・契約・fixtures・experiment・工数費用台帳の `git diff --exit-code` は0。

今回の索引と照合出力だけを `zricethezav/gitleaks:v8.30.1 dir /report --redact --report-format json --report-path /out/submission-secrets.json` でネットワークなし検査し、exit 0・検出0。提出物のみをマウントしたもので、全履歴・全製品の再診断ではない。submission-secrets.json・.logに保存した。
