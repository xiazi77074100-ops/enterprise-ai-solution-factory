"""The offline evaluator (P3-03) runs on dev only and reports the ADR-007 metrics."""

import json
import shutil
from pathlib import Path

import pytest

from app.evaluation.offline import aggregate_only, evaluate

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
        "critical_fields_wrong_but_found", "ocr_evidence_all_unverified",
    }  # fmt: skip
    assert all(0 <= metrics[k] <= 1 for k in ("field_macro_normalized_match", "evidence_position_accuracy"))


def test_a_split_without_labels_in_the_repository_is_refused() -> None:
    with pytest.raises(SystemExit):
        evaluate(WORKFLOW, PACK, MANIFEST, "holdout")


def _fake_holdout(tmp: Path, ids: tuple[str, ...]) -> Path:
    """A holdout-shaped folder and manifest made from dev files (the real holdout never enters tests)."""
    import hashlib  # noqa: PLC0415
    import shutil  # noqa: PLC0415

    (tmp / "data" / "documents").mkdir(parents=True)
    (tmp / "data" / "labels").mkdir()
    samples = []
    for sample_id in ids:
        label_path = ROOT / "fixtures" / "dev" / "labels" / f"{sample_id}.json"
        label = json.loads(label_path.read_text(encoding="utf-8"))
        document = ROOT / "fixtures" / "dev" / "documents" / label["source_file"]
        shutil.copy(label_path, tmp / "data" / "labels")
        shutil.copy(document, tmp / "data" / "documents")
        samples.append({"sample_id": sample_id, "split": "holdout", "stratum": label["stratum"],
                        "source_file_sha256": hashlib.sha256(document.read_bytes()).hexdigest(),
                        "label_sha256": hashlib.sha256(label_path.read_bytes()).hexdigest()})  # fmt: skip
    manifest = tmp / "manifest.holdout.json"
    manifest.write_text(json.dumps({"dataset": "invoice", "generator_version": "x", "samples": samples}), "utf-8")
    return manifest


def test_holdout_mode_checks_hashes_and_keeps_only_aggregates(tmp_path: Path) -> None:
    manifest = _fake_holdout(tmp_path, ("inv-0001", "inv-0002"))
    result = aggregate_only(evaluate(WORKFLOW, PACK, manifest, "holdout", tmp_path / "data"))
    text = json.dumps(result, ensure_ascii=False)
    assert result["samples"] == 2 and "metrics" in result
    assert "inv-0001" not in text and "field_errors" not in result and "missed_critical_rules" not in result

    label = tmp_path / "data" / "labels" / "inv-0001.json"
    label.write_bytes(label.read_bytes() + b" ")  # any change to a frozen file stops the run
    with pytest.raises(SystemExit):
        evaluate(WORKFLOW, PACK, manifest, "holdout", tmp_path / "data")


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract is not installed (the contract scans use OCR)")
def test_cr1_gold_is_merged_when_asked() -> None:
    """P4-04: the CR-1 gold (labels_cr1) adds one field and CON-006 to the contract evaluation."""
    workflow = json.loads((ROOT / "fixtures" / "workflows" / "contract-v3.json").read_text(encoding="utf-8"))
    pack = json.loads((ROOT / "fixtures" / "rule_packs" / "contract-1.1.0.json").read_text(encoding="utf-8"))
    manifest = ROOT / "fixtures" / "contract" / "manifest.json"
    result = evaluate(workflow, pack, manifest, "dev", extra_labels="labels_cr1")
    assert "antisocial_exclusion" in result["per_field_match"]
    assert "CON-006" in result["rule_confusion"]
