# 脆弱性診断報告書（自己診断・G2 前）

| 項目 | 内容 |
|---|---|
| 対象 | EASF `cc/P3-03-eval-g2`（main `1e4709e` ＋ 本ブランチの修正）。G1b からの追加：文書の API 3 操作（アップロード・一覧・ダウンロード）、出力の API（exportRunResult）、業務の Capability（解析・規則ベースの抽出・LLM 抽出〔mock〕・ルール・根拠〔ローカル MCP〕・出力）、文書と出力の画面 |
| 環境 | ローカル Docker Compose（`--profile app`）、`EASF_ENV=assessment`、API は 127.0.0.1:8001（読み取り専用のコンテナ、文書はボリューム `easf_documents`）。Windows 11、Docker Desktop。DB は 127.0.0.1:55433（55432 番はほかのプロジェクトが使用中のため変更） |
| 期間 | 2026-10-19（JST） |
| 実施者 | Claude Code（自己診断。独立診断は未実施、D-024） |
| 基準 | IPA「安全なウェブサイトの作り方」、ウェブ健康診断仕様、OWASP ASVS 4.0.3 L2、OWASP Top 10 for LLM 2025 |
| 評価方法 | CVSS v3.1 基本値 → 高・中・低・情報 |
| 対象外 | 実 LLM の接続（D-004）、外部の MCP / REST（ADR-005：ローカルの MCP サーバだけ）、評価・再利用の API（未実装）、メール機能（なし）、TLS（ローカル環境）、画面の DAST、ワーカーのコンテナ（ワーカーはコンテナにしていない） |

## 1. 総評

新しい指摘は **中 1 件（VA-G2-001）**。読み取り専用のコンテナで、1 MB を超えるアップロードが 500 になる（multipart の一時ファイルを書く場所がない）。`/tmp` に大きさを制限した tmpfs を付けて直し、再診断で解消を確認した。アップロードの必須項目 E-01〜E-04 はすべて問題なし（形式の偽装は 415、上限ちょうどは 201・＋1 バイトは 413、31 ページは 422、画素数の爆弾・深い入れ子・圧縮爆弾は 422 で API は落ちない、ファイルは配信されずダウンロードは attachment・nosniff・no-store）。SAST・SCA・コンテナ・秘密情報は 0 件（gitleaks の既知の誤検知は設定で除外、I-07）。**ゲート条件（高・中の未対応 0 件、SCA の高・重大 0 件、秘密情報 0 件）を満たす。**

## 2. 件数

| 重大度 | 新規 | 対応済み | 受容 | 未対応 |
|---|---|---|---|---|
| 高 | 0 | — | — | — |
| 中 | 1 | 1 | 0 | 0 |
| 低 | 0 | — | — | — |
| 情報 | 3 | — | — | — |

## 3. 実施した検査

| 段 | 道具（版） | 結果ファイル | 結果 |
|---|---|---|---|
| SAST | ruff `--select S`（app） | sast/ruff-s.json | 0 件 |
| SAST | bandit 1.9.4 | sast/bandit.json | 0 件（4,019 行）。1 回目に `"pass"` を辞書のキーにした行が B105（誤検知）→ 書き方を変えて 0 件 |
| SAST | semgrep 1.180.0（p/python・p/owasp-top-ten・p/react・p/typescript・p/secrets） | sast/semgrep.json | 0 件、エラー 0（96 ファイル）。結果の書き出し後にプロセスが終わらず、50 分の時間切れで止めた（1 回目は 25 分で時間切れ、結果なし）。端末の負荷が高かった（CPU 90% 前後、ほかのプロジェクトの処理） |
| SAST | ESLint（localStorage・dangerouslySetInnerHTML・eval の禁止） | CI | 0 件 |
| SCA | pip-audit 2.10.1 | sca/pip-audit.json | 既知の脆弱性なし（追加した mcp 2.3.0・python-multipart 0.0.32・Pillow 13.0.0 を含む） |
| SCA | npm audit `--omit=dev` | sca/npm-audit.json | 0 件 |
| 秘密情報 | gitleaks 8.30.1（履歴 37 コミット） | secrets/gitleaks-history.json | 0 件（I-07：過去の診断報告の誤検知 32 件は `.gitleaks.toml` のパスの除外で解消） |
| 秘密情報 | gitleaks 8.30.1（作業ツリーのソース 7 か所） | secrets/worktree-*.json | 0 件（試験用のダミー鍵の行番号の変更を `.gitleaksignore` に反映） |
| コンテナ | trivy 0.76.0 image（Alpine 3.24.2） | container/trivy-image.json | 0 件（全重大度・秘密情報なし） |
| コンテナ | trivy 0.76.0 config（Dockerfile） | container/trivy-config.json | 0 件（27 項目合格） |
| DAST | OWASP ZAP 2.16.1 API スキャン（未ログイン、契約 1.0.2） | dast/zap-api.json | 失敗 0・合格 114。警告は「ZAP is Out of Date」のみ（I-04） |
| DAST | OWASP ZAP 2.16.1 API スキャン（認証付き、Cookie・CSRF・Origin を付与、ログアウトを除く） | dast/zap-api-auth.json | 失敗 0・合格 114。警告は「ZAP is Out of Date」のみ。API のログで認証付きの要求の成功（200・201）を確認、サーバの 500 は 0 |
| 手動 | Python のスクリプト（§7、E-01〜E-04 ほか 25 項目） | — | 初回：500 が 3 件（VA-G2-001）→ 修正後すべて期待どおり |
| 全テスト | pytest・vitest・Playwright | CI・`reports/gate_G2.md` | 成功 |

## 4. 指摘一覧

| ID | 重大度 | CVSS | 項目 | 場所 | 状態 |
|---|---|---|---|---|---|
| VA-G2-001 | 中 | 4.3（AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:N/A:L） | 読み取り専用のコンテナで、1 MB を超えるアップロードが 500（multipart の解析が一時ファイルを作れない）。正当な文書を登録できない（可用性） | docker-compose.yml（api） | 対応済み：`tmpfs: /tmp:size=64m,mode=1777`。再発防止テスト `backend/tests/security/test_container_config.py`。再診断で上限ちょうど 201・＋1 バイト 413・偽装 415 |
| I-01〜I-06 | 情報 | — | 前回のとおり | — | 変わらず |
| I-07 | 情報 | — | 診断報告のファイル（ZAP の URL `http://api:8000/…`、trivy の基底イメージの公開 GPG 鍵の ID）が gitleaks の汎用規則に当たる。指紋による除外はコミットの書き換えで無効になったため、`reports/security/*/{dast,container}/*.json` だけをパスで除外（`.gitleaks.toml`） | .gitleaks.toml | 運用 |
| I-08 | 情報 | — | 画像（スキャン）は OCR 未対応。抽出は missing になり人の確認へ（D-030） | — | 制約として報告 |
| I-09 | 情報 | — | 子プロセスのメモリ上限（1 GiB）は POSIX だけ。Windows の開発環境では時間の上限だけ（D-030） | app/adapters/local.py | 制約として報告 |

## 5. 新しい機能の診断の要点

| 対象 | 確かめたこと | 根拠 |
|---|---|---|
| アップロード（E-01） | 拡張子・宣言の型・先頭のバイトの 3 つが一致しないものは 415（.pdf の HTML・SVG・EXE、型の偽装、拡張子 .html・二重拡張子） | test_spoofed_or_unsupported_types_are_415、§7 |
| アップロード（E-02） | 10 MB ちょうどは成功、＋1 バイトは 413、要求全体が大きすぎるとミドルウェアが 413、30 ページは成功・31 ページは 422 | test_size_limits_are_413、§7 |
| アップロード（E-03） | 30000×30000 の PNG ヘッダ・深い入れ子・圧縮爆弾・暗号化・JavaScript・添付・壊れたファイルは 422。解析は子プロセス（20 秒・POSIX では 1 GiB）で、API は落ちない | test_unsafe_or_unreadable_content_is_422、§7 |
| アップロード（E-04） | 保存名はサーバの UUID（利用者のファイル名をパスに使わない）、保存先は配信しない、ダウンロードは認可付き・attachment（RFC 5987）・nosniff・no-store、改行を含むファイル名でヘッダ・インジェクションにならない、読むときに SHA-256 を照合 | test_upload_list_and_download_round_trip、test_file_names_are_display_strings_only、§7 |
| 認可（C-01〜C-03） | 他案件の文書の一覧・ダウンロード・アップロード・実行の入力は 404／422（存在を区別しない）、出力はロールで 403、未ログイン 401。契約の全操作の認可の全件表に文書・出力の 4 操作を追加 | test_other_projects_documents_are_invisible、test_run_inputs_accept_only_documents_of_the_same_project、test_authorization_matrix |
| CSV インジェクション | 先頭が = + - @ タブ CR のセルに ' を付ける、UTF-8 BOM | test_csv_cells_that_excel_would_evaluate_get_a_quote、test_export_csv_and_json_of_a_reviewed_run |
| 出力の改ざん | 保存したノードの出力から再生成した内容が export_id と一致しなければ 409 | test_tampered_node_output_is_not_exported |
| MCP（ADR-005） | 固定のコマンドで自作のローカルサーバだけを起動、許可リストのツール名だけ、広告されないツールは呼ばない、入力はスキーマで検証、例外は型名だけ。登録時にツールのスキーマと契約を照合 | test_mcp_adapter_calls_the_local_server_over_stdio、test_catalog_rejects_a_contract_that_differs_from_the_advertised_tool |
| 根拠の捏造（LLM09・T18） | 印字された範囲だけを verified で返し、数の途中では一致させない。見つからない値は根拠なし | test_values_not_in_the_text_get_no_evidence、dev 評価の根拠の位置 1.0 |
| プロンプトインジェクション（LLM01・G-01） | 抽出は LLM を使わず、文書の文はデータとして読むだけ。dev の「不審な指示」の層の PDF は誤りなし | test_extractor_ignores_instructions_in_the_document、`reports/eval/2026-10-19-dev/report.md` |
| ルール（H-01） | 値が無い・比べられない・未知の演算子は pass にしない、入れ子 8 段 | test_rule_results、test_operators、test_nesting_deeper_than_the_limit_is_uncertain |

## 6. 受容した指摘

なし。

## 7. 手動診断の結果（今回の差分）

`assess_admin`（診断用に CLI で作った管理者。パスワードはリポジトリに置かない）でログインし、診断用の案件にアップロードした。

| ID | 内容 | 初回 | 修正後 |
|---|---|---|---|
| E-01 | .pdf の HTML／.png の SVG／.pdf の EXE／PDF を text/html と宣言／PNG を .jpg で／.html | 415・415・415・415・**500**・415 | すべて 415 |
| E-02 | 10 MB ちょうど／10 MB＋1 バイト／30 ページ／31 ページ | **500**・**500**・201・422 | 201・413・201・422 |
| E-03 | 30000×30000 の PNG ヘッダ／深い入れ子の PDF／圧縮爆弾の PDF | 422・422・422 | 422・422・422（健康確認 200） |
| A-07 | 余分な項目（project_id）／data_origin=real | 422・422 | 同じ |
| D-01 | CSRF トークンなしのアップロード | 403 | 同じ |
| E-04 | ダウンロード：attachment・RFC 5987・nosniff・no-store・application/pdf・同じバイト列、改行を含む名前でヘッダが増えない | 問題なし | 同じ |
| E-04 | `/data/documents/`・`/var/documents/`・`/documents/<id>`・`/api/v1/documents/<id>`、ID に `../` | すべて 404 | 同じ |
| C-01 | 未ログインのダウンロード | 401 | 同じ |

## 8. 制約・注意

- 自己診断であり、第三者診断・独立診断の代わりではない（D-024）。
- ZAP は API だけ。画面の DAST は未実施。ZAP は契約の例の ID で叩くため、状態を持つ流れ（実行・確認・出力）は自動テストで確認した。
- ワーカー（実行の処理）はコンテナにしていない。ワーカーでの子プロセス・MCP サーバの起動は Windows と Linux（CI・Docker の結合テスト）で確認した。
