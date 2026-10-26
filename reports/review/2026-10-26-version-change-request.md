# RV-G3-001：CC向けの変更要求案

2026-10-26。人の並行分担の指示によりCodexの別エージェントが読み取り調査し、主担当がCatalog・Executor・schemaの主要根拠を確認して整理した。**CCの設計判断・人の承認・実装は未実施**。並行エージェントはこの会話の文脈を継承したCodexであり、独立した新規チャット・Claude Code・第三者レビューと同一視しない。

## 問題と現状根拠

現行Catalogは登録した契約JSONの不変性を保証するが、Executorは `(kind, implementation.ref)` で現行ハンドラを選ぶ。同じCapability版IDでも、関数・共有ヘルパー・MCPサーバが変われば実行内容が変わり得る。版IDの一致だけを実装不変や過去結果の再現の証拠にしない。RV-G3-001は**未解消**のまま維持する。

| 根拠 | 確認内容 |
|---|---|
| `DECISIONS.md` D-043・D-047 | 同じ版のままの実装変更を開示済み。評価対象はcontract-v3・contract@1.1.0・コード71abf10として凍結 |
| `backend/app/catalog/service.py:35`・`:42` | ハッシュは契約JSON。JSONが同一なら冪等登録され、実装コード変更は判定対象外 |
| `backend/app/catalog/registry.py:18` | kind・ref・availableの許可リスト。実装digestとの対応は持たない |
| `backend/app/executor/engine.py:54` | ハンドラのキーはkindとimplementation.refのみ |
| `backend/app/executor/handlers.py:15`・`:22` | 現行関数をimportし、固定キーへ束縛 |
| `backend/app/capabilities/rule_extractor.py:15`・`evidence.py:15` | 共通valuesを参照。入口関数だけ保存しても共有処理の変更が及ぶ |
| `backend/app/adapters/mcp.py:20`・`backend/app/mcp_server.py:18` | 現行MCPサーバ・evidenceを参照 |
| `contracts/capability.schema.json:63` | implementationはrefのみ、追加プロパティ不可。digestの直接追加は契約変更が必要 |
| `backend/app/executor/events.py:48` | Capability版IDを記録するが、それだけで実装バイト列を特定できない |
| `backend/migrations/versions/0003_catalog.py:47` | DB行のUPDATE・DELETE禁止。実装不変性とは別の保護 |

行番号は基点 `5db3134abe3b7d44bf1000120820d6452ca0ddfb`。全文の独立再監査や動的試験の結果ではない。

## 選択肢と推奨案

| 案 | 利点 | 制約 |
|---|---|---|
| A：新しいref・Capability版＋固定したリリース対応表（推奨案） | 現行schemaのrefを使い、旧refの差し替えを避けて新版を並行追加できる | 実装・共有処理・依存と実行環境の対応表を、起動時/CI/実行証跡で強制する設計が必要 |
| B：契約に実装digest等を追加 | 契約自体で対応を表せる | 凍結schema・関連API・DB・Executor等の変更と承認・移行が必要。先に採用しない |
| C：イメージdigestの記録・保存だけ | 当該環境を保存する最小の補助策 | 同じCapability版が異なるイメージで異なる実装になり得るため、単独では解消にならない |

Aを検討の出発点とし、採用はCC・人が決める。新しい版名・入口関数のコピーだけでは、共有values・PDF処理・MCPツール定義などが現行コードを参照し続ける問題を防げない。対象とする実装の依存範囲、対応表の保存場所・権限・照合失敗時の扱い、runからの追跡をCCが設計する。

実装同一性の範囲と実行環境の識別を区別する。OSのセキュリティパッチ等をどこまでCapabilityの版変更条件にするかは、互換性・保守負担を含めてCCが決める。すべてを一律に固定する新基盤を、この原稿だけで追加しない。既存event metadataを使う場合もschema適合を先に確認する。

## 凍結版を壊さない移行条件

- D-047のWorkflow・Rule pack・Capability実装と元集計は変更しない。Catalog行・凍結Solution・過去traceを更新しない。
- 旧refを新しい関数へ再束縛せず、新しいref・Capability版・Workflow/Solutionを明示的に並行追加する。自動移行しない。
- 新版の意味に応じた版番号をCCが決める。スキーマが変わらないことだけでパッチ版と判定しない。
- 過去に同じ版名へ複数実装があった事実は、遡及的な対応済みにしない。歴史的実装を復元・保存できる範囲をCCが調査し、証明できない過去実行は「実装対応不明」と残す。旧版名へ別の過去実装を上書きしない。
- 評価済み集計は旧環境の結果として保持。新版の品質を旧集計から主張しない。ホールドアウト再評価や新しいデータの要否は、人が別途判断する。

## CCが具体化する変更候補

`backend/app/catalog/{registry,validation,service}.py`、`backend/app/executor/{handlers,engine,events}.py`、`backend/app/adapters/{local,mcp,resources}.py`。実装保存は `backend/app/capabilities/`、`backend/app/mcp_server.py`、`backend/app/mcp_tools/` と関係する共有コードを含め、実際に必要なパスだけをCCが指定する。列挙は変更許可ではない。

契約・DB変更が必要なら `contracts/`・`backend/migrations/` を追加変更要求に分離し、承認前に変更しない。設計書・ADR・DECISIONS・具体的な引き渡し書をCCが用意する。Codexは承認後に独立テストの対象パスを受け取る。

## 独立受入テストの案

専用テストDBと合成入力で実施し、ホールドアウト・baselineコードを使わない。

1. 同じCapability版・同じ内容は冪等、異なるref/内容は拒否する。
2. 未許可ref・任意import・任意URLを引き続き拒否する。
3. 新版の関数・共有処理・MCPを変更しても、旧版の固定入力に対する旧出力が変わらない。
4. 固定対象と決めた実装・共有処理・MCP定義・依存対応の改変をそれぞれ検出し、成功扱いにしない。
5. 旧新Workflowが明示した版へ解決され、旧Solutionを自動で新版へ向けない。
6. 別々の2案件で、exporterを含む対象ノードの版IDと固定実装の識別子を永続traceから照合できる。
7. 再試行・ワーカー再起動後も対応が変わらない。対応不明/欠落時はfail closed。
8. D-047のファイルと既存集計に差分がない。

これらは**未実行**。実装・移行・テストの担当範囲と方式が未確定で、本調査は読み取り専用のため。

## CCへ渡す開始文

> AGENTS.mdとdocs/HANDOFF.mdを最初に読み、この変更要求案をCCとしてレビューしてください。D-047の凍結対象・既存評価・過去traceを書き換えず、方式、依存範囲、版番号、必要パス、契約/DB変更の要否を具体化してください。まず設計判断と変更要求・受入テスト範囲を提示し、承認が必要な変更を先行実装しないでください。ホールドアウトを開く・生成する・マウントすること、baselineコードの閲覧、有料API・外部公開は禁止です。

人が決めるのは、方式・範囲・旧版の既知制約の扱い、新版評価の必要性とデータ方針。G4承認とは別に記録する。原稿作成をRV-G3-001の解消・実装承認として数えない。

追加現金支出0円、人の時間は未測定。第三者診断ではない。別CLIプロセスによるCCセッションは未起動（認証・課金条件未確認）。
