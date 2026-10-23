"""明示した既存集計だけを照合する。評価・原文・正解・個別出力にはアクセスしない。"""

import csv
import hashlib
import json
import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SOURCES = (
    "reports/eval/2026-10-19-dev/result.json",
    "reports/eval/2026-10-19-dev-v3/result.json",
    "reports/eval/holdout/result.json",
    "reports/eval/2026-10-21-contract-dev/result.json",
    "reports/eval/2026-10-21-contract-cr1-dev/result.json",
    "reports/eval/contract-holdout/baseline.json",
    "reports/eval/contract-holdout/factory.json",
)
METRICS = (
    "field_macro_normalized_match",
    "field_status_agreement",
    "critical_fields_wrong_but_found",
    "critical_rule_recall",
    "critical_rule_positives",
    "evidence_position_accuracy",
    "evidence_spans",
    "evidence_unverified_items",
    "evidence_coverage",
    "missing_outputs",
    "ocr_evidence_spans",
    "ocr_evidence_all_unverified",
)


def load(path: str) -> dict[str, object]:
    raw = json.loads((ROOT / path).read_text(encoding="utf-8"))
    # 集計から選択したスカラーだけを出力する。個別の誤りは索引へ転記しない。
    metrics = {key: raw["metrics"][key] for key in METRICS if key in raw["metrics"]}
    if not all(isinstance(value, (int, float, bool)) for value in metrics.values()):
        raise ValueError("集計に非スカラー値がある")
    return {
        "source": path,
        "dataset": raw["dataset"],
        "split": raw["split"],
        "samples": raw["samples"],
        "manifest_sha256": raw["manifest_sha256"],
        "workflow": {
            key: value
            for key, value in raw["workflow"].items()
            if key in ("workflow_id", "version", "scored_outputs")
        },
        "rule_pack": raw["rule_pack"],
        "metrics": metrics,
    }


def main() -> None:
    rows = [load(path) for path in SOURCES]
    baseline = json.loads((ROOT / SOURCES[-2]).read_text(encoding="utf-8"))
    factory = json.loads((ROOT / SOURCES[-1]).read_text(encoding="utf-8"))
    if (
        baseline["samples"] != factory["samples"]
        or baseline["manifest_sha256"] != factory["manifest_sha256"]
    ):
        raise ValueError("両armの宣言したデータが不一致")
    report_path = "reports/eval/contract-holdout/report.md"
    report = (ROOT / report_path).read_text(encoding="utf-8")
    labels = {
        "critical_fields_wrong_but_found": "重大な誤りの黙認",
        "critical_rule_recall": "重大ルールの再現率",
        "field_macro_normalized_match": "項目抽出",
        "evidence_position_accuracy": "根拠の位置",
        "field_status_agreement": "項目の状態",
        "evidence_coverage": "根拠の網羅",
        "evidence_unverified_items": "未確認の根拠",
        "missing_outputs": "出力の無い文書",
    }
    for key, label in labels.items():
        line = next(
            line for line in report.splitlines() if line.startswith(f"| {label}")
        )
        cells = line.split("|")[1:-1]
        for cell, arm in zip(cells[1:3], (baseline, factory), strict=True):
            match = re.search(r"\d+(?:\.\d+)?", cell)
            if match is None:
                raise ValueError(f"報告の数値を読めない: {key}")
            displayed = Decimal(match.group())
            actual = Decimal(str(arm["metrics"][key])).quantize(
                Decimal(1).scaleb(displayed.as_tuple().exponent), rounding=ROUND_HALF_UP
            )
            if actual != displayed:
                raise ValueError(f"報告の丸め値と不一致: {key}")
    a, b = baseline["metrics"], factory["metrics"]
    threshold = Decimal(str(a["field_macro_normalized_match"])) - Decimal("0.05")
    conditions = {
        "both_critical_wrong_found_zero": a["critical_fields_wrong_but_found"]
        == b["critical_fields_wrong_but_found"]
        == 0,
        "factory_critical_recall_one": b["critical_rule_recall"] == 1,
        "factory_field_at_least_baseline_minus_005": Decimal(
            str(b["field_macro_normalized_match"])
        )
        >= threshold,
        "factory_evidence_at_least_09": b["evidence_position_accuracy"] >= 0.9,
    }
    prereg_path = "docs/experiment/preregistration.md"
    prereg = (ROOT / prereg_path).read_text(encoding="utf-8")
    if (
        "B ≥ A − 0.05" not in prereg
        or "B ≥ 0.9" not in prereg
        or not all(conditions.values())
    ):
        raise ValueError("事前登録または旧集計に対する条件の照合が不一致")
    labor = []
    with (ROOT / "HUMAN_TIME_LOG.csv").open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            note = row["note"].lower()
            kind = (
                "estimate"
                if "estimate" in note
                else "wall_clock_upper_bound"
                if "upper bound" in note
                else "unknown"
            )
            labor.append(
                {
                    "arm": row["arm"],
                    "task_id": row["task_id"],
                    "minutes": row["minutes"],
                    "kind": kind,
                }
            )
    with (ROOT / "COST_LEDGER.csv").open(encoding="utf-8", newline="") as file:
        costs = [
            {key: row[key] for key in ("date", "arm", "phase", "amount_jpy")}
            for row in csv.DictReader(file)
        ]
    inputs = (
        *SOURCES,
        report_path,
        prereg_path,
        "HUMAN_TIME_LOG.csv",
        "COST_LEDGER.csv",
    )
    output = {
        "source_commit": "9801b902f51b1c63642ff14219ba7b2b8fead889",
        "scope": "既存集計の照合。再評価・元の採点の再現ではない。",
        "input_sha256": {
            path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in inputs
        },
        "aggregates": rows,
        "contract_report_numeric_cells_checked": len(labels) * 2,
        "conditions_from_original_aggregates": conditions,
        "contract_field_threshold_decimal": str(threshold),
        "contract_field_margin_decimal": str(
            Decimal(str(b["field_macro_normalized_match"])) - threshold
        ),
        "labor_entries": labor,
        "cost_entries": costs,
        "m1_decision": "未判定（D-050）",
        "m6_break_even": "未算出（構築・保守の実測不足）",
    }
    (OUT / "checked.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
