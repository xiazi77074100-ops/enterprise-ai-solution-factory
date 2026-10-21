"""The arm-neutral scorer (P4-05): outputs built from the gold score perfectly; omissions and silent errors count."""

import json
from pathlib import Path
from typing import Any

from app.evaluation.score_outputs import score

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "fixtures" / "contract" / "manifest.json"
SCORING = json.loads((ROOT / "experiment" / "contract_scoring.json").read_text(encoding="utf-8"))
LABELS = ROOT / "fixtures" / "contract" / "dev" / "labels"


def _perfect(sample_id: str) -> dict[str, Any]:
    label = json.loads((LABELS / f"{sample_id}.json").read_text(encoding="utf-8"))
    cr1 = json.loads((LABELS.parent / "labels_cr1" / f"{sample_id}.json").read_text(encoding="utf-8"))
    fields = {**label["gold_fields"], cr1["field"]: cr1["value"]}
    status = {**label["gold_field_status"], cr1["field"]: cr1["status"]}
    evidence = {**label["gold_evidence"], cr1["field"]: cr1["gold_evidence"]}
    return {
        "sample_id": sample_id,
        "fields": fields,
        "field_status": status,
        "findings": [*label["gold_findings"], cr1["finding"]],
        "evidence": {
            name: [
                {"page": s["page"], "start": s["start"], "end": s["end"], "quote": "x", "verified": True} for s in spans
            ]
            for name, spans in evidence.items()
        },
    }


def _write(folder: Path, docs: list[dict[str, Any]]) -> None:
    folder.mkdir()
    for doc in docs:
        (folder / f"{doc['sample_id']}.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


def test_gold_shaped_outputs_score_perfectly_and_omissions_count(tmp_path: Path) -> None:
    ids = [s["sample_id"] for s in json.loads(MANIFEST.read_text(encoding="utf-8"))["samples"]]
    docs = [_perfect(i) for i in ids]
    for doc in docs:  # quotes are taken from the page text at the gold offsets by the scorer itself
        for spans in doc["evidence"].values():
            for item in spans:
                item.pop("quote")
    _write(tmp_path / "all", docs)
    result = score(tmp_path / "all", SCORING, MANIFEST, "dev", extra_labels="labels_cr1")
    metrics = result["metrics"]
    assert metrics["field_macro_normalized_match"] == 1.0 and metrics["critical_rule_recall"] == 1.0
    assert metrics["critical_fields_wrong_but_found"] == 0 and metrics["missing_outputs"] == 0

    _write(tmp_path / "some", docs[1:])
    partial = score(tmp_path / "some", SCORING, MANIFEST, "dev", extra_labels="labels_cr1")["metrics"]
    assert partial["missing_outputs"] == 1 and partial["field_macro_normalized_match"] < 1.0


def test_a_wrong_critical_value_marked_found_is_silent(tmp_path: Path) -> None:
    doc = _perfect("con-0001")
    doc["fields"]["liability_cap_jpy"] = "1"  # wrong, but presented as settled
    doc["field_status"]["liability_cap_jpy"] = "found"
    _write(tmp_path / "one", [doc])
    result = score(tmp_path / "one", SCORING, MANIFEST, "dev", extra_labels="labels_cr1")
    assert {"sample_id": "con-0001", "field": "liability_cap_jpy"} in result["silent_critical_errors"]
