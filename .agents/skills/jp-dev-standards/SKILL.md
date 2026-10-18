---
name: jp-dev-standards
description: 日本の受託開発・SI の進め方に合わせた EASF の開発規約。コーディング規約（Python / TypeScript の命名・型・例外・ログ・コメント）、日本固有のデータの扱い（日付と和暦・タイムゾーン・金額と消費税の端数・全角半角・インボイスの登録番号）、設計書（基本設計・詳細設計・ADR）、テスト仕様書と試験成績（エビデンス）、レビュー記録（指摘票）、ブランチとコミット。コードを書く・設計書やテスト仕様書を作る・レビューする・コミットするときに使う。「規約」「設計書」「テスト仕様書」「試験」「エビデンス」「レビュー記録」「命名」と言われたときにも使う。
---

# jp-dev-standards — 開発規約

日本の案件の受け入れでは、動くことに加えて「設計書・テスト仕様書・試験成績・レビュー記録が揃っていて、追跡できること」が求められる。EASF ではそれを最小の手間で残す。

## 1. コーディング規約

### 共通
- 識別子・API・JSON キー・DB の列名は英語。コメント・docstring・ログの `message`・画面の文言は日本語でよい（中国語は使わない）。
- コメントは「なぜ」を書く。コードを言い換えるコメントを書かない。TODO は `TODO(<task-id>): …` の形で、タスク管理に載っているものだけ。
- 1 関数 1 責務。早期 return。魔法の数値は名前付きの定数か設定へ。
- 既存の部品・標準ライブラリを先に探す（`ponytail`）。同じものを 2 つ作らない。

### Python（バックエンド）
- 版は ADR で固定。型ヒント必須、`mypy --strict`（または同等）を通す。`Any` は境界（外部ライブラリ）だけ。
- 整形・静的検査は `ruff`（`ruff format`、`ruff check` は `E,F,I,B,UP,S,SIM,N` を基本）。
- 命名：モジュール・関数・変数は `snake_case`、クラスは `PascalCase`、定数は `UPPER_SNAKE`。真偽値は `is_` / `has_` / `can_`。
- 例外：素の `except:` / `except Exception: pass` を書かない。業務エラーは `ApiError(code, message, status)` の 1 系統。外部ライブラリの例外は境界で包む。
- ログ：`logging` の構造化ログ。`print` を使わない。個人情報・秘密を出さない（`jp-secure-coding`）。
- テスト：`pytest`。ファイルは `tests/<モジュール>/test_*.py`。テスト名は `test_<対象>_<条件>_<期待>`。

### TypeScript（フロントエンド）
- `strict: true`、`noUncheckedIndexedAccess: true`。`any` 禁止（`unknown` で受けて絞る）。`as` での握りつぶしをしない。
- 整形は Prettier、検査は ESLint（`react-hooks`、`jsx-a11y`、`react/no-danger` をエラー）。
- 命名：部品は `PascalCase.tsx`、フックは `useXxx`、それ以外は `camelCase.ts`。
- API の型は OpenAPI から生成し、手で書き写さない。
- 画面の規約は `japan-enterprise-frontend`（審美の補助は `design-taste-frontend`・`redesign-existing-projects`、ただし業務画面の規約が優先）。

## 2. 日本固有のデータ

| 対象 | 規則 |
|---|---|
| 日時 | DB・API は UTC の tz-aware（ISO-8601）。画面は JST（`Asia/Tokyo`）で `YYYY-MM-DD` / `YYYY-MM-DD HH:mm`。日付だけの業務値（請求日・支払期日・契約日）は `date` 型でタイムゾーンを持たせない |
| 和暦 | 文書中の和暦（令和 7 年 4 月 1 日、R7.4.1）は抽出時に西暦の `date` へ正規化し、元の表記も根拠として残す。元号の対応表はコードで持ち、テストで境界（平成 31 年 4 月 30 日／令和元年 5 月 1 日）を確かめる |
| 金額 | `Decimal`（float 禁止）。円は整数。画面は `¥1,234,567`、集計は万円・億円の表記を設計書で決める |
| 消費税 | インボイス制度では「1 枚の請求書につき、税率ごとに 1 回」端数処理する。端数処理の方法（切り捨て・四捨五入・切り上げ）は文書ごとに違うので、ルールでは許容差として扱い、判定できなければ人の確認へ |
| 登録番号 | 適格請求書発行事業者の登録番号は `T` ＋ 13 桁。形式の検査だけを行い、実在の確認（国税庁の公表サイトへの照会）はしない（外部接続なし）。合成データの番号は「TEST ONLY」と分かる形にする |
| 文字 | UTF-8。照合・重複判定の前に NFKC 正規化（全角英数・半角カナ）と空白の正規化。表示と根拠には元の文字列を使う |
| 口座 | 銀行名・支店名・種別・口座番号・名義（カナ）。合成データだけ。ログ・トレースでは伏せる |

## 3. 文書の体系

`docs/` に Markdown で置く。設計書は「何を・なぜ」を書き、コードと同じコミットで直す。

| 文書 | 場所 | 中身 |
|---|---|---|
| ADR | `docs/adr/ADR-NNN-<slug>.md` | 状況・選択肢（2 つ以上）・決定・理由・影響・確認日（`references/templates.md`） |
| 基本設計書 | `docs/design/basic/` | 方式設計（構成・モジュール境界）、画面一覧・画面遷移、API 一覧、データ一覧、権限表、非機能（性能・セキュリティ・運用）、外部接続一覧 |
| 詳細設計書 | `docs/design/detail/` | モジュールごとの処理・状態遷移・エラー・DB 定義・入出力の契約 |
| セキュリティ設計書 | `docs/design/security.md` | 脅威モデル、`jp-secure-coding` の対応表、受容したリスク |
| テスト仕様書 | `docs/test/` | 試験項目の表（`references/templates.md`） |
| 試験成績・エビデンス | `reports/` | 実行コマンド・日時・コミット SHA・結果・スクリーンショット・ログ |
| レビュー記録 | `reviews/` | 指摘票（`references/templates.md`） |

日本の顧客向け文書の慣習：表紙の情報（文書名・版・日付・作成者・承認者）、改版履歴（版・日付・内容・作成者）を冒頭に置く。

## 4. ブランチ・コミット

- ブランチ：`cc/<task-id>-<slug>`、`codex/<task-id>-<slug>`、`main` は保護（直接コミットしない）。
- コミット：Conventional Commits の type（`feat` `fix` `docs` `test` `refactor` `chore` `security`）＋ scope ＋ 日本語の要約。例：`feat(catalog): Capability の版を不変にする`。本文に理由とタスク ID。
- 1 コミット 1 目的。生成物・秘密・`.env`・大きなバイナリ・ホールドアウトのラベルをコミットしない。
- コミットのたびに `easf-phase-gate` の `CHANGELOG.md` を更新する必要はない（ゲートでまとめる）。

## 5. レビュー

- 自分の変更は `ponytail-review`（作りすぎ）と `jp-secure-coding`（安全）の 2 つの観点で見直してから出す。
- 独立レビュー（Codex ⇔ CC）の指摘は `reviews/` の指摘票に残し、全件「対応済み／対応しない（理由）」まで閉じる。

## references

- [templates.md](references/templates.md) — ADR・テスト仕様書・試験成績・指摘票の書式
