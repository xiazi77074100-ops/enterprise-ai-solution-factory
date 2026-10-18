# G0 レビュー（P0-02）

| 項目 | 内容 |
|---|---|
| 対象 | `main` @ 1db1b4e（Phase 0 の成果物すべて） |
| 実施 | Claude Code、2026-10-18 17:16 JST |
| 方法 | `easf_package/prompts/02_REVIEW_GATE.md` の敵対的な観点、`01_CODEX_PARALLEL.md` の Initial action の 4 項目 |
| **制約** | **自己レビュー**（D-011）。成果物の作成者と同じエージェントが行ったため、独立性は低い。見落としの可能性を前提に、G4・最終監査は別セッションで行う（D-012） |

## 0. 総評

- 判定：**BLOCKER 0 件、MAJOR 7 件、MINOR 8 件、質問 3 件**。
- 契約 v1 は検査を通るが、**実行時の意味（確認の却下・案件をまたぐルール・権限）と、UI・運用に必要な API が足りない**。どれも G0 の凍結前に契約を直せば解消できるため、P0-06 で反映してから G0 報告に進む。
- 質問 Q1（holdout を mock の LLM では評価できない）は Phase 3 の前に決める必要がある。G0 では「いつ・どう決めるか」を決める。

## 1. 実行した確認

| コマンド | 終了コード | 結果 |
|---|---|---|
| `python scripts/sync_skills.py --check` | 0 | skill の写しが一致 |
| `scripts/validate_contracts.py`（jsonschema 4.26.0、openapi-spec-validator 0.9.0） | 0 | `OK: schemas=5 capabilities=6 rule_packs=2 workflows=2 openapi=valid` |
| 陰性試験（P0-03 で実施。循環・未登録の版・入力の不足・外部 `$ref`・冪等でないリトライ・汎用エンジン内の業務名） | 1 | 6 種すべて検出 |
| `ls backend frontend` | 2 | 存在しない＝アプリケーションコードなし（G0 前の規則を満たす） |
| `git log` の作成者 | — | 全コミットが個人の名前・アドレス（D-009） |

未実行：Codex による独立レビュー（環境にない。D-011）、外部の資料（ライブラリの版・ライセンス・LLM の料金）の確認（各 ADR で「採用時に確認」としている）。

## 2. 指摘一覧

| ID | 区分 | 観点 | 場所 | 内容 | 修正案 |
|---|---|---|---|---|---|
| RV-G0-001 | MAJOR | 仕様 | `contracts/openapi.yaml` RunStatus、`examples/capabilities/human_review.json` | 確認で **却下（rejected）** されたときの実行の結末が決まっていない。export は却下でも動く配線になっており、「確認を通っていない結果が出力される」余地がある | Run の状態に `rejected` を追加。却下ならそれ以降のノードは `skipped`、出力しない。状態遷移を詳細設計に書く |
| RV-G0-002 | MAJOR | 設計 | `rule_pack.schema.json` の `unique_in_project`、INV-006 | 案件をまたぐ判定には過去の実行の値が要るが、RuleValidator の入力契約にそれがない。暗黙に DB を読むと Capability が純粋でなくなり、再実行・評価の再現性が崩れる | Executor が読み取り専用の `project_context`（同じ案件の確認済みの値の一覧、実行開始時点のスナップショット）を入力として渡す。RuleValidator の入力に任意項目 `project_context` を追加 |
| RV-G0-003 | MAJOR | セキュリティ | `docs/design/` | **権限表（ロール × 操作）が無い**。ADR-006 にロールはあるが、どの API を誰が呼べるかが契約にない。認可のテスト（期待値表）が作れない | `docs/design/basic/permissions.md` を作り、OpenAPI の全 operationId について許可ロールを書く。OpenAPI に `x-easf-roles` を付ける |
| RV-G0-004 | MAJOR | 仕様 | `contracts/openapi.yaml` | FR-09 の再利用の分類（unchanged / config_only …）と追加工数を **記録する API が無い**（参照だけ） | `POST /api/v1/projects/{project_id}/reuse-records` を追加（solution_lead / qa_evaluator） |
| RV-G0-005 | MAJOR | 仕様 | `contracts/openapi.yaml` | 画面に必要な一覧が無い：案件の解決策一覧、要件の版の一覧、評価の一覧 | `GET /projects/{id}/solutions`、`GET /projects/{id}/requirements`、`GET /evaluations?solution_id=` を追加 |
| RV-G0-006 | MAJOR | セキュリティ | `contracts/openapi.yaml`、ADR-006 | 利用者・案件メンバーの管理方法が無い（オブジェクト単位の認可の前提なのに、メンバーを登録する手段がない） | 利用者の作成は管理用の CLI（API にしない＝攻撃面を減らす）。案件メンバーは `GET/PUT /projects/{id}/members`（solution_lead）。ADR-006 に追記 |
| RV-G0-007 | MAJOR | 設計 | ADR-004、`capability.schema.json` | 版の不変性の判定に使う **内容ハッシュの正規化方法** が決まっていない。キーの順序・空白・改行（このリポジトリは autocrlf で CRLF になる）で同じ内容が別ハッシュになり、冪等な再登録が 409 になる | ハッシュは RFC 8785（JSON Canonicalization Scheme）で正規化した JSON の SHA-256 と決める。`.gitattributes` で `eol=lf` を固定 |
| RV-G0-008 | MINOR | 仕様 | `human_review.json` の `route_when: on_flags` | 「フラグがなければ確認を飛ばす」ときの下流（export は `reviewed_fields` 必須）の扱いが未定義 | v1 は `always` だけにする（条件付きの経路は v2 で検討） |
| RV-G0-009 | MINOR | セキュリティ | `rule_pack.schema.json` の `and/or/not` | 入れ子の深さに上限がない（深い式で評価器の再帰が深くなる） | 評価器で深さ 8 まで、登録時に検査。スキーマの説明に明記 |
| RV-G0-010 | MINOR | セキュリティ | `openapi.yaml` の login | ログインは CSRF トークン無しのため、ログイン CSRF（攻撃者のアカウントでログインさせる）の余地 | ログインでも `Origin` の照合を必須にすることを説明に明記 |
| RV-G0-011 | MINOR | 仕様 | `events.schema.json` | `execution_mode` に `mixed` が無い（Run には有る） | `mixed` を追加 |
| RV-G0-012 | MINOR | 仕様 | `capability.schema.json` の `side_effects` | Exporter は内部の保存領域に書くが、それが「副作用」かが曖昧 | 「EASF の外への作用（送信・外部の書き込み・支払い等）」と定義を明記 |
| RV-G0-013 | MINOR | 規約 | `scripts/sync_skills.py` | Windows の Git Bash でエラー文が文字化けする | 出力を UTF-8 に固定（`sys.stderr.reconfigure`） |
| RV-G0-014 | MINOR | データ | `examples/rule_packs/invoice-1.0.0.json` | 参照表の社名「TEST ONLY 例示商事株式会社」は、`fixture-data` の「社名はリアルに、偽物の印は欄外」と食い違う | 見本であることを残しつつ、Phase 3 で生成器の出力から参照表を作ると README に明記（見本の値は変えない） |
| RV-G0-015 | MINOR | 計画 | `PHASE0_PLAN.md` §D-1 の 6 | G0 の受入条件が「Codex の独立レビュー」のまま | 「G0 レビュー（D-011・D-012）」に直す |
| Q1 | 質問 | 評価 | ADR-002・`fixture_plan.md` | **mock の LLM は既知の文書の固定応答しか返せないため、holdout（未知の文書）を評価できない。** 実 API を使わないままだと、抽出の品質の評価と ADR-007 の判定ができない | 選択肢：(a) Phase 3 の前に実 API を 1 社だけ有効化（上限 5,000 円、D-008）、(b) LLM を使わないローカルの抽出（見出しの近くの値を拾う規則ベース）を別の Capability 版として作り、mock の代わりに使う、(c) 両方。**提案：(c)**。(b) は費用ゼロで評価の流れを先に通せ、(a) と同じ契約で比べられる。決定は Phase 3 の着手前 |
| Q2 | 質問 | 実験 | `preregistration.md` §6 | CR-2（請求書）をベースラインと比べるか | 提案：参考値（比較は CR-1 だけ） |
| Q3 | 質問 | 実験 | `preregistration.md` 全体 | 事前登録を Factory 側（CC）が作った | 承認時に人が「A に不利な条件がないか」を確認する。必要なら別セッションの AI に読ませて意見を取る |

## 3. 独立テストの観点（Phase 1 以降のテスト設計の入力）

| 対象 | 観点 |
|---|---|
| 請求書 | 層ごとの期待結果（fixture_plan §2.1）、和暦、表の多い明細、スキャン、重複ラベル、合計の端数 |
| 契約書 | 欠落・あいまい・矛盾（根拠 2 か所）、条番号の体裁 3 種、「法的助言ではない」の表示 |
| Workflow | 循環・未登録の版・型の不一致・入力の不足・予算超過・タイムアウト・冪等でないノードのリトライ禁止・却下（RV-G0-001） |
| アダプタ | mock と real の区別（`execution_mode` と `mixed`）、許可リスト外の MCP ツール、LLM の出力のスキーマ違反・拒否・レート制限 |
| LLM ポート | プロファイルの切り替えで Capability の版が変わらない、無効なプロファイル・`CHANGE_ME`・キーなしで起動エラー、`api_key_env` の接頭辞 |
| 認証・認可 | 権限表（RV-G0-003）からの全件テスト、IDOR、自分の解決策の自己承認の禁止、確認者以外の決定 |
| 人の確認 | 修正前後の保存、二重送信（冪等キー）、決定済みの再決定 409、却下の結末 |
| 根拠の完全性 | 照合できない根拠は `unverified`、OCR 由来の根拠、矛盾した 2 か所の根拠 |
| 再利用 | 2 案件で同じ `capability_version_id`、分類 4 種、模擬の実行を実績に数えない |

## 4. 一般性の主張についての評価

2 業務とも「文書 → 抽出 → ルール → 根拠 → 確認 → 出力」の同じ形で、6 つの Capability をすべて共有する。したがって示せるのは **「文書を確認する業務の中での再利用」** までであり、文書以外の業務（予測・対話・業務システム連携など）への一般化の根拠にはならない。報告では次のように書く：

- 再利用率は高く出るが、それは 2 業務の形が同じだから（業務の選び方による偏り）。
- 本当に効くかは、M1（2 件目の追加工数）と CR-1（要件変更の工数）で判断する。
- 3 件目として形の違う業務（例：問い合わせの分類）を試すまで、汎用性は「仮説」と書く。

## 5. 対応の方針

MAJOR 7 件・MINOR 8 件は P0-06（CC）で反映し、`validate_contracts.py` を再実行してから G0 報告を書く。Q1〜Q3 は G0 報告で人に決めてもらう。
