# 版固定の第一段階：実装判断用の設計案

2026-10-26、Codex、P5-03i。基点 `3449406902192809cb04147d44ced6cc1d8fad8a`。前提は [Codexレビュー](2026-10-26-codex-version-review.md)。**未承認の設計提案**。製品実装・試験は未実行。本書は自己レビューであり第三者診断・CC承認・G4承認ではない。

## 採用を提案する範囲

第一段階は、現行refに対応する業務ソースと束縛を固定し、照合失敗時にAPI/ワーカーの本番ハンドラ生成を拒否する。契約・DB・既存Capability版・入出力を変えない。表の名前は `backend/app/catalog/implementation_manifest.json`、照合処理は `backend/app/catalog/implementation_integrity.py` とする案。表と検査を分け、静的許可リストを正本のまま維持する。

この設計で保証するのは指定したソース群と束縛の一致。環境を含む完全な再現性、過去の全実装の復元、新旧実装の並行稼働は保証しない。RV-G3-001の部分的な予防策であり、指摘全体の解消として閉じない。

## 固定対象の具体案

表はschema版、各kind/ref、固定ファイル一覧（リポジトリ相対パスとSHA-256）、想定するハンドラ種別・入口を持つ。任意のimport先やコマンドとして解釈しない。入口の検査はコードで記述した既知の構造と照合する。JSONから動的に属性を探索して関数を実行しない。

| 現行ref | 固定する業務処理（`backend/app/`以下） | 実行境界 |
|---|---|---|
| document_parser.v1 | capabilities/document_parser.py、pdf_text.py、ocr.py | StoredDocumentHandler → LocalHandler → 子プロセス |
| rule_based_extractor.v1 | capabilities/rule_extractor.py、values.py | LocalHandler → 子プロセス |
| structured_extractor.v1 | capabilities/mock_extractor.py（指示文・schemaも含む） | LlmHandler → MockLlm。実LLM接続を追加しない |
| rule_validator.v1 | capabilities/rule_validator.py | RulePackHandler → LocalHandler |
| easf_local_mcp:locate_evidence | mcp_server.py、mcp_tools/locate_evidence.json、capabilities/evidence.py、pdf_text.py、values.py | McpToolHandler → 固定stdioサーバ |
| result_exporter.v1 | capabilities/result_exporter.py | LocalHandler → 子プロセス |
| human_review.v1 | 第一段階の業務関数表では対象外と明示 | executor/engine.py内の特別処理。ハンドラ欠落とは区別 |

全行に共通して束縛を作る `executor/handlers.py` と使用adapterの `base.py`・`local.py`・`llm.py`・`mcp.py`・`resources.py` を固定する。関連packageの `__init__.py` も対象に含める。実装時に存在するファイルを明示列挙し、ワイルドカードで勝手に固定範囲を増減しない。

一方、resourcesが参照するDBモデル・文書保存、engineの状態機械・人の確認、JSON検証・Python/依存ライブラリ・OCR本体/言語データは、今回の業務ソース識別子の保証外である。配布物のGit SHAとイメージdigestを別の環境証拠として残す。これらの変更が出力へ影響しないと断定しない。完全な実装不変性が受入条件なら、この部分案では不足するため別範囲を設計する。

## 照合位置と失敗時の挙動

`backend/app/main.py:26` と `executor/worker.py:18` はともに `production_handlers(settings)` を使う。同関数で表/ファイル照合後に既存テーブルを組み立て、既知のハンドラ種別・関数・MCPツール束縛を照合してから返す案。`main.py`・`worker.py`を変更する必要は現時点では見込まない。明示的にhandlersを渡すテスト用経路は別とし、本番起動を検査済みと誤認しない。

ファイル欠落、期待値不一致、未知/重複ref、想定外の束縛は専用例外で停止し、代替実装へ戻らない。例外文とログは固定のエラーコードと相対的な識別子に限り、内容・絶対パス・設定値を含めない。起動失敗に対して新しいHTTP statusやrunの状態遷移を増やさない。

照合時点ではhandlersのimportは既に済んでいる。従ってこの検査は不正なコードのimport実行そのものを防止する仕組みではない。信頼したビルド・起動前の検査と、実行中にコードを差し替えない配布条件が前提。起動前の照合を通した後、import済みコードとディスクの食い違いが生じる運用を許可しない。

## 配布前提

- 本番/診断用のAPIとワーカーは同じ検査済み配布物を使う。ソース・依存・manifestを読み取り専用にし、アプリディレクトリへの書き込み可能なbind mount、hot reload、実行中のpip更新を行わない。
- 既存composeのAPIはread_only、tmpfsは/tmp、書き込みvolumeは文書領域。これは既存APIの根拠であり、ワーカーも同条件で動くことの実績ではない。
- ワーカーのコンテナ定義は未実装。第一段階でローカル可変ソースのまま動かすなら、起動時の一致だけを報告し、起動後の不変性は未保証とする。読み取り専用ワーカー配布の追加は別タスクとする。
- Dockerfileのbase tagは可変でapk更新もある。Git SHA/uv.lockだけを同一環境の証拠にせず、実際の配布イメージdigestを別に記録する。

## 初回生成と将来追加の制約

初回はhandlersの照合呼び出し・束縛検査のソースを確定してから、そのSHAをmanifestへ登録する。manifest自身は固定ファイル一覧に含めず、自己参照を作らない。初期表をレビューした後、再生成で旧行の期待値を書き換える運用を許可しない。

handlersと共通adapterも固定するため、将来のハンドラ追加で同ファイルを変更すれば旧行の照合も失敗する。新しい表の行を足すだけで並行追加できる設計ではない。将来の追加には、固定済み束縛・共有モジュールを保つ分離設計を別途用意する。この制約は初期の逸脱検出を小さく実装するために残す提案であり、拡張性を実現済みとは扱わない。

## 更新権限とCIの基準

CCが表と検査を所有し、Codexは独立試験を担当する案。既存refに対応するファイルSHAや入口の変更は禁止し、新refを追加する際は新しい表の行を追加する。共通ファイル変更で旧行のSHAが変わるなら、旧版用の共有処理隔離が必要となるため、その場で期待値を書き換えず別変更要求にする。初期登録は「今回確認する現行ソースの基準」であり、D-043以前や全評価時点の実装への遡及的な保証ではない。

CIはPRの変更先から取得した表だけで旧値を決めず、統合先の信頼したmainの表をGit objectとして読み、旧行の削除/変更を拒否する。初回導入では比較元の表が存在しないため、レビュー済みの初期表を明示的な一回の導入変更として承認する。基準が取得できない場合は成功にしない。古い履歴からのpushでも比較できるfetch設定と、PR head/baseの区別が必要。

この比較は変更管理の検査であり、管理権限を持つ者がコード・CI・基準を同時に変えることに対する暗号学的な保護ではない。人/CCのレビュー権限を置き換えない。リポジトリ設定・ブランチ保護の現状は未確認であり、強制済みと主張しない。

## 承認後に使う変更候補パス

| 担当 | パス・変更 |
|---|---|
| CC | `backend/app/catalog/implementation_manifest.json`（新規）、`implementation_integrity.py`（新規）、`backend/app/executor/handlers.py`（照合呼び出し・束縛検査） |
| CC/割当後のCodex | `backend/tests/unit/test_implementation_integrity.py`（新規、DB不要の隔離コピー試験） |
| CC | `scripts/check_implementation_manifest.py`（新規の旧行比較）、`.github/workflows/ci.yml`（比較元取得と検査） |
| CC | `docs/design/detail/capabilities.md`（保証範囲）、`docs/design/detail/run_execution.md`（配布前提）、決定・タスク記録 |

これらは**許可待ちの候補**。今回変更したパスではない。registryは静的許可リストのまま読み取り、変更を必須にしない。contracts・migration・Capability/Workflow/Rule pack・D-047実装の変更は含めない。trace識別子の永続化は前回T07として別範囲に残し、この第一段階では改変しない。

受入条件は前回T01〜T06に加え、human_reviewを対象外と明示し、既知6ハンドラのみを照合すること、初回基準導入と比較元欠落、既存行と共有処理の同時変更を拒否すること。T04の比較ツールは実装・CI配線を合わせて確認する。OS/ワーカー配布やT07〜T10の成功をこれで代用しない。

## 実績・未実行・残る判断

実行したのはGet-Contentによる対象文書/worker/main/Dockerfile/compose/CIの読み取りと、rgによるimport/起動箇所/ファイル一覧の確認。読み取りコマンドはexit 0で完了したものを根拠にする。1回のrg引数 `backend/app/mcp_tools/*.py` はWindows上で不正なパス指定となり、該当検索は失敗。再確認で対象がPythonではなく `locate_evidence.json` と分かった。この失敗を診断成功に含めない。

未実行：製品変更、manifestの生成、差し替え検出試験、CI基準比較の新検査、ワーカーの固定配布、環境再現試験、ホールドアウト評価、baseline調査。理由は本作業が読み取りと設計案に限定され、適用が未承認のため。既存CIの成功はこの未実装案の成功を意味しない。

並行Codexの読み取りレビューで、初回生成順と、共通ファイル固定が将来追加を制約する点を指摘され、本書に反映した。実装・試験のレビューではない。

人/CCが決めるのは、(1)この部分保証を第一段階として採用するか、(2)CC所有箇所の実装担当、(3)初期基準のレビュー・更新権限、(4)ワーカー固定配布を別タスクにするか。採用まで製品変更へ進めない。RV-G3-001は未解消、G4も未承認。
