# P5-03d：VA-G4-001の修正と本体再診断

2026-10-23、Codex。基点 `fce7ee915eefca8d58c26d85b7c7e9378a5e96ae`、適用指示D-052。プロジェクト内の自己診断であり、第三者診断ではない。今回の修正と試験はCodex自身が実施した自己レビュー。

## 変更と結果

`backend/app/core/middleware.py` の予期しない例外のログだけを、P5-03cの提示済み差分で修正した。例外オブジェクト・本文・原因・SQLパラメータを渡さず、例外型とサーバ発行のtrace_idを固定の書式および構造化フィールドへ記録する。完全なスタックトレースを記録しなくなる代わりに、応答と同じtrace_idで追跡する。

`backend/tests/security/test_error_logging.py` の通常・連鎖・SQLAlchemy例外の3ケースを、本体に対して修正前後で実行した。**修正前は3失敗（exit 1）、修正後は3成功（exit 0）**。[before-pytest.log](before-pytest.log)、[after-pytest.log](after-pytest.log)。SQLAlchemy例外は構成のみで、SQLの実行・DB接続はしていない。TestClientで実ミドルウェアを包み、実在の資格情報・環境ファイル・外部APIを使わない。

確認項目：合成値が標準表示のログとHTTP応答へ出ない、原因メッセージ・SQL文がログに出ない、`exc_info` を添付しない、例外型を維持、500・`internal_error`・セキュリティヘッダを維持、標準表示と構造化フィールドのtrace_idが応答本文・ヘッダと一致。VA-G4-001は**確認した3ケースの範囲で対応済み**。過去のP5-03cの失敗・隔離結果は変更していない。

## 検査と制約

| 検査 | 実行結果 | 証跡 |
|---|---|---|
| 本体3ケースの再発防止 | 3 passed、exit 0 | after-pytest.log |
| backend・fixturesのruff | exit 0 | ruff.log |
| backend・fixturesの整形 | exit 0 | format.log |
| 変更したmiddleware・新規テストのmypy strict | exit 0、2 source files | mypy.log |
| backend全appのbandit | exit 0 | bandit.log |
| 今回の提出ログのgitleaks・skill同期・差分確認 | 各exit 0、秘密情報検出0 | submission-secrets.json・.log、コマンド記録 |
| backend全件pytest・全体mypy・契約テスト | ローカルは未実行。専用DBが必要な全件は、このコミットのCIで確認する | CIの結果はGitHub Actionsの当該SHAで追跡 |

API・画面・データ・評価アルゴリズムを変更していない。契約1.0.2、D-047の契約書設定・Capability実装、Catalog・Composer・Executor・アダプタには差分なし。ホールドアウトのアクセス・生成・マウント、baselineコード参照は行っていない。

全例外経路・他のロガー・外部のログ転送基盤・ログ閲覧権限・保持削除の確認は**未実行**（今回の共通例外ログと合成3ケースの範囲外）。SCA・DAST・実画面・保持削除演習・ホールドアウト再評価は**未実行**。別担当者による今回の差分の独立レビューも**未実行**（今回の修正・試験はCodex自身）。過去のローカル全件pytestのsetup error、semgrepの解析警告、RV-G3-001〜003、ライセンスと来歴・保持の不足は本修正では解消していない。

追加支出0円、有料APIなし、人の実時間は未測定。G4承認は行わない。コマンドと確認結果は [commands.md](commands.md)。
