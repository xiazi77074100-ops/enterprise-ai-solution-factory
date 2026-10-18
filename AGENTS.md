# enterprise-ai-solution-factory（EASF）

Claude Code と Codex の両方が読む共通の規則。`CLAUDE.md` は `@AGENTS.md` を読むだけ。

## 1. 正本と現在地

- 仕様の正本は `easf_package/`（README・docs・schemas・tasks・prompts）。**読み取り専用**。変更は変更要求（`easf_package/docs/06_DECISIONS_AND_RISKS.md` の Change control）を通す。
- 現在地は `docs/HANDOFF.md`（**新しいセッションは最初に読む**）。2026-10-19 時点で Phase 2 が完了し、**G1b の承認待ち**（`reports/gate_G1b.md`）。G0・G1a は承認済み（D-014・D-024）、契約 v1 は凍結（現在 1.0.2）。Phase 0 の計画書は `docs/phase0/PHASE0_PLAN.md`。開発環境は `docs/design/dev_setup.md`。決定は `DECISIONS.md`、タスクは `TASK_STATUS.md`。
- EASF は個人の独立した POC（D-002）。会社の資産・データ・アカウント・端末・勤務時間を使わない。
- 各フェーズは承認されたタスクだけを行う。次のゲートの承認前に次のフェーズのコードを書かない。
- ゲートを飛ばさない。各フェーズの終わりで止まり、人間の go / no-go を待つ（`easf-phase-gate` skill）。

## 2. 言語

- 画面・業務文言・進捗報告・レビュー報告・設計書は日本語。API・クラス名・JSON キー・コード識別子は英語。
- 中国語の文言を新しく作らない（コメント・コミット・文書を含む）。

## 3. 役割とファイル所有

| 担当 | 役割 | 単独所有するもの |
|---|---|---|
| Claude Code（CC） | 統合責任者。設計・共通契約・バックエンド中核・統合・ゲート報告 | `contracts/`、`backend/migrations/`、`backend/app/{catalog,composer,executor,adapters}`、`AGENTS.md`、`.claude/skills/` |
| Codex | 独立レビュー・独立テスト・割り当てられた UI と業務ルール・比較実験。**必須ではない**（D-011）：使えないときは CC が代行し、自己レビューであることを報告に書く | 引き渡し書（handoff）で指定されたパスだけ |
| 人間 | 仕様・ADR・費用・フェーズ移行・外部公開の承認 | — |

- 同じファイルを並行して変えない。共通 API・スキーマ・マイグレーションは CC だけが変える。Codex が変更を要するときは引き渡し書に「変更要求」として書く。
- 作業は担当ごとのブランチ（`cc/<task-id>-<slug>`、`codex/<task-id>-<slug>`）。マージは契約テスト・独立レビュー後に CC が行う。
- **タスクを 1 つ終えるごとに、コミット → プッシュ → `main` へ fast-forward でマージ → プッシュしてから次のタスクへ進む**（D-013）。ゲートの承認が要る地点では止まる。

## 4. skill（必ず該当するものを読んでから作業する）

| skill | 使う場面 |
|---|---|
| `easf-phase-gate` | フェーズ・タスクの着手と終了、ゲート報告、Codex への引き渡し、台帳（決定・タスク・変更履歴・費用・工数）の更新 |
| `easf-capability-contract` | Capability・Workflow・Rule pack・アダプタの追加や変更、契約スキーマ、版管理、証跡（evidence） |
| `easf-eval-integrity` | 合成データ・正解ラベル・ホールドアウト・評価・ベースライン比較実験 |
| `jp-secure-coding` | **コードを書くときは常に**。IPA「安全なウェブサイトの作り方」・ウェブ健康診断仕様・OWASP ASVS に沿った実装規則（FastAPI / React / LLM / MCP） |
| `jp-vuln-assessment` | ゲート前の脆弱性セルフ診断（第三者診断と同じ観点）、診断報告書 |
| `jp-dev-standards` | コーディング規約・命名・日付と金額・設計書・テスト仕様書・レビュー記録・コミット |
| `ui-design` | **画面を作る・直すときは必ず**。EASF の UI 規約（部品・表・フォームの 3 つの約束・選択肢・ダイアログ・待ち・文字と色・実行と模擬・根拠・AI 下書きの見せ方） |
| `spec-sync` | 画面・API・項目・操作・入力チェック・権限・状態遷移を変えたら、同じコミットで設計書を直す |
| `fixture-data` | 合成データの生成器・正解ラベル・画面の集計の整合 |
| `japan-enterprise-frontend` | 日本の業務システムの UI の汎用原則（`ui-design` の背景） |
| `design-taste-frontend` / `redesign-existing-projects` | 余白・揃え・配色の調整と、既存画面の見た目の点検だけ。**`ui-design` と食い違ったら `ui-design` が優先**（LP 向けの装飾・動きを業務画面に持ち込まない） |
| `ponytail` / `ponytail-review` | 既存の部品・標準ライブラリを再利用し最小のコードで書く／作りすぎのレビュー |

- フロントエンドの skill は `D:\aidd\sales-assistant` から取り込んだ。`ui-design`・`spec-sync`・`fixture-data` は同リポジトリの `ui-design`・`demo-spec-sync`・`demo-mock-data` を EASF 向けに書き直したもの（出所は `.claude/skills/README.md`）。画面の見た目（部品の作り・面の構成・浮動ラベル・サイドバー・ヘッダ帯・ログイン画面）は sales-assistant の UI を手本にしてよい（D-026）。ただし配色は EASF の色（青緑・ミント・空色）に変え、sales-assistant の製品名・ロゴ・会社名・著作権表示・業務用語・データは使わない。
- sales-assistant の skill が更新されたら、同じ表の対応で差分を確かめて取り込み、README の取得日を直す。
- skill の正本は `.claude/skills/`。Codex 用の `.agents/skills/` はその写し。skill を足す・直したら `python scripts/sync_skills.py` を実行して両方をコミットする。`python scripts/sync_skills.py --check` はずれ・frontmatter の不備で失敗する（Phase 1 で CI に入れる）。

## 5. 禁止事項

- 2 つの業務を `if scenario == "invoice"` のように分岐で作る、固定の 2 デモにする、Claude Code / Codex のラッパーにする。
- 模擬（MOCK）を実接続として見せる・数える。未実行のテストを成功と書く。測っていない効果（30% 削減など）を書く。
- 会社（MCT / SBI）・顧客の非公開コード・データ・API 仕様・アカウントを許可なく使う。実在の SBI / AI Hub のエンドポイントを推測で作る。
- 任意コード実行、`shell=True`、任意 URL への接続、許可リスト外の MCP ツール呼び出し、秘密情報のコミット・ログ出力。
- 実際の送金・会計計上・法的助言。
- 初期の追加現金支出 10,000 円を超える前に承認を得ずに使う。

## 6. 報告

- 進捗・ゲート報告は日本語。実行したコマンド・終了コード・出力の要点・コミット SHA を付ける。実行していないものは「未実行」と書き、理由を添える。
- 事実と推測を分ける。不明な点は「不明（要確認）」と書き、作り話で埋めない。
