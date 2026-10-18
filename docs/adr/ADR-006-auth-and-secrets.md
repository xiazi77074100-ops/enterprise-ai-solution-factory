# ADR-006 POC の認証・認可・秘密管理

| 項目 | 内容 |
|---|---|
| 状態 | 承認（D-001・D-006） |
| 日付 | 2026-10-18 |
| 作成 | Claude Code |
| 承認 | プロジェクト責任者 2026-10-18 |

## 選択肢
| 観点 | A サーバ側セッション＋ Cookie | B JWT（localStorage） | C OIDC（Keycloak など） |
|---|---|---|---|
| 診断での指摘 | 少ない（属性と CSRF を正しくすれば） | XSS 時の持ち出し・失効できないことを指摘されやすい | 少ない |
| ログアウト・失効 | 即時 | 難しい | IdP 次第 |
| 手間 | 小 | 小 | 大（別サービス） |

## 決定
A。
- パスワードは argon2id。初期の管理者は初回起動時に環境変数で指定（固定値なし）。
- セッション：DB に保存、Cookie `__Host-easf_session`（Secure・HttpOnly・SameSite=Lax・Path=/）、ログインで振り直し、無操作 30 分・絶対 8 時間。
- CSRF：セッションに紐づくトークンを `X-CSRF-Token` ヘッダで送る＋ `Origin` の照合。
- ログイン：失敗の文言を 1 種類、5 回失敗で 15 分ロック、応答時間を揃える。
- ロール：`admin`・`solution_lead`・`solution_architect`・`qa_evaluator`・`business_reviewer`。案件のメンバーシップ（案件ごとのロール）でオブジェクト単位の認可。
- 自分が作った解決策を自分で承認できない（`solution.approve` は作成者以外）。確認タスクの決定は割り当てられた `business_reviewer` だけ。
- ローカルで HTTPS を使わない間は `__Host-` と `Secure` が使えないため、設定 `EASF_COOKIE_SECURE=false` を開発時だけ許し、診断用の設定（`EASF_ENV=assessment`）ではローカルの自己署名 HTTPS（リバースプロキシ）で `true` にする。
- 秘密：環境変数と `.env`（コミットしない）、`pydantic-settings` の `SecretStr`、`gitleaks` を pre-commit と CI。

- 利用者の作成・無効化・パスワードの初期化は **管理用の CLI**（`python -m app.admin ...`、P1-05 で実装）だけで行い、API を作らない（攻撃面を減らす）。案件のメンバーとロールは `GET/PUT /projects/{id}/members`（solution_lead）。権限の全体は `docs/design/basic/permissions.md`（2026-10-18 追記、RV-G0-003・006）。

## やらないこと
多要素認証、パスワードリセットのメール、外部 IdP 連携（ASVS の自己評価では「対象外（POC）」と書く）。
