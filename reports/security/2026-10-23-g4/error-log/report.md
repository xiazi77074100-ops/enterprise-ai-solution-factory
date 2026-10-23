# P5-03c：例外ログ秘匿化の独立確認・変更要求

2026-10-23、Codex。対象 `fe581a5d84f0581712fe71afa8f68d9126c9bd54`。これはプロジェクト内の自己診断であり、第三者診断ではない。製品コードは未修正。

## 結論と指摘 VA-G4-001（SR-01）

実際の `SecurityMiddleware` に通常例外・連鎖例外・SQLAlchemyのStatementErrorを渡したところ、**3ケースすべてで合成の機密値がログに混入した**。HTTP応答への混入は0ケース。原因は `backend/app/core/middleware.py:86` の `exc_info=exc` で、標準loggingのフォーマッタが例外本文・原因・SQLパラメータを出力すること。

本物の資格情報・文書・実ログの流出を観測したわけではない。DBや外部APIへ接続せず、ASGIをプロセス内で直接呼び出した。ルータ・認証・実際のDBエラー経路は通していないため、リモートから特定のAPIで誘発できるという証明ではない。

暫定リスクは **中、CVSS v3.1 5.5**（`CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N`）。限定的なローカルログ読取権限を持つ利用者が、本来見られない重大な機密値を取得できる配備を仮定する。実際のログ権限・保持・転送先と本POCの実影響は未確認。C:Hの重大影響は評価上の仮定であり、本物の秘密が漏れたという実績ではない。FIRSTの[CVSS v3.1仕様](https://www.first.org/cvss/v3.1/specification-document)に従い、Impact=3.5952、Exploitability=1.83457659、合計を小数第1位へ切り上げた。CVSSはFIRSTの仕様を参照して使用する。

## 再現結果と修正案の隔離検証

| 条件 | 終了コード | ログ混入 | HTTP混入 | 500応答 / エラー型 / trace復元 | 構造化trace_id |
|---|---:|---:|---:|---|---|
| 実製品・3ケース | **1（診断失敗）** | 3/3 | 0/3 | すべて保持 | 0/3 |
| 差分案を当てた隔離コピー・同じ3ケース | **0** | 0/3 | 0/3 | すべて保持 | 3/3、応答のtrace_idと一致 |

[baseline-result.json](baseline-result.json) と [candidate-result.json](candidate-result.json) に各条件を記録。`baseline-synthetic-logs.txt` はすべてTEST ONLYの値で、通常例外では改行、連鎖例外では原因、SQLAlchemy例外ではパラメータの混入を確認できる。秘密のように見える実在の値を作ったり読んだりしていない。初回確認の `result.json`・`synthetic-logs.txt` も保持し、最終の追加確認項目とは区別した。

診断は `_env_file=None` で環境ファイルを無効にし、DB URLは未使用の明示的な合成値、設定用鍵はプロセス内で生成して認証には使わず記録もしない。例外はリクエストの合成値から作成する。ログは専用ハンドラで捕捉し、実際のアプリのログ設定を一時変更した後に必ず復元する。

## 変更要求（共有処理・製品未適用）

[proposed-fix.patch](proposed-fix.patch) は、例外オブジェクトをログへ渡すのをやめ、固定の書式に例外型・trace_idだけを記録する最小差分。構造化フィールドにも同じ値を保持し、標準のテキスト表示でも確認できる。新しい依存・フィルタ・正規表現は不要。完全なスタックトレースを失う代わりに、型と応答と同じtrace_idで追跡する。

```python
logger.error(
    "unhandled exception: %s (trace_id=%s)",
    type(exc).__name__,
    trace_id_var.get(),
    extra={"error_type": type(exc).__name__, "trace_id": trace_id_var.get()},
)
```

`git apply --check` は0。この差分を今回の証跡ディレクトリ直下の一時コピーにだけ適用し、[verify_candidate.ps1](verify_candidate.ps1) で同じ診断を実行して0を確認した。コピーの削除前に絶対パスが証跡ディレクトリ内であることを確認し、元の環境変数を復元した。製品・contracts・frontendの差分は0。

補足：初期案はextraだけに型・trace_idを保持しており、混入の防止と構造化フィールドの検査は通ったが、標準表示にはtrace_idが出なかった。表示の検査を追加するとexit 1となった結果を `candidate-extra-only-result.json`・`candidate-extra-only-logs.txt` に保存。最終案は通常表示にも型・trace_idが出ることを加えて3ケースともexit 0で確認した。

共有処理への適用は、[並行作業規則](../../../../easf_package/prompts/01_CODEX_PARALLEL.md)の「Never modify shared API schemas, DB migrations, or cross-cutting modules without explicit integration-owner approval.」に従い、統合担当への変更要求として残す。[easf-phase-gate](../../../../.agents/skills/easf-phase-gate/SKILL.md) の停止条件「セキュリティの高・中の指摘を直せない。」にも該当するため、別タスク・次のゲートへは進めない。修正適用の承認後は、この3ケースを本体で再実行し、backend全体のruff・mypy・bandit・pytestと契約テストを確認する。

## 未実行・費用

製品への差分適用・製品修正後の回帰は**未実行**（共有処理の明示承認待ち）。既存ログの実データ調査・ログ権限・転送先の点検、実DBでの例外誘発、API経由の再現、すべての例外経路の網羅は**未実行**（今回の合成・プロセス内診断の範囲外）。SCA・DAST・実画面・保持削除演習も**未実行**。CI成功が得られても、製品の未修正を解消したことにはならない。

ホールドアウトのアクセス・生成・マウント、baselineコード参照は行っていない。D-047・契約・依存・CIも変更していない。追加支出0円、有料APIなし。人の実時間は未測定。コマンドと終了コードは [commands.md](commands.md)。G4承認は行わない。
