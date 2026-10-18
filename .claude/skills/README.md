# skill の一覧と出所

正本はこの `.claude/skills/`。`python scripts/sync_skills.py` で Codex 用の `.agents/skills/` へ写す。

| skill | 出所 | ライセンス | 取得日 |
|---|---|---|---|
| `easf-phase-gate` | EASF で作成 | プロジェクトに従う | 2026-10-18 |
| `easf-capability-contract` | EASF で作成 | プロジェクトに従う | 2026-10-18 |
| `easf-eval-integrity` | EASF で作成 | プロジェクトに従う | 2026-10-18 |
| `jp-secure-coding` | EASF で作成 | プロジェクトに従う | 2026-10-18 |
| `jp-vuln-assessment` | EASF で作成 | プロジェクトに従う | 2026-10-18 |
| `jp-dev-standards` | EASF で作成 | プロジェクトに従う | 2026-10-18 |
| `japan-enterprise-frontend` | `D:\aidd\sales-assistant\.ai\skills\japan-enterprise-frontend`（作者の汎用 skill。製品固有の名前・データを含まない形にまとめたもの） | 作者（プロジェクト責任者本人）が EASF での利用を承認（DECISIONS D-003） | 2026-10-18 |
| `design-taste-frontend` | sales-assistant の `taste-skill`（Leonxlnx/taste-skill@ce26fc2） | MIT（フォルダ内 LICENSE） | 2026-10-18（元の取得 2026-09-29） |
| `redesign-existing-projects` | sales-assistant の `redesign-skill`（Leonxlnx/taste-skill@18dfc92） | MIT（フォルダ内 LICENSE） | 2026-10-18（元の取得 2026-10-09） |
| `ponytail` | DietrichGebert/ponytail@e3ba2aa | MIT（フォルダ内 LICENSE） | 2026-10-18（元の取得 2026-09-29） |
| `ponytail-review` | DietrichGebert/ponytail@e3ba2aa | MIT（フォルダ内 LICENSE） | 2026-10-18（元の取得 2026-09-29） |
| `ui-design` | sales-assistant の `ui-design`（81f79e2、2026-10-14）を EASF 向けに書き直し | プロジェクトに従う | 2026-10-18 |
| `spec-sync` | sales-assistant の `demo-spec-sync`（81f79e2）を EASF 向けに書き直し | プロジェクトに従う | 2026-10-18 |
| `fixture-data` | sales-assistant の `demo-mock-data`（81f79e2）を EASF 向けに書き直し | プロジェクトに従う | 2026-10-18 |

- 外部の skill は中身を変えずに取り込み、フォルダ名だけ frontmatter の `name` に合わせた（`taste-skill` → `design-taste-frontend`、`redesign-skill` → `redesign-existing-projects`）。
- 書き直した 3 つは、規約の構成と決まり（部品の振る舞い・フォームの約束・文字の段・整合ルール・同期の手順）を引き継ぎ、sales-assistant 固有のファイルパス・画面・業務用語・ロール色・データは除いた。見た目の作り（部品・面の構成）は D-026 で sales-assistant を手本にすることにし、配色だけ EASF の色に変えている。
- 取り込まなかったもの：`gsap-*`（動きの演出。EASF の画面方針では使わない）。

## 同期の対応表（sales-assistant が更新されたとき）

| sales-assistant | EASF | 取り込み方 |
|---|---|---|
| `.ai/skills/japan-enterprise-frontend` | `japan-enterprise-frontend` | そのまま写す |
| `.claude/skills/taste-skill` | `design-taste-frontend` | そのまま写す |
| `.claude/skills/redesign-skill` | `redesign-existing-projects` | そのまま写す |
| `.claude/skills/ponytail`・`ponytail-review` | 同名 | そのまま写す |
| `.claude/skills/ui-design` | `ui-design` | 差分の決まりだけを EASF の言葉で反映 |
| `.claude/skills/demo-spec-sync` | `spec-sync` | 同上 |
| `.claude/skills/demo-mock-data` | `fixture-data` | 同上 |

最終確認：2026-10-18。そのまま写す 5 つは差分なし（`diff -rq`）。書き直す 3 つは sales-assistant の 81f79e2 時点の内容を反映。
