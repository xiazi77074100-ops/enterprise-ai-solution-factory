# 現行実装の固定・逸脱検出：実装と自己診断

2026-10-26、P5-03j、Codex。基点 `b513ec46d807a8b397461d5078b992b8a9a98fe5`、人の限定代行承認D-053。自己診断であり第三者診断ではない。

## 範囲と結果

6通常ハンドラ・24ソース/JSONファイルの初期固定表を追加。API/worker共通の生成時にファイルSHAと実ハンドラの関数同一性・種別、mockの応答/指示/schema、MCPの固定stdio接続条件を照合する。unknown/missing/duplicate ref、不正パス、symlink、SHA不一致、再束縛は起動前に拒否する。任意import・コマンド・外部接続は追加していない。

旧行の変更/削除をCIで比較する。比較元はPR base、main push前、作業ブランチの信頼mainに分ける。初回表がないことを許す基点は本書の基点SHAだけで、Git commit自体の存在も検査する。manifest自身は固定対象外。生成処理・照合処理を整形後に確定してから初期表を生成した。未コミットの初期表をソース修正に合わせて確定し、以後の旧値書換えは認めない。

既存の業務ソース、契約、DB、D-047構成・既存評価は変更していない。変更した製品ファイルは承認範囲のhandlersと新しいcatalog照合/表だけ。設計書を同時更新した。

## 実行記録

コマンドはリポジトリ直下（mypy/banditはbackend）で実行。仮想環境は `backend/.venv/Scripts/`。Git SHAは提出コミット履歴で追跡する。

| コマンド/確認 | 終了コード・結果 |
|---|---|
| pytest `-k 'current_release or startup_stops'`（初期表生成前） | exit 1、2失敗。1件は期待どおり表欠落、他1件はテストのdatabase_url不足。後者は実装の否定試験として数えず修正 |
| pytest 新規テスト＋既存test_handlers（初回実装） | exit 0、26成功 |
| mypy 新規実装・handlers・テスト（初回） | exit 1、テストでimportした属性の再公開扱い4件。定義元からimportするよう修正 |
| ruffを誤った実行パスで呼んだ試行 | 実行ファイル不存在で未実行。シェルの最終exit 0を検査成功と扱わず、正しいパスで再実行 |
| ruff `--config backend/pyproject.toml`をルートからテストにも指定 | テスト用per-file-ignoreのパス基準が異なりassert/合成secretを8件検出。既存規則を変えずbackend内から再実行 |
| ruff check/format（正しいbackend実行位置） | exit 0、対象3ファイル。比較scriptは別途同じ規則でcheck exit 0 |
| mypy `app/catalog/implementation_integrity.py app/executor/handlers.py tests/unit/test_implementation_integrity.py` | exit 0、3ファイル指摘なし |
| bandit `-q -r app/catalog/implementation_integrity.py app/executor/handlers.py` | exit 0、指摘なし |
| pytest 新規テスト＋既存test_handlers（追加試験後） | exit 0、28成功・1skip。Windowsのsymlink作成権限不足によるskipで、CIで実行する |
| 同pytest（CI基準分岐のstub試験追加後） | exit 0、32成功・1skip。初期導入可、他基点の表欠落拒否、導入基点自体のcommit欠落拒否、既存表比較を確認 |
| `python scripts/check_implementation_manifest.py --base-ref b513ec46d807a8b397461d5078b992b8a9a98fe5` | exit 0、明示した初期基準導入 |
| 同script `--base-ref 0000000000000000000000000000000000000000` | exit 1、存在しないcommitを拒否。失敗を期待する負例として確認 |
| `git diff --check` | exit 0 |

試験は隔離コピーのvalidator・共通values・MCP定義・handlers・checker改変、欠落、重複、不正path/digest、束縛差替え、共有MCPオブジェクトのargs改変、mock指示改変、API/worker起動拒否、旧行のSHA/束縛/削除/対象縮小、比較関数の同一内容/行追加を含む。実DBには接続しない。行追加の比較試験は、将来の新実装が実行可能であることを証明しない。

並行Codexの読み取りレビューで重大な破綻の指摘なし。テストの`.env`読み込み防止とCI基準分岐の確認を推奨され、全新規Settingsへ`_env_file=None`を指定しstub試験を追加した。初回生成順・MCP固定条件・自己比較しないCI分岐も確認した。最終SHA一致は主担当が実行試験で確認した。`git diff --exit-code b513ec4 -- backend/app/capabilities backend/app/adapters backend/app/mcp_server.py backend/app/mcp_tools contracts backend/migrations fixtures` はexit 0、対象に差分なし。

## 保証限界・未実行

人の確認、DB/文書保存・engine、実依存/OCR環境、過去の同じ版に複数実装があった対応、実行中の可変ソース、trace識別子、新旧並行実行は未対応。完全な再現性の保証ではなく、RV-G3-001全体を閉じない。共通handlers/adapterを固定したため将来の拡張には分離設計が要る。

未実行：ローカルsymlink試験（Windows権限）、ワーカーの固定配布（別タスク）、実環境の再現・全件ローカルDB回帰（全件CIで確認）、新しいホールドアウト評価/baseline調査（禁止・対象外）。Claude Codeレビューは以前の利用上限のため未実行。G4は未承認。新しいサービス購入なし、人の時間とモデル追加請求は未測定。
