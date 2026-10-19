# 詳細設計：業務の Capability（解析・抽出・検証）

| 版 | 日付 | 変更内容 | 作成者 |
|---|---|---|---|
| 0.1 | 2026-10-19 | 初版（P3-01b） | Claude Code |

Capability の契約（入出力・設定のスキーマ）は `contracts/examples/capabilities/` が正。ここは実装の動きを書く。どの部品も業務名を持たず、業務の違いはノードの設定（`field_spec`・Rule pack）で表す（`easf-capability-contract` §1-4）。

## 1. 一覧

| 実装キー | Capability | 種類 | 実装 | 実行のされ方 |
|---|---|---|---|---|
| `document_parser.v1` | `document.parser@1.0.0` | local | `backend/app/capabilities/document_parser.py` | ワーカーが文書を読み（`StoredDocumentHandler`）、子プロセスで解析 |
| `rule_based_extractor.v1` | `document.rule_extractor@1.0.0` | local | `backend/app/capabilities/rule_extractor.py` | 子プロセス |
| `structured_extractor.v1` | `document.extractor@1.0.0` | llm | `backend/app/capabilities/mock_extractor.py`（mock の応答） | LlmPort の mock（`execution_mode: mock`、D-004） |
| `rule_validator.v1` | `document.rule_validator@1.0.0` | local | `backend/app/capabilities/rule_validator.py` | ワーカーが Rule pack を読み（`RulePackHandler`）、子プロセスで評価 |

結び付けは `backend/app/executor/handlers.py`、許可リストの `available` は `backend/app/catalog/registry.py`（一致をテストで確かめる）。ワーカー側の読み出しは `backend/app/adapters/resources.py`。参照が解決できない（文書・Rule pack が無い、保存したファイルのハッシュが違う）ときはノードを失敗にし、再試行しない（`document_not_found`・`document_unreadable`・`rule_pack_not_found`）。

## 2. 解析（document_parser.v1）

- PDF：テキスト層（pypdfium2、`backend/app/capabilities/pdf_text.py`）のページごとのテキスト。根拠の文字の番号はこの文字列を指す。
- 画像（PNG・JPEG）：OCR は POC では未対応。空のテキストの 1 ページを返し、抽出はすべて `missing` → 人の確認へ。`extraction_method` は `text_layer`（契約の選択肢に「OCR なし」がないため。OCR を足すときは `ocr_tesseract`）。
- 1 ページが 50,000 文字を超えたら失敗（切り詰めると根拠の位置がずれるため）。
- 出力：`document_id`・`document_sha256`（登録時のハッシュ）・`pages`。

## 3. 規則ベースの抽出（rule_based_extractor.v1、D-015）

設定 `field_spec[]` の各項目に `labels`（見出しの文字列、1〜10 個）を書く。

1. ページのテキストを NFKC に正規化する。
2. 各見出しについて「見出し＋（任意の括弧書き、例「（10%）」「（普通）」）＋ `：` または `:`」の後ろの、行末までを候補にする。
3. 型ごとに読む：`date`（西暦・和暦〔令和・平成、R・H〕→ ISO 8601）、`decimal`（`¥`・`￥`・`円`・桁区切りを除いた数字の文字列）、`integer`、`string`（前後の空白を除き 200 文字まで）。
4. 結果：異なる値が 1 つ → `found`、2 つ以上 → `uncertain`（値は null）、見出しはあるが読めない → `uncertain`、見出しが無い → `missing`。
5. `array`・`boolean` はこの方式では読まないので `uncertain`（人が確認）。

文書の中の文は、どれもデータとして扱う（指示として解釈しない。LLM を使わない）。

## 4. LLM の抽出（structured_extractor.v1、mock）

実 API は D-004 で保留。mock は文書を読まず、`field_spec` の全項目を null・`uncertain` で返す（決定的。正解ラベルを使わない）。実行は `mixed` / `mock` として記録され、実接続には数えない。流れの確認のためだけに使う。

## 5. ルールの検証（rule_validator.v1）

Rule pack（`contracts/rule_pack.schema.json`）の式を、決まった演算子だけで評価する（`eval` しない）。

| 状況 | 結果 |
|---|---|
| 式が真 | `pass` |
| 式が偽 | `fail` |
| 参照した値が null・空・無い | ルールの `on_missing`（`uncertain` または `fail`） |
| 値はあるが比べられない（数値でない、未知の演算子、`unique_in_project` で案件の文脈が無い） | `uncertain` |
| `and`・`or`・`not` の中で値が無い | 3 値の論理（Kleene）。決まらなければ `uncertain` |
| 入れ子が 8 段を超える | `uncertain` |

- `present` は値の有無そのものを見る（無ければ偽）。
- `matches_reference`：参照表で `match_field` が `key_field` の値と一致する行のうち、`value_field` が項目の値と一致する行があれば真。該当する行が無い（未登録の取引先）も偽。
- `unique_in_project`：Executor が渡す `project_context.values[<項目名>]`（同じ案件の、この実行より前に成功した実行の確認後の値）に含まれていれば偽。
- `format`：`jp_invoice_registration_no` は `T` ＋ 13 桁の形だけを見る（合成データの登録番号は検査用数字をわざと誤っているため、検査用数字は確かめない）。
- `message` は「ルールの題名：適合／不適合／判定できません（要確認）」。入力の値を含めない。
- `requires_review`：`fail` が 1 つでもある、または `critical` が `pass` でない。

## 6. 案件の文脈（project_context）

入力スキーマに `project_context` を持つ Capability には、Executor が入力を組み立てるときに付ける（辺からは渡さない）。中身は、同じ案件で、この実行より前に作られ成功した実行の、人の確認ノードの出力 `reviewed_fields` の値（文字列・数値だけ、項目ごとに 10,000 件・50 項目まで）。`snapshot_at` はこの実行の作成日時。Capability は DB を読まない（`easf-capability-contract` §1.1）。実装は `backend/app/executor/engine.py`。
