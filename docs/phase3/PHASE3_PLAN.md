# Phase 3 計画（請求書の POC、ゲート G2）

| 版 | 日付 | 変更内容 | 作成者 |
|---|---|---|---|
| 0.1 | 2026-10-19 | 初版 | Claude Code |
| 0.2 | 2026-10-19 | P3-04（OCR）を追加、G2 の進め方（D-033） | Claude Code |

## 1. 着手前の確認（easf-phase-gate §1）

| # | 項目 | 内容 |
|---|---|---|
| 1 | 直前のゲート | G1b 承認済み（D-027） |
| 2 | フェーズとタスク | Phase 3。P3-01（請求書の業務の Capability）・P3-02（合成データと独立したテスト）。本計画で細かく分ける（§4）。すべて CC（D-024） |
| 3 | 変えてよいパス | `backend/`（`app/capabilities/` を新設）、`backend/migrations/`、`fixtures/`、`frontend/`、`docs/`、台帳。`contracts/` は原則変えない（変えるなら版を上げて DECISIONS に書く） |
| 4 | 受入条件 | G2：請求書の業務が実際の部品の実行・確認・正解での評価まで動き、誤りが見える。AC-05（解析・抽出・検証・確認・出力）、AC-08（凍結したデータの版と正解で評価）、AC-09（重大な誤りを黙って通さない） |
| 5 | 時間・費用 | 追加現金支出 0 円の見込み（LLM は mock、D-004。Gemini の有効化は別途承認） |

## 2. 範囲

**やること**

- 文書の API（アップロード・一覧・ダウンロード）と保存（`jp-secure-coding` upload-and-files.md）。
- Capability の実装（業務名を持たない汎用の部品。請求書の違いは設定・Rule pack で表す）：
  - `document_parser.v1`：PDF のテキスト層（pypdfium2、D-028）。画像は OCR（Tesseract があれば。なければ「OCR 未対応」で空のページとし、抽出は missing → 確認へ）
  - `rule_based_extractor.v1`：見出しの近くの値を拾う規則ベースの抽出（D-015）
  - `structured_extractor.v1`：LLM の抽出。mock だけ（D-004）
  - `rule_validator.v1`：Rule pack の式を評価（3 値。`eval` しない）
  - `easf_local_mcp:locate_evidence`：根拠の位置の照合（ADR-005。自作のローカル MCP サーバ）
  - `result_exporter.v1` と `exportRunResult`（JSON・CSV。CSV インジェクション対策）
- 合成データ（請求書）：生成器・dev 28 件・正解ラベル・manifest・生成器のテスト。ホールドアウト 12 件は**人が秘密の種で生成**し、リポジトリの外に置く（fixture_plan §6）。
- 評価（dev での測定。ホールドアウトの評価は人が実行し、AI には集計値だけ）。

**やらないこと**

- 契約書の業務（Phase 4）。実 LLM API（D-004）。評価の API・画面の本格的なもの（必要な最小限だけ）。

## 3. 決めたこと（D-028）

| 項目 | 決定 | 理由 |
|---|---|---|
| PDF の解析 | **pypdfium2**（5.14.0、Apache-2.0 / BSD-3） | 日本語の合成 PDF で pdfplumber（0.11.10）と比べ、どちらも正しく抽出。pypdfium2 は 1 依存で速く、文字の番号から位置の箱を直接取れ、画像化（スキャン層の生成）にも使える。PyMuPDF は AGPL で不採用（ADR-003） |
| PDF の生成（合成データ） | **ReportLab**（5.0.1、BSD）＋ 組み込みの日本語 CID フォント（HeiseiKakuGo-W5） | フォントのファイルを同梱しなくてよい。テキスト層から正しく抽出できることを確認した |
| 根拠の位置 | 解析の出力（ページのテキスト）の**文字の番号**（開始・終了）と、その範囲の SHA-256 | 生成器も同じ解析の関数で正解の位置を決める（`fixture-data` §1） |

## 4. タスク（順に。タスクごとに CI の成功を確かめてから main へ）

| タスク | 内容 | 主な証跡 |
|---|---|---|
| P3-00 | 本計画、D-027・D-028 | — |
| P3-02a | 請求書の生成器（レコード → PDF・スキャン画像・正解ラベル）、dev 28 件、manifest（dev）、生成器のテスト、ホールドアウトの手順書、Rule pack `invoice@1.1.0`（登録済みの振込先の表を生成器の会社に合わせる） | 層の件数、根拠の範囲の一致、TEST ONLY、日付の順序、実在名の突き合わせ |
| P3-01a | 文書の API と保存 | アップロードの否定テスト（形式の偽装・サイズ・ページ数・ファイル名）、認可の全件表 |
| P3-01b | `document_parser.v1`・`rule_based_extractor.v1`・`structured_extractor.v1`（mock）・`rule_validator.v1` | Capability の契約テスト、dev での抽出の結果 |
| P3-01c | 根拠の照合（MCP）・`result_exporter.v1`・`exportRunResult` | 根拠の照合、CSV インジェクション |
| P3-01d | 請求書の Workflow を実際に流す（アップロード → 解析 → 抽出 → 検証 → 根拠 → 確認 → 出力）、画面の追加（文書・出力） | 端から端まで、画面の E2E |
| P3-04 | スキャン画像の OCR（Tesseract・日本語）。OCR 由来の根拠は「未確認」（ADR-003）。順序：ホールドアウトの凍結 → OCR の実装と dev での調整 → 最終の版でホールドアウトを 1 回評価 → G2 の判定（D-033） | OCR のテスト、dev の再評価 |
| P3-03 | dev での評価、凍結（人のホールドアウトの生成のあと）、G2 前の診断（アップロード E-01〜E-04 を必須）、G2 報告 | `reports/gate_G2.md` |

## 5. 人にお願いすること（時期が来たら知らせる）

- ホールドアウトの生成（秘密の種、`fixtures/HOLDOUT.md` の手順）と、manifest のハッシュの記録（凍結）。
- 重大ラベル（critical の層・不審な指示の層）の目視確認（`reviewed_by`）と、全社名の目視確認（fixture_plan §4）。
