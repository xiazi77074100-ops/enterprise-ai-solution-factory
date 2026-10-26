# 別案件・exporterまでの再利用証拠（P5-03k）

2026-10-26、Codex。製品の基点 `012e996340d69c1d2ce6815d8eeceb2774e0c626`。自己診断であり第三者診断ではない。RV-G3-003の「別案件・exporter・DB保存済みtrace」の不足を、今回のdev入力の限定範囲で補完した。G4承認や一般的な再利用性の証明ではない。

## 実行範囲と結論

既存のinvoice-v3とcontract-v3、各dev PDF 1件を変更せず使い、別々の2案件で登録→実行→確認承認→exportまで完了。APIはTestClientから実アプリを呼び、DBと本番local/MCPハンドラを使用した。Uvicorn経由の通信や実画面の確認ではない。確認承認は合成利用者としてテストがAPIを呼んだもので、人の実作業として数えない。

最終実行は2案件・2run・12ノードすべて成功、execution_modeはreal。MCPは自作ローカルstdioの実プロトコルであり、外部連携ではない。LLMノード・testkitノードは実行していない。初回にも同じ2文書で2runを実行し、初回の結果は別ファイルに保持した。これらから精度・作業削減率・費用効果を算出しない。

| 共通ノード | Capability版 | DB版IDの比較 |
|---|---|---|
| parse | document.parser@1.0.0 | 2案件で一致 |
| validate | document.rule_validator@1.0.0 | 2案件で一致 |
| locate | document.evidence_locator@1.0.0 | 2案件で一致 |
| review | review.human@1.0.0 | 2案件で一致 |
| export | result.exporter@1.0.0 | 2案件で一致 |

extractは請求書1.0.0・契約書1.1.0でDB版IDも異なるため、共通版の再利用に含めない。出力内容・export_idの一致を要求する試験でもない。

## 保存した証拠

[evidence.json](evidence.json)に完全なproject/run/trace/Capability版IDと30イベントを保存。各runの15イベントをDBコミット後の別セッションで再読出し、ハッシュ鎖を検証した。各node.completedの版ID・project/runをNodeRunと照合し、export APIのexport_idがDB保存出力と一致することも確認した。

| 種別 | 請求書 | 契約書 |
|---|---|---|
| project_id | 1b66807f-0f1a-48c5-ba75-2b52d0de1393 | ace04884-d457-44c2-a2e6-53a29bac34b2 |
| run_id | 1c712425-8c07-40ea-9d29-7efb8a7fd795 | c82cedfd-4d28-4130-a971-ea9594892291 |
| trace_id | caaf3789b87f4de69e1826c295f34e86 | 556769a3e2bd4c41a4e9b2a5293886e7 |
| export_id | 0ccd48e8-2846-53aa-a4b5-8416306bf5d7 | 5d2548f2-93ce-5099-8070-b6cab0cc27ca |

保存JSONからRFC 8785＋SHA-256のハッシュ鎖を再計算し、テストソース/固定表のSHAも現ファイルと照合した結果は[evidence-check.json](evidence-check.json)。固定表SHAは診断の来歴であり、各runのeventに実装digestを追加したことにはならない。

DBは終了後に削除している。保存済みというのはDBへコミットし再読出ししたことを指し、現在も同じIDをAPIで照会できるという意味ではない。診断の証拠JSONは保持する。本文・抽出値・Cookie・CSRF・接続URI・パスワードは提出物に保存しない。

## コマンドと結果

| コマンド・確認 | 終了コード・結果 |
|---|---|
| `backend/.venv/Scripts/python.exe reports/review/2026-10-26-reuse/run.py` 初回 | exit 0、pytest 1成功（128.23秒）。DB削除・既存コンテナのID/名前集合一致。ホスト文書の削除は未対応だったため別途回収 |
| 同コマンド、文書隔離・SQL引用・削除確認の補強後 | exit 0、pytest 1成功（156.21秒）。文書2件・未使用の空の既定領域・専用DBを削除。既存コンテナ集合一致 |
| backend内で `ruff check tests/integration/test_reuse_evidence.py`・`ruff format --check` | exit 0 |
| backend内で `mypy tests/integration/test_reuse_evidence.py` | exit 0、1ファイル指摘なし |
| `ruff check --config backend/pyproject.toml reports/review/2026-10-26-reuse/run.py` | 初回5指摘、補強後exit 0。SQLはpsycopg.sqlのLiteral/Identifierで引用。固定コマンドのS603は入力範囲を注記 |
| `python -`（保存JSONのハッシュ鎖・版ID・ソースSHA再計算） | exit 0、2案件・6ノードずつ・15イベントずつ・5共通版ID一致 |
| gitleaks v8.30.1、提出ディレクトリ、network none、既存設定/ignore使用 | exit 0、秘密検出0。初回のイメージ名フィルタは空だったが、一覧の絞り込みで既存の固定版を確認して実行 |
| `git diff --exit-code 012e996 -- backend/app contracts backend/migrations fixtures` | exit 0、製品・契約・DB定義・固定データに差分なし |
| `git diff --cached --check` | 初回exit 2、Windowsのpytestログに二重CRがあった。提出ログの改行/末尾空白だけを正規化し、補助のログ出力も改行変換を止めた。実行結果・JSONの内容は変更していない |

時間はpytestの実行時間であり、人の時間や性能測定ではない。初回は[initial-evidence.json](initial-evidence.json)・[initial-execution.json](initial-execution.json)・[initial-pytest.log](initial-pytest.log)、最終は[execution.json](execution.json)・[pytest.log](pytest.log)に記録する。補助は同梱run.pyと新規integrationテストのみで製品は変えない。

## 後始末とレビュー

並行Codexの読み取りレビューで、一時文書の回収不足を指摘された。新テストはtmp_path配下の専用領域を使い、resolve後の親・固定した末尾名・symlink不使用を確認して削除する。単独診断時だけ、importで生成した元の未使用領域もtemp直下/prefix確認後にrmdirする。非空なら削除しない。[storage-cleanup.json](storage-cleanup.json)で文書2件と領域の削除を確認。

初回領域は、実行時刻に該当する専用prefixが1件、内容が32桁hexの保存名2件だけであること、サイズと両dev PDFのSHAが一致すること、symlinkなし、Pythonのtemp root直下であることを確認して、その既知領域だけ削除。[initial-storage-cleanup.json](initial-storage-cleanup.json)に記録した。時刻/prefixだけで再帰削除していない。途中のDB保存名照会は自分のコンテナ停止後で失敗し、データ取得はなかった。

専用_test URLと新規DB生成手順、既存コンテナ集合の一致を非干渉の根拠とする。集合一致だけで既存DB内容の不変を証明したとは扱わない。他のDB/コンテナ・一時領域は削除していない。

## 未実行と残る制約

実画面の登録→修正→根拠→出力（AC-12）、確認値の修正、ホールドアウト評価、baseline調査、完全な環境再現、再起動/タイムアウト時の全後始末、traceへの実装digest永続化は未実行（今回の対象外）。DBイメージは既存postgres:17-alpineのtagであり、そのdigestまで固定した実験ではない。

RV-G3-001の過去の版と実装の曖昧さ、RV-G3-002の旧集計への採点影響、保持/来歴など他のG4不足は維持する。RV-G3-003の最終受入はCC・人が判断し、今回のdev 2文書の証拠を一般化しない。新サービス購入なし、人の時間・モデル追加請求は未測定。
