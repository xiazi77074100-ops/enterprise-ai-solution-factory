"""The offline evaluator (P3-03) runs on dev only and reports the ADR-007 metrics."""

import json
from pathlib import Path

import pytest

from app.evaluation.offline import evaluate

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = json.loads((ROOT / "fixtures" / "workflows" / "invoice-v2.json").read_text(encoding="utf-8"))
PACK = json.loads((ROOT / "fixtures" / "rule_packs" / "invoice-1.1.0.json").read_text(encoding="utf-8"))
MANIFEST = ROOT / "fixtures" / "manifest.json"


def test_dev_evaluation_reports_every_metric() -> None:
    result = evaluate(WORKFLOW, PACK, MANIFEST, "dev")
    assert result["samples"] == 28 and result["rule_pack"] == "invoice@1.1.0"
    metrics = result["metrics"]
    assert set(metrics) >= {
        "field_macro_normalized_match", "critical_rule_recall", "evidence_position_accuracy",
        "critical_fields_wrong_but_found", "unverified_evidence_never_positioned",
    }  # fmt: skip
    assert all(0 <= metrics[k] <= 1 for k in ("field_macro_normalized_match", "evidence_position_accuracy"))


def test_a_split_without_labels_in_the_repository_is_refused() -> None:
    with pytest.raises(SystemExit):
        evaluate(WORKFLOW, PACK, MANIFEST, "holdout")
