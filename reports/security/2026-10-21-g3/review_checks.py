"""P4-06: 公開済み集計値と Git 差分だけの再確認。文書・ラベルを読まない。"""

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
a, b = [json.loads((ROOT / f"reports/eval/contract-holdout/{arm}.json").read_text(encoding="utf-8"))
        for arm in ("baseline", "factory")]
for row in (a, b):
    assert row["samples"] == 12
    assert not {"field_errors", "silent_critical_errors", "missed_critical_rules"} & row.keys()
    assert row["metrics"]["critical_fields_wrong_but_found"] == 0
    assert row["metrics"]["critical_rule_recall"] == 1
    assert row["metrics"]["evidence_position_accuracy"] == 1
    assert row["metrics"]["missing_outputs"] == 0
    assert all(sum(counts.values()) == 12 for counts in row["rule_confusion"].values())
assert a["manifest_sha256"] == b["manifest_sha256"]
threshold = a["metrics"]["field_macro_normalized_match"] - 0.05
margin = b["metrics"]["field_macro_normalized_match"] - threshold
assert margin > 0
assert sum(v.get("pass->fail", 0) for v in b["rule_confusion"].values()) == 3
print(f"A={a['metrics']['field_macro_normalized_match']:.12f}")
print(f"B={b['metrics']['field_macro_normalized_match']:.12f}; 閾値={threshold:.12f}; 余裕={margin:.12f}")
print("12 件、重大黙認 0、重大再現率 1、根拠位置 1、誤警告 3：報告の丸め値と一致")
files = subprocess.check_output(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "71abf10"],
                                cwd=ROOT, text=True).splitlines()
print("CR-1 の app 配下の変更:", [p for p in files if p.startswith("backend/app/")])
engine = subprocess.check_output(["git", "diff", "e52a823~1..2b87f6f", "--", "backend/app/catalog",
                                  "backend/app/composer", "backend/app/executor", "backend/app/adapters"],
                                 cwd=ROOT, text=True)
assert not engine
print("指定差分の catalog/composer/executor/adapters: 変更なし")
