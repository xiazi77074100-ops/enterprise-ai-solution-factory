# ADR-009 フロントエンドの部品ライブラリ

| 項目 | 内容 |
|---|---|
| 状態 | **承認（D-010）**。D-001 の時点の推奨（Ant Design）を、D-003 の後に見直したもの |
| 日付 | 2026-10-18 |
| 作成 | Claude Code |
| 承認 | プロジェクト責任者 2026-10-18 |

## 状況
仕様（`easf_package/docs/05`）の候補は React / TypeScript / Vite / Ant Design。その後、画面の規約として sales-assistant 由来の `ui-design` skill を使うことが決まった（D-003）。`ui-design` は Tailwind CSS ＋ヘッドレス部品（Radix）で自作する共通部品（PageHeader・Panel・StatTile・Field・Truncate・Pagination・MultiSelect・SearchSelect・Modal・ConfirmDialog・ActionDialog）を前提に書かれている。

## 選択肢
| 観点 | A Ant Design | B Tailwind CSS ＋ Radix（共通部品を自作） |
|---|---|---|
| ライセンス | MIT | MIT / MIT |
| `ui-design` skill との一致 | 部品の対応を読み替える必要（Form.Item・Table・Select など）。文字の段・密度は上書きが多い | **そのまま適用できる** |
| CSP（診断） | CSS-in-JS が実行時に `<style>` を挿入 → `style-src 'unsafe-inline'` か nonce の仕組みが必要。nonce なしなら「情報」〜「低」の指摘 | 静的な CSS ファイルだけ → `style-src 'self'` の厳しい CSP がそのまま通る |
| 作る量 | 少ない（表・フォーム・日付選択が揃う） | 多い（共通部品を Phase 1 で作る。表は TanStack Table、日付は軽量な部品を選定） |
| 日本語・密度 | 対応済みだが既定の余白が大きめ | 規約どおりに作れる |
| 利用者の経験 | — | sales-assistant と同じ作り方 |

## 推奨
**B**。理由：(1) 採用した `ui-design` の規約をそのまま守れる、(2) 厳しい CSP で第三者診断の指摘を 1 つ減らせる、(3) 作り方を既に知っている。増える作業（共通部品）は Phase 1 の P1-03（Codex）に含め、見積に反映する。

## 決定
B。共通部品は Phase 1 で `frontend/src/components/` に作る。表は TanStack Table（MIT）、選択肢は Radix Popover ＋ cmdk（MIT）を候補とし、Phase 1 の依存追加時に版・ライセンスを確認して追記する。
