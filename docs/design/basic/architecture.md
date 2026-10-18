# 基本設計：方式設計（構成・モジュール境界・外部接続）

| 版 | 日付 | 変更内容 | 作成者 |
|---|---|---|---|
| 0.1 | 2026-10-18 | 初版（Phase 0） | Claude Code |

## 1. 全体構成

```
ブラウザ（React + TS、日本語 UI）
   │ 同一オリジン、Cookie セッション + CSRF トークン
   ▼
FastAPI（モジュラーモノリス）─── PostgreSQL（メタデータ・状態・トレース・キュー）
   │                          └─ 文書のボリューム（Web から配信しない）
   ├─ ワーカー（同じコードベース、別プロセス）：Workflow のノード実行
   │     ├─ local アダプタ：レジストリに登録した関数
   │     ├─ mcp_tool アダプタ ── 自作のローカル MCP サーバ（stdio）
   │     ├─ llm アダプタ ── LlmPort ── mock（既定）／anthropic／openai／azure_openai／gemini（D-004 で無効）
   │     └─ rest アダプタ（許可リストの接続先のみ。POC では未使用）
   └─ 解析の子プロセス（PDF・OCR。時間・メモリの上限）
```

すべて Docker Compose。DB のポートは 127.0.0.1 にだけ公開する。外部への通信は LLM の許可リストのホストだけ（実 API 有効化後）。

## 2. モジュールと依存の向き

| モジュール | 責務 | 依存してよい先 |
|---|---|---|
| `api` | ルータ、認証・CSRF・認可の依存性、入出力モデル | 下のすべて（サービス層経由） |
| `core` | 設定、DB、セッション、ヘッダ、安全な HTTP クライアント、ログの伏せ字 | なし |
| `project` | 案件・要件の版・承認 | core |
| `catalog` | Capability・Rule pack の版、不変性、契約の検証、内容ハッシュ | core |
| `composer` | Workflow の検証（版の解決・設定・辺の型・循環・予算）、解決策のハッシュ | core, catalog |
| `executor` | 状態機械、ノード実行、一時停止と再開、リトライ・タイムアウト・予算 | core, catalog, adapters（ポートだけ）, observability |
| `adapters` | local / mcp_tool / llm / rest のアダプタ、LlmPort | core |
| `domain` | 6 つの Capability の実装、Rule pack の評価器、根拠の照合 | core（**executor・composer を import しない**） |
| `evaluation` | データセットの版、採点、報告 | core, catalog, observability |
| `observability` | イベント・トレース・費用の記録、伏せ字 | core |
| `reuse` | 再利用の記録と集計 | core, observability |

- `domain` の実装は起動時にレジストリへ登録し、`executor` はレジストリのキー（`implementation.ref`）で呼ぶ。
- **予約入力 `project_context`**：Executor は、Capability の入力スキーマに `project_context` があるとき、同じ案件の成功した実行の確認済みの値を、実行開始時点のスナップショットとして渡す（辺からは渡さない）。Capability は DB を直接読まない（RV-G0-002）。
- 汎用モジュール（catalog・composer・executor・adapters・evaluation・observability・reuse）に業務名を書かない。`scripts/validate_contracts.py` が検査し、Phase 1 で import-linter による依存の向きの検査を CI に加える。

## 3. LLM ポート（ADR-002）

```
domain.structured_extractor ──(llm_profile 名)──> adapters.llm.LlmPort
                                                   ├─ MockLlmAdapter        execution_mode=mock（既定で有効）
                                                   ├─ AnthropicAdapter      enabled=false
                                                   ├─ OpenAIAdapter         enabled=false
                                                   ├─ AzureOpenAIAdapter    enabled=false
                                                   └─ GeminiAdapter         enabled=false
```

- プロファイルは `config/llm_profiles.yaml`（`contracts/llm_profile.schema.json`）。起動時に検証し、`enabled: true` で `model: CHANGE_ME` のもの、API キーの環境変数が無いもの、許可リスト外の接続先は起動エラー。
- 提供元を切り替えるのはノードの `config.llm_profile` の値だけ。Capability の版は変わらない。
- すべての応答は `output_schema` でサーバ側検証。usage・費用・遅延は NodeRun に記録。
- 実 API の有効化手順：D-004 の承認 → ADR-002 の「確かめた資料」を埋める → プロファイルの `pricing` と `data_handling_note` を記入 → `enabled: true` → 費用の台帳で確認。

## 4. 外部接続一覧

| 接続先 | 用途 | 状態 |
|---|---|---|
| `api.anthropic.com` | LLM | 無効（D-004） |
| `api.openai.com` | LLM | 無効（D-004） |
| `<resource>.openai.azure.com` | LLM | 無効（D-004） |
| `generativelanguage.googleapis.com` | LLM | 無効（D-004） |
| ローカル MCP サーバ（stdio） | EvidenceLocator | 有効（外部接続ではない） |

## 5. 画面

`easf_package/docs/05_UI_AND_DEMO.md` の 8 画面。規約は `ui-design` skill。部品は Tailwind CSS ＋ Radix（ADR-009、D-010）。
