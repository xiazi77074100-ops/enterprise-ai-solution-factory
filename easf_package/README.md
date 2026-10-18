# Enterprise AI Solution Factory (EASF) — AI Coding Delivery Kit

バージョン: 1.1 / 2026-10-18  
ステータス: 製品方針確定・実装未着手

## 推奨 GitHub リポジトリ名

**`enterprise-ai-solution-factory`**  
説明: `Reusable AI solution factory for enterprise POCs, capability orchestration, evaluation, and delivery evidence.`

## はじめに

1. `docs/01_PRD.md`、`docs/02_ARCHITECTURE.md`、`docs/03_ACCEPTANCE_AND_EXPERIMENT.md`、`docs/04_SECURITY_AND_IP.md` を確認する。
2. `docs/00_PROJECT_GUIDE_JA.md` にある日本語の概要と運用方針を確認する。
3. Claude Code に `prompts/00_ORCHESTRATOR_CC.md` を渡す。**最初は Phase 0 の設計・契約確定のみ。承認前に実装しない。**
4. G0 でインターフェース契約を確定した後、Codex に `prompts/01_CODEX_PARALLEL.md` を渡す。
5. `tasks/PHASE_PLAN.md` と `tasks/TASK_BOARD.csv` に沿って、フェーズごとに実施する。
6. 各ゲートで `prompts/02_REVIEW_GATE.md` により独立レビューを行う。
7. 比較実験は `prompts/03_BASELINE_EXPERIMENT.md` に従い、Factory 固有の資産がベースラインに混入しないようにする。

## 必須要件

- 二つのハードコードされたデモや Claude Code の単純なラッパーにはしない。
- 日本企業向けの二つの業務 POC：請求書処理と契約書レビュー。データは合成データまたは使用許可済みデータに限定する。
- バージョン管理された Capability Catalog、構成、実ワークフロー実行、トレース、評価、再利用実績、人手による確認を実装する。
- 同じバージョンの能力が複数プロジェクトで実行されたことを証跡で確認する。
- **UI・業務文言・進捗報告は日本語。技術識別子・API・既存の英語技術文書は英語のままでよい。中国語の記載は使用しない。**
- 目標期間は1〜2か月。追加現金支出の初期上限は10,000円。超過前に承認を得る。
- 比較対象も Claude Code / Codex を利用する。人手工数、API コスト、デバッグ、再作業をすべて計測する。
- 会社のコード、データ、端末、アカウント、勤務時間等は許可なく使用しない。SBI/MCT の非公開情報や未確認 API を前提にしない。
- 各フェーズの実測証跡と人間による承認が必須。未実行のテストを成功と報告しない。

## 資料構成

| パス | 内容 |
|---|---|
| `docs/00_PROJECT_GUIDE_JA.md` | 日本語のプロジェクト概要・作業指針 |
| `docs/01_PRD.md` | 製品要件（既存の英語文書） |
| `docs/02_ARCHITECTURE.md` | アーキテクチャ（既存の英語文書） |
| `docs/03_ACCEPTANCE_AND_EXPERIMENT.md` | 受入基準・比較実験（既存の英語文書） |
| `docs/04_SECURITY_AND_IP.md` | セキュリティ・権利関係 |
| `docs/05_UI_AND_DEMO.md` | 日本語 UI・デモ構成 |
| `docs/06_DECISIONS_AND_RISKS.md` | 決定事項・リスク |
| `docs/07_DATA_AND_EVAL.md` | 合成データ・評価 |
| `docs/08_API_AND_EVENTS.md` | API・イベント設計 |
| `schemas/` | Capability・Workflow の JSON Schema |
| `examples/` | 構成例（実装ではない） |
| `tasks/` | フェーズ計画・タスク管理 CSV |
| `prompts/` | Claude Code / Codex 用の指示文（英語） |

## 重要な注意事項

本資料は**設計・実行用の仕様書**であり、アプリケーション本体や検証済みの成果物ではない。性能改善率、外部基盤との接続、テスト合格などの実績を示すものではない。未確定の技術選定と数値基準は Phase 0 で承認を得る。
