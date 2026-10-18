# 脆弱性診断報告書（自己診断）— 草稿

> **状態：途中（ゲート判定に使えない）。** 診断の途中で Docker の常駐プロセスが応答しなくなり、コンテナの再診断（trivy）・設定の診断（trivy config）・動的診断（ZAP）・全テストの再実行が終わっていない。§8 を参照。

| 項目 | 内容 |
|---|---|
| 対象 | EASF `2f22521`（main）＋未コミットの変更（backend/Dockerfile・.dockerignore・docker-compose.yml の api サービス・VA-001 の修正） |
| 環境 | ローカル Docker Compose（`--profile app`）、`EASF_ENV=assessment`（compose で固定）、API は 127.0.0.1:8001。Windows 11、Docker Desktop 28.5.1 |
| 期間 | 2026-10-18 18:55 〜（中断）（JST） |
| 実施者 | Claude Code（自己診断。Codex による独立診断は未実施） |
| 基準 | IPA「安全なウェブサイトの作り方」、ウェブ健康診断仕様、OWASP ASVS 4.0.3 L2、OWASP Top 10 for LLM 2025 |
| 評価方法 | CVSS v3.1 基本値 → 高・中・低・情報 |
| 対象外 | ファイルアップロード・実行・確認タスク・LLM / MCP 接続（Phase 1 では未実装。Phase 2 以降で診断）、メール機能（機能なし）、TLS（ローカル環境） |

## 1. 総評

終わった検査（SAST・SCA・秘密情報・コンテナ初回）では、高・中の指摘は 0 件。初回のイメージ（Debian slim）にあった OS パッケージの高 44 件は、Alpine への変更で 0 件になった。残る中 6 件（zlib・pip）は Dockerfile で対策したが、再ビルドと再診断はまだ。手動診断で低 1 件（VA-001：本番設定で Secure でない Cookie を許してしまう）を見つけ、修正と再発防止のテストを追加した。**DAST と再診断が終わるまで G1a の判定には使わない。**

## 2. 件数

| 重大度 | 件数 | 対応済み | 受容 | 未対応 |
|---|---|---|---|---|
| 高 | 0 | — | — | — |
| 中 | 6（イメージの依存） | 修正済み・再診断待ち | 0 | 0 |
| 低 | 1（VA-001） | 1 | 0 | 0 |
| 情報 | 3 | — | — | — |

## 3. 実施した検査

| 段 | 道具（版） | 結果ファイル | 結果 |
|---|---|---|---|
| SAST | ruff `--select S`（app） | sast/ruff-s.json | 0 件 |
| SAST | bandit 1.9.4（`-r app`） | sast/bandit.json | 0 件 |
| SAST | semgrep 1.180.0（p/python・p/owasp-top-ten・p/react・p/typescript・p/secrets、対象 backend/app・frontend/src・scripts） | sast/semgrep.json | 0 件、エラー 0 |
| SAST | ESLint（localStorage・dangerouslySetInnerHTML・eval の禁止規則） | CI | 0 件 |
| SCA | pip-audit 2.10.1 | sca/pip-audit.json | 既知の脆弱性なし |
| SCA | npm audit | sca/npm-audit.json | 0 件（全重大度） |
| SCA | osv-scanner | — | 未実施（pip-audit・npm audit で代替。次回入れる） |
| ライセンス | importlib.metadata・package-lock.json | sca/licenses-*.json | 画面の本番依存 37 件はすべて MIT・ISC・Apache-2.0・BSD。Python は psycopg（LGPL-3.0）のみ（情報 I-03） |
| 秘密情報 | gitleaks 8.30.1（履歴） | secrets/gitleaks-history.json | 2 件、どちらも誤検知（テスト専用の固定ダミー鍵）。`.gitleaksignore` に指紋と理由を記載し、再実行で 0 件 |
| 秘密情報 | gitleaks 8.30.1（作業ツリー） | secrets/gitleaks-worktree.json | 208 件、すべて追跡対象外のファイル（`.env`〔.gitignore 済み・履歴に一度も入っていない〕、`.venv`・`node_modules` 内のライブラリのデータ）。追跡されているファイルでは上の誤検知 2 件のみ |
| コンテナ | trivy 0.76.0 image（Debian slim 版） | （上書き済み） | 高 44・中 63・低 62。修正版のない OS パッケージが中心 → Alpine に変更 |
| コンテナ | trivy 0.76.0 image（Alpine 3.24.2 版） | container/trivy-image.json | 高・重大 0、中 6（zlib 1.3.2-r0 → 1.3.2-r1、pip 25.0.1 の 5 件）、低 1。秘密情報 0 |
| コンテナ | trivy image（対策後の Alpine 版） | — | **未実施**（Docker が応答しないため） |
| コンテナ | trivy config | — | **未実施**（リポジトリ全体を対象にして終わらず中断。次回は Dockerfile と compose だけを対象にする） |
| コンテナ | 手動確認 | — | 非 root（uid 10001）、読み取り専用のファイルシステム、`no-new-privileges`、`cap_drop: ALL`、ポートは 127.0.0.1 のみ |
| DAST | OWASP ZAP（API スキャン） | — | **未実施**（開始後、Docker が応答しなくなり結果なし） |
| 手動 | §7 | — | 自動テストと curl で確認した項目のみ。残りは未実施 |

## 4. 指摘一覧

| ID | 重大度 | CVSS | 項目 | 場所 | 状態 |
|---|---|---|---|---|---|
| VA-001 | 低 | 3.1（AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N） | 本番設定で Secure でないセッション Cookie を許す | backend/app/core/config.py | 修正済み（再診断 OK） |
| VA-002 | 中 | 依存の公表値 | イメージの zlib・pip の既知の脆弱性 | backend/Dockerfile | 修正済み・再診断待ち |
| I-01 | 情報 | — | ローカル環境のため HTTP（HSTS なし、Cookie に Secure なし） | 環境 | 仕様（ADR-006） |
| I-02 | 情報 | — | 診断環境の Cookie 名が `__Host-` でない（I-01 による） | 環境 | 仕様 |
| I-03 | 情報 | — | psycopg は LGPL-3.0（動的リンクで利用、改変なし） | backend 依存 | 一覧に残す |

## 5. 指摘の詳細

### VA-001 本番設定で Secure でないセッション Cookie を許す（低）

- 場所：`backend/app/core/config.py`
- 概要：`EASF_COOKIE_SECURE` の既定値は `false`。`EASF_ENV=prod` のときも検査がなく、設定漏れのまま起動すると Cookie が `Secure` なし・`__Host-` なしで発行される。
- 再現手順：`EASF_ENV=prod` で `EASF_COOKIE_SECURE` を設定せずに起動し、ログイン応答の `Set-Cookie` を見る。
- 影響：HTTP で通信が起きた場合にセッション ID が盗聴されうる（攻撃者が通信路上にいることが前提）。
- 原因：安全でない既定値と、本番での必須チェックの欠落。
- 対策：`EASF_ENV=prod` で `cookie_secure` が偽なら設定の読み込みで失敗させ、起動させない（根本的解決）。
- 再発防止のテスト：`backend/tests/security/test_cookie_settings.py`（2 件、成功）
- 再診断：2026-10-18、Docker 再起動後に pytest 全 67 件成功

### VA-002 イメージの依存の既知の脆弱性（中）

- 場所：`backend/Dockerfile`
- 概要：Alpine 版のイメージに zlib 1.3.2-r0（CVE-2026-85091）と pip 25.0.1（CVE-2025-8869 ほか 4 件）が含まれていた。どちらも修正版がある。pip は実行時に使わない。
- 対策：実行用のイメージで `apk upgrade --no-cache` を行い、pip を削除する。
- 再診断：未実施（再ビルドと trivy image を次回に行う）

## 6. 受容した指摘

なし。

## 7. 手動診断の結果

Phase 1 で実装済みの機能だけを対象にする。「自動テスト」は `backend/tests/` の該当テストが成功していることを根拠にする（最後に全件成功したのは P1-04 の 65 件）。

| ID | 結果 | 根拠 |
|---|---|---|
| A-01 | 問題なし | test_list_sort_allowlist_and_like_escape（並び替えの許可リスト、LIKE のエスケープ） |
| A-02 | 一部確認 | test_validation_error_does_not_echo_input。画面は dangerouslySetInnerHTML を ESLint で禁止。画面での入力確認は未実施 |
| A-03〜A-06 | 対象外 | アップロード・ダウンロード・エクスポートは未実装 |
| A-07 | 問題なし | test_mass_assignment_fields_are_rejected |
| A-08 | 問題なし | test_invalid_contracts_are_rejected（外部 `$ref` を拒否） |
| A-09 | 対象外 | XML を扱わない |
| A-10 | 一部確認 | 契約スキーマの上限、test_body_over_limit_*。絵文字・結合文字は未実施 |
| B-01 | 問題なし | test_login_failure_is_identical_for_unknown_user_and_wrong_password（応答時間は未計測） |
| B-02 | 問題なし | test_lockout_after_repeated_failures |
| B-03 | 問題なし | test_login_sets_httponly_cookie_and_rotates_session |
| B-04 | 問題なし | test_logout_invalidates_server_side_session |
| B-05 | 一部確認 | test_idle_session_expires。絶対期限は未確認 |
| B-06 | 指摘（VA-001）・情報（I-01） | HttpOnly・SameSite=Lax・Path=/ はテストで確認 |
| B-07 | 未実施 | — |
| B-08 | 問題なし | CSRF トークンはメモリのみ、ESLint で localStorage を禁止 |
| B-09 | 問題なし | test_create_and_deactivate_user（argon2id）、短いパスワードの拒否 |
| B-10 | 問題なし | test_authorization_matrix（実装済みの全 20 操作を未ログインで 401） |
| C-01 | 問題なし | test_project_of_another_user_is_not_found、認可の全件表（非メンバーは 404） |
| C-02 | 問題なし | 認可の全件表（ロールのないメンバーは 403） |
| C-03 | 対象外 | 確認タスクは未実装 |
| C-04 | 一部確認 | test_database_rejects_mutation_of_registered_versions、test_changed_content_same_version_is_conflict、test_requirement_revision_approval_rules |
| C-05 | 問題なし | 認可は API 側で全件表により確認（画面の表示に依存しない） |
| C-06 | 一部確認 | test_list_filters_and_get。他案件の混入は一覧の件数で確認 |
| D-01 | 問題なし | test_state_change_requires_csrf_token_and_origin、test_login_requires_same_origin |
| D-02 | 問題なし | 契約で状態を変える操作はすべて POST・PUT・DELETE |
| D-03 | 問題なし | CSP `frame-ancestors 'none'`、`X-Frame-Options: DENY`（test_health_ok_with_security_headers） |
| D-04 | 問題なし | API にリダイレクト先を受けるパラメータなし。画面のログイン後の戻り先は内部パスのみ |
| D-05 | 問題なし | CORS ミドルウェアを使わない（同一オリジン） |
| E-01〜E-04 | 対象外 | アップロードは未実装 |
| F-01 | 問題なし | test_internal_error_hides_details_and_api_is_no_store、test_unknown_path_returns_error_shape_with_headers |
| F-02 | 問題なし | test_no_server_or_framework_header、コンテナで `Server` ヘッダなしを curl で確認 |
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
- **未実施のもの**：対策後のイメージの trivy image、trivy config、ZAP の API スキャンと認証付きベースライン、osv-scanner、§7 の未実施項目。理由：診断の途中で Docker Desktop の常駐プロセスが応答しなくなった（`docker info` が 150 秒で時間切れ）。Docker Desktop の再起動が必要。
- 全テスト（pytest 67 件）は Docker 再起動後に再実行し成功。
