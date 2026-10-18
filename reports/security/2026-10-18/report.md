# 脆弱性診断報告書（自己診断）

| 項目 | 内容 |
|---|---|
| 対象 | EASF `815a5b0`（main）＋本報告と同じコミットの修正（VA-003〜VA-005、HEALTHCHECK） |
| 環境 | ローカル Docker Compose（`--profile app`）、`EASF_ENV=assessment`（compose で固定）、API は 127.0.0.1:8001。Windows 11、Docker Desktop 28.5.1 |
| 期間 | 2026-10-18 18:55 〜 21:45（JST）。途中、Docker Desktop の再起動で約 1 時間中断 |
| 実施者 | Claude Code（自己診断。Codex による独立診断は未実施） |
| 基準 | IPA「安全なウェブサイトの作り方」、ウェブ健康診断仕様、OWASP ASVS 4.0.3 L2、OWASP Top 10 for LLM 2025 |
| 評価方法 | CVSS v3.1 基本値 → 高・中・低・情報 |
| 対象外 | ファイルアップロード・実行・確認タスク・LLM / MCP 接続（Phase 1 では未実装。Phase 2 以降で診断）、メール機能（機能なし）、TLS（ローカル環境）、画面（frontend）の DAST（§8） |

## 1. 総評

高 0 件。中 1 件（VA-002：コンテナの依存）と低 4 件（VA-001・VA-003〜VA-005）を検出し、すべて修正・再診断済み。ZAP の認証付きスキャンで、NUL 文字を含む入力が 500 になる不具合（VA-004）と、末尾スラッシュのリダイレクトが Host ヘッダを `Location` に使う不具合（VA-005）を見つけた。どちらも再発防止のテストを追加した。最終のイメージ・API で、trivy 0 件、ZAP の失敗 0 件、サーバの 500 は 0 件。**ゲート条件（高・中 0 件、低は対応済み、SCA 高・重大 0 件、秘密情報 0 件）を満たす。** ただし自己診断であり、§8 の制約がある。

## 2. 件数

| 重大度 | 件数 | 対応済み | 受容 | 未対応 |
|---|---|---|---|---|
| 高 | 0 | 0 | 0 | 0 |
| 中 | 1 | 1 | 0 | 0 |
| 低 | 4 | 4 | 0 | 0 |
| 情報 | 5 | — | — | — |

## 3. 実施した検査

| 段 | 道具（版） | 結果ファイル | 結果 |
|---|---|---|---|
| SAST | ruff `--select S`（app） | sast/ruff-s.json | 0 件 |
| SAST | bandit 1.9.4（`-r app`） | sast/bandit.json | 0 件 |
| SAST | semgrep 1.180.0（p/python・p/owasp-top-ten・p/react・p/typescript・p/secrets、対象 backend/app・frontend/src・scripts） | sast/semgrep.json | 0 件、エラー 0 |
| SAST | ESLint（localStorage・dangerouslySetInnerHTML・eval の禁止規則） | CI | 0 件 |
| SCA | pip-audit 2.10.1 | sca/pip-audit.json | 既知の脆弱性なし |
| SCA | npm audit | sca/npm-audit.json | 0 件（全重大度） |
| SCA | osv-scanner | — | 未実施（pip-audit・npm audit・trivy で代替。次回の診断で追加） |
| ライセンス | importlib.metadata・package-lock.json | sca/licenses-*.json | 画面の本番依存 37 件はすべて MIT・ISC・Apache-2.0・BSD。Python は psycopg（LGPL-3.0）のみ（I-03） |
| 秘密情報 | gitleaks 8.30.1（履歴） | secrets/gitleaks-history.json | 誤検知 2 件（テスト専用の固定ダミー鍵）を `.gitleaksignore` に指紋と理由を書いて除外。再実行で 0 件 |
| 秘密情報 | gitleaks 8.30.1（作業ツリー） | secrets/gitleaks-worktree.json | 208 件、すべて追跡対象外（`.env`〔.gitignore 済み・履歴に一度も入っていない〕、`.venv`・`node_modules` 内のライブラリのデータ）。追跡ファイルでは上の誤検知 2 件のみ |
| コンテナ | trivy 0.76.0 image（Debian slim 版） | （上書き済み） | 高 44・中 63・低 62（修正版のない OS パッケージが中心）→ Alpine に変更 |
| コンテナ | trivy 0.76.0 image（Alpine 版・対策前） | （上書き済み） | 高・重大 0、中 6（VA-002）、低 1 |
| コンテナ | trivy 0.76.0 image（最終） | container/trivy-image.json | **0 件**（全重大度・秘密情報なし） |
| コンテナ | trivy 0.76.0 config（Dockerfile） | container/trivy-config.json | 初回 低 1（DS-0026 HEALTHCHECK なし）→ 追加して 0 件（27 項目合格）。compose ファイルは trivy の対象外のため手動で確認 |
| コンテナ | 手動確認 | — | 非 root（uid 10001）、読み取り専用のファイルシステム、`no-new-privileges`、`cap_drop: ALL`、ポートは 127.0.0.1 のみ、HEALTHCHECK で healthy |
| DAST | OWASP ZAP 2.16.1 API スキャン（未ログイン、契約の全 54 URL） | dast/zap-api.json | 初回 低 1（VA-003）→ 最終 失敗 0・合格 114。警告は「ZAP is Out of Date」のみ（I-04） |
| DAST | OWASP ZAP 2.16.1 API スキャン（ログイン済み〔admin〕、Cookie・CSRF トークン・Origin を付与、ログアウトを除く） | dast/zap-api-auth.json | 初回 低 1（VA-004、サーバの 500）→ 再診断 失敗 0・合格 114、サーバのログに 500 なし。ここで VA-005 を確認 |
| 手動 | §7 | — | 自動テスト・curl による確認 |
| 全テスト | pytest | — | 71 件すべて成功（VA-001・VA-003〜VA-005 の再発防止テストを含む） |

ZAP の版：最新の `stable` イメージがこの端末で壊れていた（ライブラリ 431 個が 0 バイト。Docker 停止時の取得中断が原因と推定）ため、壊れていない `2.16.1` に固定して使った（D-023）。

## 4. 指摘一覧

| ID | 重大度 | CVSS | 項目 | 場所 | 状態 |
|---|---|---|---|---|---|
| VA-001 | 低 | 3.1（AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N） | 本番設定で Secure でないセッション Cookie を許す | backend/app/core/config.py | 対応済み（再診断 OK） |
| VA-002 | 中 | 依存の公表値（最大 中） | イメージの zlib・pip の既知の脆弱性 | backend/Dockerfile | 対応済み（trivy 再診断 0 件） |
| VA-003 | 低 | 3.1（AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N） | `Cross-Origin-Resource-Policy` ヘッダなし（ZAP 90004） | backend/app/core/middleware.py | 対応済み（ZAP 再診断 OK） |
| VA-004 | 低 | 3.5（AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:N/A:L） | NUL 文字を含む入力で 500（DB エラー） | backend/app/core/middleware.py | 対応済み（ZAP 再診断 OK） |
| VA-005 | 低 | 3.1（AV:N/AC:H/PR:N/UI:R/S:U/C:N/I:L/A:N） | 末尾スラッシュのリダイレクトが Host ヘッダを `Location` に使う（Host ヘッダ・インジェクション） | backend/app/main.py | 対応済み（curl・ZAP 再診断 OK） |
| I-01 | 情報 | — | ローカル環境のため HTTP（HSTS なし、Cookie に Secure なし） | 環境 | 仕様（ADR-006） |
| I-02 | 情報 | — | 診断環境の Cookie 名が `__Host-` でない（I-01 による。本番は VA-001 の対策で必須） | 環境 | 仕様 |
| I-03 | 情報 | — | psycopg は LGPL-3.0（動的リンクで利用、改変なし） | backend 依存 | 一覧に残す |
| I-04 | 情報 | — | ZAP 10116「ZAP is Out of Date」（道具の版の警告。対象の欠陥ではない） | 診断の道具 | D-023 |
| I-05 | 情報 | — | `/health`・`/ready` はキャッシュ可能（ZAP 10049）。秘密を含まない固定の応答 | API | 仕様 |

## 5. 指摘の詳細

### VA-001 本番設定で Secure でないセッション Cookie を許す（低）

- 場所：`backend/app/core/config.py`
- 概要：`EASF_COOKIE_SECURE` の既定値は `false`。`EASF_ENV=prod` でも検査がなく、設定漏れのまま起動すると Cookie が `Secure` なし・`__Host-` なしで発行される。
- 再現手順：`EASF_ENV=prod` で `EASF_COOKIE_SECURE` を設定せずに起動し、ログイン応答の `Set-Cookie` を見る。
- 影響：HTTP の通信が起きた場合にセッション ID が盗聴されうる（攻撃者が通信路上にいることが前提）。
- 原因：安全でない既定値と、本番での必須チェックの欠落。
- 対策：`EASF_ENV=prod` で `cookie_secure` が偽なら設定の読み込みで失敗させ、起動させない（根本的解決）。
- 再発防止のテスト：`backend/tests/security/test_cookie_settings.py`
- 再診断：2026-10-18、pytest 全件成功

### VA-002 イメージの依存の既知の脆弱性（中）

- 場所：`backend/Dockerfile`
- 概要：Alpine 版のイメージに zlib 1.3.2-r0（CVE-2026-85091）と pip 25.0.1（CVE-2025-8869 ほか 4 件）が含まれていた。どちらも修正版がある。pip は実行時に使わない。
- 対策：実行用のイメージで `apk upgrade --no-cache` を行い、pip を削除する。
- 再診断：2026-10-18、trivy image 0 件

### VA-003 Cross-Origin-Resource-Policy ヘッダなし（低）

- 場所：`backend/app/core/middleware.py`
- 概要：全応答に `Cross-Origin-Resource-Policy` がなく、別オリジンのページから応答を読み込める（Spectre 系のサイド・チャネル対策が不足）。ZAP は 200 の応答（`/health`・`/ready`）でのみ報告したが、全応答で同じ。
- 再現手順：`curl -sI http://127.0.0.1:8001/health` にヘッダがない。
- 対策：全応答に `Cross-Origin-Resource-Policy: same-origin` を付ける。
- 再発防止のテスト：`backend/tests/unit/test_http_baseline.py`（必須ヘッダの一覧に追加）
- 再診断：2026-10-18、ZAP 未ログインのスキャンで検出なし

### VA-004 NUL 文字を含む入力で 500（低）

- 場所：全 API（入口は `backend/app/core/middleware.py`）
- 概要：JSON の文字列に `\u0000` を含めると PostgreSQL が `text fields cannot contain NUL` で失敗し、500 になる。エラー応答に内部情報は出ない（既存のテストで確認済み）。
- 再現手順：ログイン後、`POST /api/v1/projects` に `{"name":"a\u0000b","business_domain":"x"}`（CSRF トークン・Origin 付き）。
- 影響：不正な入力で 500 とエラーログが出る（ログの汚染、監視の誤報）。データの漏えい・改ざんはない。
- 原因：DB が受け付けない文字を入口で拒否していない。
- 対策：最外層の中間処理で、パス・クエリ文字列の `%00`、JSON 本文の NUL（`\u0000`。`\\u0000` は普通の文字列なので除く）を 422 `validation_error` で拒否する。JSON 以外の本文（将来のファイルのアップロード）は対象外。
- 再発防止のテスト：`backend/tests/security/test_nul_bytes.py`（3 件。`\\u0000` の文字列が登録できることも確認）
- 再診断：2026-10-18、ZAP 認証付きスキャンで 500 なし、curl で 422

### VA-005 Host ヘッダ・インジェクション（低）

- 場所：`backend/app/main.py`
- 概要：`/api/v1/projects/` のように末尾にスラッシュを付けると 307 で転送され、`Location` が要求の `Host` ヘッダから作られる。
- 再現手順：`curl -sI -H "Host: evil.example" http://127.0.0.1:8001/api/v1/projects/` → `location: http://evil.example/api/v1/projects`
- 影響：利用者のブラウザから `Host` は変えられないため直接の悪用は難しいが、前段のキャッシュ・プロキシの設定次第でキャッシュ汚染や誘導に使われうる。
- 原因：フレームワークの末尾スラッシュの自動転送（`redirect_slashes`）。
- 対策：自動転送を無効にする（契約のパスに末尾スラッシュはなく、画面も使っていない）。末尾スラッシュ付きは 404。
- 再発防止のテスト：`backend/tests/security/test_host_header.py`
- 再診断：2026-10-18、curl で 404・`Location` なし

## 6. 受容した指摘

なし。

## 7. 手動診断の結果

Phase 1 で実装済みの機能だけを対象にする。「自動テスト」は `backend/tests/` の該当テストが成功していること（最終 71 件成功）を根拠にする。

| ID | 結果 | 根拠 |
|---|---|---|
| A-01 | 問題なし | test_list_sort_allowlist_and_like_escape（並び替えの許可リスト、LIKE のエスケープ）、ZAP の SQL インジェクション検査で検出なし |
| A-02 | 一部確認 | test_validation_error_does_not_echo_input、ZAP の XSS 検査で検出なし。画面は dangerouslySetInnerHTML を ESLint で禁止。画面への入力確認は未実施 |
| A-03〜A-06 | 対象外 | アップロード・ダウンロード・エクスポートは未実装 |
| A-07 | 問題なし | test_mass_assignment_fields_are_rejected |
| A-08 | 問題なし | test_invalid_contracts_are_rejected（外部 `$ref` を拒否） |
| A-09 | 対象外 | XML を扱わない |
| A-10 | 指摘（VA-004）→ 対応済み | NUL 文字。上限は契約スキーマと test_body_over_limit_*。絵文字・結合文字は未実施 |
| B-01 | 問題なし | test_login_failure_is_identical_for_unknown_user_and_wrong_password（応答時間は未計測） |
| B-02 | 問題なし | test_lockout_after_repeated_failures |
| B-03 | 問題なし | test_login_sets_httponly_cookie_and_rotates_session |
| B-04 | 問題なし | test_logout_invalidates_server_side_session |
| B-05 | 一部確認 | test_idle_session_expires。絶対期限は未確認 |
| B-06 | 指摘（VA-001）→ 対応済み、情報（I-01・I-02） | HttpOnly・SameSite=Lax・Path=/ はテストで確認 |
| B-07 | 未実施 | — |
| B-08 | 問題なし | CSRF トークンはメモリのみ、ESLint で localStorage を禁止 |
| B-09 | 問題なし | test_create_and_deactivate_user（argon2id）、短いパスワードの拒否 |
| B-10 | 問題なし | test_authorization_matrix（実装済みの全 20 操作を未ログインで 401） |
| C-01 | 問題なし | test_project_of_another_user_is_not_found、認可の全件表（非メンバーは 404） |
| C-02 | 問題なし | 認可の全件表（ロールのないメンバーは 403） |
| C-03 | 対象外 | 確認タスクは未実装 |
| C-04 | 一部確認 | test_database_rejects_mutation_of_registered_versions、test_changed_content_same_version_is_conflict、test_requirement_revision_approval_rules |
| C-05 | 問題なし | 認可は API 側で全件表により確認（画面の表示に依存しない） |
| C-06 | 一部確認 | test_list_filters_and_get |
| D-01 | 問題なし | test_state_change_requires_csrf_token_and_origin、test_login_requires_same_origin |
| D-02 | 問題なし | 契約で状態を変える操作はすべて POST・PUT・DELETE |
| D-03 | 問題なし | CSP `frame-ancestors 'none'`、`X-Frame-Options: DENY` |
| D-04 | 指摘（VA-005）→ 対応済み | API にリダイレクト先を受けるパラメータなし。画面のログイン後の戻り先は内部パスのみ |
| D-05 | 問題なし | CORS ミドルウェアを使わない（同一オリジン） |
| E-01〜E-04 | 対象外 | アップロードは未実装 |
| F-01 | 問題なし | test_internal_error_hides_details_and_api_is_no_store、test_unknown_path_returns_error_shape_with_headers |
| F-02 | 指摘（VA-003）→ 対応済み | test_no_server_or_framework_header、コンテナで `Server` ヘッダなしを curl で確認 |
| F-03 | 問題なし | コンテナ（assessment）で `/docs`・`/redoc`・`/openapi.json`・`/.env`・`/.git/config`・`/debug` がすべて 404（curl）。画面のビルドにソースマップなし（CI） |
| F-04 | 未実施 | — |
| F-05 | 問題なし | test_trace_method_not_allowed |
| F-06 | 問題なし | test_internal_error_hides_details_and_api_is_no_store |
| F-07 | 未実施 | — |
| F-08 | 対象外 | ローカル環境 |
| G-01〜G-06 | 対象外 | LLM・MCP・実行は未実装 |
| H-01、H-03、H-04 | 対象外 | 実行・確認は未実装 |
| H-02 | 問題なし | test_changed_content_same_version_is_conflict、DB トリガー |

## 8. 制約・注意

- 自己診断であり、第三者診断の代わりではない。Codex による独立診断も未実施。
- ZAP は API（契約の OpenAPI）だけを対象にした。画面（frontend）の DAST、ブラウザでの XSS の確認は未実施（Phase 1 の画面は表示のみで、`dangerouslySetInnerHTML` は ESLint で禁止）。
- ZAP の認証付きスキャンはログアウト（`DELETE /api/v1/session`）を除いた。セッションが切れて残りが未ログインになるのを防ぐため。ログアウトは自動テストで確認済み。
- §7 の「未実施」（A-02 の画面、A-10 の一部、B-05 の絶対期限、B-07、F-04、F-07）は次回の診断で行う。
- 診断に使った利用者（`zap-assessor`）はスキャンの後のテストの実行で DB ごと消えている。パスワードは一時フォルダにのみ置き、リポジトリに入れていない。報告のファイルにセッション ID・CSRF トークン・パスワードが含まれないことを確認した。
- テストと API が同じ開発用 DB を使うため、完全なテストの実行で開発用のデータが消える（既存の運用）。
