# 契約 v1（G0 で凍結）

| ファイル | 内容 |
|---|---|
| `openapi.yaml` | REST API（OpenAPI 3.1） |
| `capability.schema.json` | Capability の版の契約 |
| `workflow.schema.json` | 型付き DAG（版の固定・辺の対応付け・予算） |
| `rule_pack.schema.json` | 業務ルール（固定の演算子だけの式） |
| `events.schema.json` | トレース・監査イベント |
| `llm_profile.schema.json` | LLM プロファイル（Claude / OpenAI / Azure OpenAI / Gemini / mock） |
| `examples/` | 6 Capability・2 Workflow・2 Rule pack・LLM プロファイルの見本 |

所有者は Claude Code だけ（`AGENTS.md`）。凍結後の変更は版を上げ、全利用者のテストを通してから。`easf_package/schemas/` からの変更点は `docs/phase0/PHASE0_PLAN.md` §B-4（S1〜S11）。

## 検査

```sh
python -m venv .venv-tools && .venv-tools/Scripts/python -m pip install jsonschema pyyaml openapi-spec-validator
.venv-tools/Scripts/python scripts/validate_contracts.py
```

2026-10-18 の実行結果：`OK: schemas=5 capabilities=6 rule_packs=2 workflows=2 openapi=valid`（終了コード 0）。陰性試験（循環・未登録の版・入力の不足・外部 `$ref`・冪等でないリトライ・汎用エンジン内の業務名）はすべて検出（終了コード 1）。
