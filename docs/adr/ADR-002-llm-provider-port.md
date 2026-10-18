# ADR-002 LLM の提供元とポート（Claude / OpenAI / Gemini / Azure OpenAI）

| 項目 | 内容 |
|---|---|
| 状態 | 承認（D-001・D-004）。**実 API の利用開始は別途承認** |
| 日付 | 2026-10-18 |
| 作成 | Claude Code |
| 承認 | プロジェクト責任者 2026-10-18 |

## 状況
StructuredExtractor（項目・条項の抽出）と、スキャン文書の読み取り（ADR-003）に LLM を使う可能性がある。提供元はまだ決めない（D-004）が、Claude・OpenAI・Gemini・Azure OpenAI のどれにも **設定だけで** 切り替えられるようにしておく。切り替えでエンジンや Capability の版を変えない（再利用の分類で `config_only` になること）。

## 選択肢
| 観点 | A 自前の薄いポート＋各社の公式 SDK | B 汎用の抽象化ライブラリ（LiteLLM など） | C 1 社に固定 |
|---|---|---|---|
| 4 社への対応 | アダプタ 4 つ（各 100〜200 行の見込み） | 1 つで多数 | 1 社だけ |
| 構造化出力（JSON Schema）の各社の違い | 自分で吸収し、必ずサーバ側でも検証 | ライブラリ次第で見えにくい | — |
| 依存・攻撃面 | 公式 SDK だけ（必要なものだけ入れる） | 大きい依存ツリー | 最小 |
| 費用・トークンの記録 | 各社の usage をそのまま記録 | 正規化済み | — |

## 決定
A。ポート `LlmPort` と、提供元ごとのアダプタ `anthropic` / `openai` / `azure_openai` / `gemini`、それに **`mock`** を用意する。Phase 2 では `mock` だけを有効にし、実 API のアダプタは利用開始の承認後に有効にする（コードは用意してよいが既定は無効）。

### ポート（言語に依存しない定義。Python では `typing.Protocol`）

```
LlmPort.generate_structured(request: LlmRequest) -> LlmResult

LlmRequest
  profile: str                  # 設定のプロファイル名（例 "extractor_default"）。提供元名ではない
  instructions: str             # システム側の指示（固定のテンプレートから作る）
  documents: [DocumentPart]     # データ（テキストのページ、または画像）。指示とは別の区画で渡す
  output_schema: JSONSchema     # 期待する出力。提供元へは対応できる範囲に変換して渡し、戻りは元のスキーマで必ず検証
  max_output_tokens: int
  temperature: float | null     # 再現性のため既定 0（提供元が対応する場合）
  timeout_ms: int
  trace_context: {run_id, node_run_id, trace_id}

LlmResult
  status: "ok" | "invalid_output" | "refused" | "timeout" | "rate_limited" | "provider_error" | "budget_exceeded"
  output: object | null         # output_schema で検証済みのときだけ
  provider: "anthropic" | "openai" | "azure_openai" | "gemini" | "mock"
  model: str                    # 実際に応答したモデル名・版（取得できれば）
  execution_mode: "real" | "mock"
  usage: {input_tokens, output_tokens}
  cost_jpy: decimal | null      # 料金表がない・未確認なら null（推測しない）
  latency_ms: int
  provider_request_id: str | null
  raw_output_sha256: str        # 生の出力はトレースに保存せず、ハッシュだけ
```

- **Capability は提供元を知らない**。ノードの `config.llm_profile` でプロファイル名だけを指定する。
- プロファイルは **設定ファイル**（`config/llm_profiles.yaml`、スキーマは `contracts/llm_profile.schema.json`）で管理し、API からは作成・変更できない（接続先を API から変えられると SSRF の入口になるため）。画面には読み取り専用の一覧（`GET /api/v1/llm-profiles`）だけを出す。

### 提供元ごとの扱い（実装時に公式文書で再確認する）

| provider | SDK（候補） | 接続先（許可リスト） | 認証 | 構造化出力 | 備考 |
|---|---|---|---|---|---|
| `anthropic` | `anthropic`（MIT） | `api.anthropic.com` | API キー | JSON Schema による構造化出力、またはツール定義の入力スキーマ | モデル名は設定 |
| `openai` | `openai`（Apache-2.0） | `api.openai.com` | API キー | `json_schema`（strict）形式の応答 | |
| `azure_openai` | `openai`（Azure 用クライアント） | 設定した `https://<resource>.openai.azure.com` の完全一致 | API キー（将来は Entra ID） | OpenAI と同じ | モデル名ではなくデプロイ名。`api_version` を設定。データの所在地（リージョン）を記録 |
| `gemini` | `google-genai`（Apache-2.0） | `generativelanguage.googleapis.com` | API キー | 応答スキーマ（JSON）指定 | Vertex AI 経由は将来の別 provider とする |
| `mock` | なし | 接続しない | なし | 固定の応答（合成データの正解とは別に作った決定的な出力） | `execution_mode: "mock"`。実接続の件数に数えない |

### 安全（`jp-secure-coding` ai-llm-mcp.md）

- API キーは環境変数。プロファイルの `api_key_env` は `EASF_LLM_` で始まる名前だけ許す（設定から DB のパスワードなど他の環境変数を読めないように）。
- 接続は共通の安全な HTTP クライアント（許可リスト・リダイレクト拒否・タイムアウト・応答サイズ上限）を通す。SDK の HTTP クライアントを差し替えられない場合は、SDK に渡すベース URL を固定値にし、エグレスの許可リスト（コンテナのネットワーク設定）で補う。
- LLM にツールを渡さない（抽出はテキスト → JSON だけ）。
- 送るのは合成データだけ。各社のデータ保持・学習利用の条件は、実 API の利用開始時に公式の規約で確かめ、この ADR に日付付きで追記する。
- 料金は記憶から書かない。利用開始時に公式の料金ページで確かめ、プロファイルの `pricing`（`source_url`・`verified_at` 付き）に入れる。

### 予算と記録
- 実行（Run）ごとのトークン・円の上限（Workflow の `budget`）と、日ごとの上限（設定）。超えたら `budget_exceeded` で失敗（成功にしない）。
- 呼び出しごとに provider・model・usage・cost_jpy・latency を NodeRun とトレースに記録し、実費は `COST_LEDGER.csv` に月ごとに転記する（請求の実額で照合）。

## 理由
4 社とも「JSON Schema に沿った構造化出力」に対応しているが、細部（使えるスキーマの範囲、拒否・打ち切りの返し方、usage の形）が違う。ポートを薄く保ち、検証をサーバ側に一本化すれば、提供元を変えても評価の条件が揃う。抽象化ライブラリは依存が大きく、POC の 4 社のために入れる利点が小さい。

## 影響・やらないこと
- 提供元の比較実験（どれが精度が高いか）は範囲外。必要なら変更要求。
- ストリーミング・会話履歴・エージェント的なツール利用は使わない。
- 実 API の有効化は、(1) D-004 の承認、(2) 料金・データ条件の確認と追記、(3) `COST_LEDGER.csv` の予算確認、の後。

## 確かめた資料
未確認（実 API の利用開始時に各社の公式文書・料金ページ・利用規約を確認し、URL と確認日を書く）。
