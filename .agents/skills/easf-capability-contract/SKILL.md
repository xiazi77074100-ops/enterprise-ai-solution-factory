---
name: easf-capability-contract
description: EASF の中核の契約と不変条件。Capability（版・入出力スキーマ・実装参照・適用範囲・出所）、Workflow（型付き DAG・版の固定・設定）、Rule pack、アダプタ（local / REST / MCP / LLM、実接続と模擬の区別）、証跡（evidence の文書 ID・ページ・位置・テキストのハッシュ）、版の上げ方、再利用の分類。Capability・Workflow・Rule pack・アダプタを追加・変更するとき、Composer / Executor / Catalog を実装するとき、契約スキーマ（contracts/）を直すとき、「業務ごとに分岐したい」と思ったときに使う。
---

# easf-capability-contract — 契約と不変条件

EASF の価値は「**同じ版の部品を、設定だけ変えて別の業務で動かし、その証拠を残す**」こと。これを壊す実装は、動いても不合格（G1b・G3 で落ちる）。

## 1. 不変条件（破ったらゲート不合格）

1. **Capability の版は不変**。登録後は内容を変えない。直したら新しい版。同じ `capability_id@version` の再登録は、内容のハッシュが同じなら冪等、違えば拒否。
2. **Workflow の全ノードは版を固定**（`capability_version` に範囲指定 `^1.0` を許さない）。解決策（Solution）は構成のハッシュを持ち、実行はそのハッシュを記録する。
3. **スキーマ検証は 3 か所**：登録時（契約自体が正しいか）、構成時（つながるノードの出力と入力が合うか）、実行時（実際の入出力）。どこかで外れたら失敗で、成功にしない。
4. **汎用エンジン（catalog・composer・executor・evaluation・observability・reuse）に業務名を書かない**。`invoice` / `contract_review` / `請求書` / `契約書` が `backend/app/{catalog,composer,executor,adapters,evaluation,observability,reuse}` に出たら失敗する検査（`scripts/validate_contracts.py`）を置く（「契約」だけは Capability の契約の意味でも使うので対象にしない）。業務の違いは Rule pack・抽出プロファイル・Workflow の設定（データ）で表す。
5. **成功にしてはいけない状態**：必須ノードの失敗、確認待ち、重大ルールのガード失敗、予算超過、時間切れ、出力スキーマ違反。
6. **証跡は作らない**：根拠は「不変の文書 ID・ページ・文字の開始と終了位置・その範囲のテキストの SHA-256」。元の文書で照合できなければ `unverified`。
7. **模擬は模擬**：模擬アダプタの結果には `execution_mode: "mock"` を付け、画面・API・報告で区別する。実接続の件数・再利用の実績に数えない。

## 1.1 補足（G0 レビューで追加）

- 確認で却下された実行は `rejected`。以降のノードは `skipped`、出力しない。
- 案件をまたぐ判定（重複など）は、Executor が渡す予約入力 `project_context`（実行開始時点のスナップショット）だけを使う。Capability から DB を読まない。
- 内容ハッシュは RFC 8785 で正規化した JSON の SHA-256。

## 2. 実装参照の解決（任意コード実行を作らない）

`implementation.reference`（例 `capabilities.document_parser:run`）を文字列から `importlib` しない。起動時にコードで登録した **許可リスト（レジストリ）** のキーとして扱い、無いキーは登録を拒否する。REST / MCP の接続先も、アダプタ設定の許可リストの名前で参照する（URL を契約に直接書かない）。

## 3. Capability を足す・直すとき

1. 既存の 6 つ（DocumentParser・StructuredExtractor・RuleValidator・EvidenceLocator・HumanReview・ResultExporter）の設定で済まないか先に考える。済むなら Rule pack・プロファイルを足すだけにする。
2. 入出力スキーマは JSON Schema 2020-12 の範囲で、外部 `$ref` を使わない。文字列・配列に上限。`additionalProperties: false`。
3. `configuration_schema` を必ず書く（ノードの `config` はこれで検証する）。
4. `timeout_ms`、`side_effects`（POC では `false` だけ実行可）、`provenance`（出所・ライセンス）、`evaluation_profile` を書く。
5. 版の上げ方：
   | 変更 | 版 |
   |---|---|
   | 出力の意味を変えない内部の修正 | パッチ（1.0.0 → 1.0.1） |
   | 任意の入力・出力項目の追加、設定項目の追加 | マイナー（1.0.x → 1.1.0） |
   | 必須項目の追加・削除・型や意味の変更 | メジャー（1.x → 2.0.0） |
   新しい版を作っても、古い版を使う Workflow はそのまま動く（自動で上げない）。
6. 契約テスト（正常・スキーマ違反・時間切れ・巨大入力）を書く。

## 4. Rule pack

- ルールはデータ（YAML / JSON）。各ルールに `rule_id`・`severity`（critical / major / minor）・説明（日本語）・判定式（許可された演算子だけの小さな式。`eval` しない）・根拠に使う項目。
- 判定結果は `pass` / `fail` / `uncertain` の 3 値。値が無い・読めないは `uncertain`（契約では「欠落」と「不明」を分ける）。`critical` の `fail` と `uncertain` は必ず人の確認へ。
- Rule pack にも版を付け、評価・実行の記録に残す。

## 5. 再利用の分類（ReuseRecord）

| 分類 | 意味 |
|---|---|
| `unchanged` | 同じ版をそのまま |
| `config_only` | 同じ版、設定・Rule pack だけ違う |
| `adapter_modification` | アダプタ（接続）だけ変えた |
| `new_code` | 新しい版・新しい Capability を作った |

再利用の証拠は「同じ `capability_version_id` が、2 つの案件の実行（trace ID）で動いた記録」。工数は `HUMAN_TIME_LOG.csv` と結びつける。

## 6. 契約ファイル

G0 で `contracts/`（`openapi.yaml`、`capability.schema.json`、`workflow.schema.json`、`events.schema.json`、`rule_pack.schema.json`）を凍結する。`easf_package/schemas/` は出発点で、正本ではない。凍結後の変更は版を上げ、全利用者のテストを通してから。所有者は CC だけ。
