# Phase 0 計画書（G0 計画の承認申請）

| 項目 | 内容 |
|---|---|
| 版 | 0.1 |
| 日付 | 2026-10-18 |
| 作成 | Claude Code（統合責任者） |
| 状態 | **計画は承認済み**（2026-10-18、D-001）。Phase 0 の成果物を作成中。アプリケーションコードは未着手 |
| 根拠 | `easf_package/` の README・docs 00〜08・schemas・examples・tasks・prompts 00〜04 を全部読んだうえで作成 |

---

## A. プロジェクトの理解（1 ページ）

**何を作るか**：日本企業向けの AI コンサル・プリセールス・導入チームが、業務要件から「検証できる POC」を短期間で組み立て、実行結果・品質・再利用の証拠を資産として残すための仕組み（Enterprise AI Solution Factory）。

**どう証明するか**：版管理された 6 つの共通 Capability（DocumentParser・StructuredExtractor・RuleValidator・EvidenceLocator・HumanReview・ResultExporter）を、**同じ版のまま設定と Rule pack だけ変えて** 2 つの業務で実行し、トレース ID で裏付ける。

| 業務 | 流れ | 出力 |
|---|---|---|
| A 請求書処理 | 合成請求書 → 解析 → 項目抽出 → ルール確認（合計不一致・登録番号欠落・振込先変更・期日欠落・番号重複） → 根拠表示 → 人の確認・修正 | 構造化 JSON / CSV（送金・計上はしない） |
| B 契約書レビュー | 合成契約書 → 解析 → 条項抽出 → ポリシー確認（必須条項欠落・過大な責任上限・自動更新・通知期間欠落） → 根拠表示 → 人の確認・修正 | レビューレポート（法的助言ではない。「あり・なし・不明」を区別） |

**プラットフォーム側**：Catalog（不変の版）・Composer（型付き DAG）・Executor（状態機械・一時停止と再開・時間とリトライの上限）・Trace・Evaluator（凍結した正解データ）・Reuse Tracker。

**成功の定義**：2 件目の案件の総工数が、AI Coding のみ（Claude Code / Codex）の熟練者と比べて 30% 以上少なく、品質が劣らず、重大な誤りを黙って通さないこと。**これは検証する目標であって、結果ではない。** 未達なら未達と報告し、部品ライブラリ＋手順書への方向転換を検討する。

**制約**：1〜2 か月、追加現金支出の初期上限 10,000 円、日本語 UI、合成データのみ、各ゲートで人の承認。

**対象外**：本番のマルチテナント、送金・会計計上・銀行連携、法的意見、完全自律のコード生成、グループの ID 基盤、マーケットプレイス・課金、汎用 Agent ランタイム、全社展開、SBI AI Hub など未公開 API との接続、文書以外の業務への一般化の主張、メール送信機能。

---

## B. Phase 0 のチェックリストと ADR

### B-1. Phase 0 の成果物

| # | 成果物 | 置き場所 | 担当 | 状態 |
|---|---|---|---|---|
| 0 | AI 開発の skill 一式（CC / Codex 共通）と共通規則 | `AGENTS.md`、`CLAUDE.md`、`.claude/skills/`、`.agents/skills/`、`scripts/sync_skills.py` | CC | **作成済み**（本書と一緒に提出。§G） |
| 1 | 本計画書（A〜F） | `docs/phase0/PHASE0_PLAN.md` | CC | **作成済み** |
| 2 | ADR-001〜009 | `docs/adr/` | CC | **作成済み・承認済み** |
| 3 | モジュール境界と所有表 | `docs/design/basic/architecture.md` | CC | **作成済み** |
| 4 | 契約 v1（OpenAPI・Capability・Workflow・Rule pack・イベント・LLM プロファイル）と例 | `contracts/`、`contracts/examples/` | CC | **作成済み**（`scripts/validate_contracts.py` で検査。凍結は G0） |
| 5 | 脅威モデル（STRIDE＋LLM）とセキュリティ設計 | `docs/design/security.md` | CC | **作成済み** |
| 6 | 合成データ計画（層・件数・生成器・manifest の書式） | `docs/design/fixture_plan.md` | CC（D-011） | **作成済み** |
| 7 | ベースライン実験の事前登録 | `docs/experiment/preregistration.md` | CC（D-011）→ 人の承認 | **作成済み（承認待ち）** |
| 8 | 見積と台帳 | `docs/phase0/estimates.md`、`DECISIONS.md`、`TASK_STATUS.md`、`CHANGELOG.md`、`COST_LEDGER.csv`、`HUMAN_TIME_LOG.csv` | CC | **作成済み** |
| 9 | G0 レビュー（敵対的な自己レビュー） | `reviews/G0_REVIEW.md` | CC（D-011・D-012） | 作成中 |
| 10 | G0 ゲート報告 | `reports/gate_G0.md` | CC | 最後 |

### B-2. Workflow 方式の比較（PHASE_PLAN の必須項目）

| 観点 | 案 1：自前の軽量な型付き DAG | 案 2：LangGraph | 案 3：Temporal / Prefect |
|---|---|---|---|
| 中身 | 標準ライブラリ `graphlib` で順序付け、実行状態は PostgreSQL の状態機械（Run / NodeRun）、一時停止は ReviewTask の行 | LLM 向けのグラフ実行ライブラリ。チェックポイントと human-in-the-loop の仕組みがある | 本格的なワークフローエンジン（別サーバ・ワーカー） |
| 版の固定・スキーマ検証・証跡 | 自分で作る（ただし EASF の中核そのもの） | グラフ定義がコードなので「データとしての Workflow・版の固定」を別に作る必要 | 同上。加えて運用が重い |
| 一時停止と再開 | DB の状態で表現。単純 | 組み込みあり | 組み込みあり |
| 依存・攻撃面 | 最小 | 中（LangChain 系の依存） | 大（別サービス） |
| 1〜2 か月の POC | 適する | 可 | 過剰 |
| 「Claude Code のラッパーではない」「汎用エンジンに業務分岐なし」の証明 | しやすい（全部見える） | 可 | 可 |

**推奨：案 1**。ノード数が 6〜8 の小さな DAG で、ループは使わない。中核の価値（版の固定・3 か所の検証・証跡）はどの案でも自作になるため、外部エンジンの利点が小さい。LangGraph は「将来の Agent ランタイムのアダプタ」として位置付ける。

### B-3. ADR の候補（承認後に比較表つきで作成。版・ライセンス・保守状況は作成時に公式の情報で確かめて確認日を書く）

| ADR | 決めること | 候補 | 現時点の推奨（理由） |
|---|---|---|---|
| 001 | Workflow エンジン | 上の 3 案 | 案 1（B-2） |
| 002 | モデル提供元・料金・データの扱い・再現性 | Claude / OpenAI / Gemini / Azure OpenAI | **決定（D-004）**：提供元に依存しないポート＋ 4 社のアダプタ＋ mock。実 API は保留し mock で進める。ルール判定は LLM を使わない |
| 003 | 日本語 PDF・OCR | テキスト層の抽出（pypdfium2 / pdfplumber 等）、Tesseract（jpn）、PaddleOCR、LLM の画像入力、クラウドの文書解析 | テキスト層のある PDF を主、スキャン画像は LLM の画像入力を従とする 2 段。**PyMuPDF は AGPL のため採用しない前提**。スキャン文書の件数で費用を見積もる |
| 004 | DB・保存・マイグレーション | PostgreSQL ＋ SQLAlchemy 2 ＋ Alembic、保存はローカルのボリューム / MinIO | PostgreSQL＋Alembic、文書はローカルのボリューム（MinIO は AGPL かつ POC に不要） |
| 005 | MCP SDK と契約の対応 | 公式 Python SDK | 公式 SDK。自作のローカル MCP サーバ（stdio）で 1 つの Capability を提供し「実際の MCP ツール呼び出し」とする。**外部の実連携ではないことを明記**。`mcp_resource` / `mcp_prompt` は実行ノードにしない |
| 006 | POC の認証と秘密管理 | サーバ側セッション＋ Cookie、JWT、OIDC（Keycloak 等） | サーバ側セッション（`__Host-` Cookie、CSRF トークン、argon2id）。JWT を localStorage に置く方式は診断で指摘されるため採らない。ロール：Solution Lead / Architect / QA / Business Reviewer / Admin |
| 007 | 品質の閾値とホールドアウト | 下の D-2 の提案値 | D-2 |
| 008 | ベースライン実験の順序 | 下の D-2 の提案 | D-2 |
| 009 | フロントエンドの部品ライブラリ | Ant Design（仕様の候補）、Tailwind ＋ Radix | **決定（D-010）：Tailwind ＋ Radix**（`ui-design` skill をそのまま適用でき、CSP を厳しくできる） |

### B-4. 提供されたスキーマの確認結果（契約 v1 で直す点）

| # | 対象 | 問題 | 直し方の案 |
|---|---|---|---|
| S1 | capability | `implementation.reference`（`module:function`）を文字列のまま import すると任意コード実行の入口になる | 起動時に登録した許可リストのキーとして解決（skill `easf-capability-contract` §2） |
| S2 | capability | `input_schema` などに外部 `$ref` を書けると、検証時に SSRF になる | 外部 `$ref` を禁止し、検証器の取得を無効にする |
| S3 | capability | `configuration_schema` が任意で、ノードの `config` を検証できない | 必須にする |
| S4 | capability | `applicability: ["invoice","contract"]` が業務名をエンジンに持ち込む余地 | 検索用のタグとしてだけ扱い、エンジンの分岐に使えないことをテストで保証 |
| S5 | capability | 入出力・設定のサイズ上限がない | 文字列・配列の上限、`additionalProperties: false` を必須の書き方に |
| S6 | capability | `kind` に `mcp_resource` / `mcp_prompt` があるが実行の意味が不明 | v1 は `local` / `rest` / `mcp_tool` / `llm`。Resource・Prompt は参照データとして別扱い |
| S7 | workflow | 辺（edges）がノード間のつながりだけで、どの出力をどの入力に渡すかがない | 辺に `mapping`（出力のパス → 入力の項目）を足し、構成時に型を照合 |
| S8 | workflow | 人の確認（HumanReview）・タイムアウト・リトライ・予算のノード単位の設定がない | ノードに `timeout_ms`（上限あり）・`retry`（冪等なときだけ）、Workflow に `budget` |
| S9 | workflow | `capability_version` に範囲を書けてしまう（パターンなし） | 完全な semver のパターンを必須に |
| S10 | examples | 例が 3 ノード（parse・extract・validate）だけで、根拠・確認・出力がない | 6 Capability を使う完全な例を 2 業務分 |
| S11 | 全体 | イベント・Rule pack・評価結果のスキーマがない | `events.schema.json`、`rule_pack.schema.json` を追加 |

---

## C. リポジトリ構成・モジュール境界・担当

### C-1. 構成（案）

```
AGENTS.md / CLAUDE.md                 共通規則（作成済み）
.claude/skills/ → .agents/skills/     skill（正本 → Codex 用の写し。作成済み）
easf_package/                         仕様キット（読み取り専用）
contracts/                            OpenAPI・JSON Schema（CC 単独所有。G0 で凍結）
docs/{phase0,adr,design,test,experiment}/
backend/
  app/
    api/            ルータ（認証の依存性を既定で付与）
    core/           設定・DB・セキュリティ（セッション・CSRF・ヘッダ・安全な HTTP クライアント）
    project/ catalog/ composer/ executor/ adapters/ evaluation/ observability/ reuse/
    domain/         6 つの Capability の実装と Rule pack の読み込み（業務名はここと設定にだけ現れる）
  migrations/       Alembic（CC 単独所有）
  tests/{unit,integration,contract,security}/
frontend/           React + TypeScript + Vite（Ant Design は ADR-009）
  src/{app,components,features/<画面>,api(生成)}
rulepacks/          invoice-v1・contract-v1 など（データ）
fixtures/           生成器・dev 用の文書と正解・manifest（ホールドアウトの正解は置かない）
reports/  reviews/  handoffs/  scripts/
```

**依存の向き**（import-linter などで CI 検査）：`domain` は `executor` を import しない、`executor` は `domain` を import しない（レジストリ経由だけ）、汎用モジュールに業務名の文字列が出ない（テストで検査）。

### C-2. CC と Codex の担当

| 領域 | Phase 0 | Phase 1〜2 | Phase 3〜4 | Phase 5〜6 |
|---|---|---|---|---|
| 契約・マイグレーション | CC | CC（単独） | CC（単独） | CC |
| Catalog・Composer・Executor・アダプタ | — | CC | CC | CC |
| 6 つの Capability | — | — | CC（請求書で作る） | — |
| Rule pack・業務設定 | — | — | 請求書：CC／**契約：Codex**（同じ版を使う） | — |
| UI | — | Codex（画面の枠・案件画面） | Codex（実行・確認画面） | CC（デモ） |
| 契約テスト・否定テスト | — | Codex | Codex（独立テスト） | — |
| 合成データ・正解 | Codex（計画） | — | Codex（生成）＋人（確認） | — |
| セキュリティ自己診断 | CC（設計） | CC 実施・Codex 確認 | 同左 | Codex（独立レビュー） |
| ベースライン実験 | Codex（事前登録案） | — | — | Codex（**別リポジトリ・別セッション**） |
| ゲート報告・統合 | CC | CC | CC | CC |

**変更（D-011・D-012）**：Codex は必須ではない。P0-02・P0-04 は CC が実施し、独立性の低下は D-012 の方法で補う。以下の表の Codex の担当は「Codex が使えれば Codex、使えなければ CC」と読む。

並行作業は G0 で契約を凍結した後だけ。G0 前に Codex に頼むのは独立レビュー（`prompts/01`）・合成データ計画・事前登録の案だけ。

---

## D. G0 の受入条件と、決めていただきたいこと

### D-1. G0 の受入条件（提案）

1. ADR-001〜009 が「承認」になっている（未決のものは理由と期限つき）。
2. `contracts/` の v1 が凍結され、§B-4 の S1〜S11 が対応済みか、理由付きで見送り。
3. 脅威モデルと `jp-secure-coding` の対応表、ゲートのセキュリティ条件（高・中 0 件など）が承認されている。
4. 合成データ計画・manifest の書式・ホールドアウトの保管方法・閾値（D-2）が事前登録されている。
5. ベースライン実験の事前登録が承認されている。
6. G0 レビュー（`reviews/G0_REVIEW.md`。D-011・D-012 により自己レビュー）の BLOCKER・MAJOR がすべて閉じている。
7. 見積・台帳のひな形があり、追加現金支出の累計が記録されている。
8. 権利関係の確認（D-3 の 1・2）が済んでいる。
9. G0 までにアプリケーションコードを書いていない（コミット履歴で確認できる）。

### D-2. 数値の提案（ADR-007・008。ホールドアウトを見る前に決める）

| 項目 | 提案値 |
|---|---|
| 重大な誤りの黙認（重大項目の誤りが確認を経ずに「成功」になる） | **0 件**（必須。1 件でも不合格） |
| ホールドアウト | 各業務 10 件以上、全体の 25〜30%、層別 |
| 項目抽出（dev での目安、正規化一致のマクロ平均） | 0.85 以上（目安。合否はホールドアウトで判定） |
| 重大ルールの再現率（ホールドアウト） | 1.0（見逃しは「確認へ回した」なら可） |
| 根拠の位置の正しさ（照合できた根拠のうち） | 0.9 以上、照合できないものは「未確認」と表示されること |
| 確認の記録の完全さ | 100%（確認者・時刻・修正前後） |
| セキュリティ | 自己診断で高・中 0 件、SCA の高・重大 0 件、秘密の検出 0 件 |
| ベースラインの順序 | 契約書レビュー（2 件目の業務）について、**ベースラインを先に**別リポジトリ・別セッションで実施 → その後 Factory 側で Phase 4。同じ人が両方を行う学習効果は「妥当性への脅威」として報告。可能なら評価者を別にする |
| 要件変更の実験 | 両方の arm で同じ変更要求（例：契約のポリシーに 1 条項追加、請求書に 1 項目追加）を行い工数を比べる |

### D-3. 決めていただきたいこと

1. **権利関係（最優先）**：このリポジトリの git ユーザーは `mct-chengwei`、sales-assistant のコミットは `@mct-japan.co.jp` のアドレスで、公開先も MCT のテナントです。仕様（`04_SECURITY_AND_IP.md`）は会社の資産・端末・アカウント・勤務時間の無断使用を禁じています。EASF は **個人の独立した POC** ですか、それとも **会社の業務** ですか。これによって、コミットに使う名前とアドレス、使ってよい端末と時間、外部公開の条件が変わります。
2. **取り込んだ skill の扱い**：`japan-enterprise-frontend`（sales-assistant で作った汎用の UI skill）を EASF で使ってよいことの確認。外部の MIT の skill 4 つは LICENSE を同梱済み。
3. **LLM の利用**：Claude API を使ってよいか、使うアカウント（個人・会社）、10,000 円のうち LLM に充てる上限（提案：5,000 円、残りは予備）。
4. **スキャン文書の範囲**：回転・低品質のスキャン画像を合成データの層に含めるか（含めると OCR の費用と手間が増える。提案：各業務 5 件程度だけ含める）。
5. **公開・診断の環境**：デモと診断はローカル（Docker Compose）だけでよいか。第三者の脆弱性診断を実際に受ける予定があるか（あるなら、公開する環境・HTTPS・診断の基準を ADR に足す）。
6. **D-2 の数値**：このままでよいか、変更があればご指示ください。

---

## E. リスク

| 区分 | リスク | 影響 | 対策 |
|---|---|---|---|
| 実験の妥当性 | 同じ人・同じ AI が両方の arm を行う学習効果、件数の少なさ | 30% の判断が信頼できない | ベースラインを先に、別リポジトリ・別セッション、工数の細目を記録、脅威として明記、損益分岐は前提付き |
| 実験の妥当性 | ホールドアウトの漏れ（AI が正解を見る） | 品質の過大評価 | 正解はリポジトリの外、ハッシュだけ記録、漏れたら止めて記録 |
| プロンプトインジェクション | 文書中の指示で金額・口座の判定が変わる | 重大な誤りの黙認 | LLM にツールなし、出力のスキーマ検証、重大項目はルールと人の確認、不審な指示を含む合成データで試験 |
| セキュリティ | 第三者診断で認可・セッション・ヘッダの指摘 | 受け入れの遅れ | `jp-secure-coding` で書く時点で対策、認可の期待値表を全 API で自動テスト、ゲートごとの自己診断 |
| 法務・知財 | 会社の資産・時間・アカウントの使用（D-3-1）、sales-assistant 由来のものの扱い | プロジェクトの継続・公開ができない | G0 で確認。取り込んだのは skill だけで、コード・データは使わない |
| 法務・知財 | 実在の請求書・契約書の様式の写し、実在の会社名・口座 | 権利・個人情報の問題 | 生成器で作る架空のデータ、TEST ONLY の印 |
| 法務 | 契約レビューが法的助言と受け取られる | 責任問題 | 「あり・なし・不明」と根拠だけ、画面と報告に注意書き |
| 統合 | CC と Codex の同時変更・契約のずれ | 手戻り | 契約の単独所有、凍結、契約テスト、引き渡し書 |
| 統合 | 模擬の連携が実連携に見える | 信頼の失墜 | `execution_mode` の記録と画面のバッジ、報告で区別 |
| 予算 | LLM・OCR の費用超過 | 上限 10,000 円の超過 | 実行予算の上限、費用の台帳、上限の前に承認 |
| 予算・期間 | 画面の作り込み・範囲の広がり | 期間超過 | 毎週の確認、画面の装飾は後回し、変更要求の手続き |
| 一般化 | 文書の業務 2 つで汎用性を主張してしまう | 誤った判断 | 報告で範囲を明記 |

---

## E2. 回答（2026-10-18）

§D-3 の 6 点への回答は `DECISIONS.md` の D-002〜D-008。LLM は実 API を保留し、4 社に対応するポートを用意（D-004）。

## F. 承認のお願い

**この Phase 0 計画（§B-1 の成果物の作り方、§B-2 の推奨、§C の構成と担当、§D-1 の G0 受入条件）で進めてよろしいでしょうか。あわせて §D-3 の 6 点についてご回答をお願いします。**

承認をいただくまで、ADR・契約などの Phase 0 の残りの成果物には着手せず、アプリケーションコードも書きません。

---

## G. 作成済みの skill（AI 開発の共通基盤）

Claude Code は `.claude/skills/`、Codex は `.agents/skills/` を読む。共通の規則は `AGENTS.md`（Claude Code は `CLAUDE.md` から読み込む）。

| skill | 目的 |
|---|---|
| `jp-secure-coding` | IPA「安全なウェブサイトの作り方」11 項目・ウェブ健康診断 13 項目・OWASP ASVS・OWASP Top 10 for LLM に沿った、書く時点の実装規則（FastAPI / React / アップロード / LLM・MCP / 依存と秘密） |
| `jp-vuln-assessment` | 第三者診断と同じ観点の自己診断（SAST・SCA・秘密・コンテナ・ZAP・手動 60 項目超）、CVSS による判定、診断報告書、ゲートの条件 |
| `jp-dev-standards` | コーディング規約、和暦・JST・金額と消費税の端数・登録番号・全角半角、設計書・テスト仕様書・試験成績・レビュー指摘票、コミット |
| `easf-phase-gate` | フェーズとゲートの運用、台帳、ゲート報告、Codex への引き渡し、正直な報告 |
| `easf-capability-contract` | 不変の版、3 か所のスキーマ検証、業務分岐の禁止、証跡、模擬の区別、Rule pack、再利用の分類 |
| `easf-eval-integrity` | 合成データ、ホールドアウトの凍結と隔離、閾値の事前登録、ベースラインの公平さ |
| `japan-enterprise-frontend` ほか 4 つ | sales-assistant から取り込んだフロントエンドの skill（出所とライセンスは `.claude/skills/README.md`） |

同期の確認：`python scripts/sync_skills.py --check`（2026-10-18 に実行、終了コード 0。写しをわざとずらすと終了コード 1 になることも確認済み）。
