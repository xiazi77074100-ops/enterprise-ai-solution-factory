"""P4-06: dev データだけで採点の中立性と集計の境界を確認する。"""

import copy
import json
from pathlib import Path

from app.evaluation.offline import aggregate_only
from app.evaluation.score_outputs import _position, score
from tests.unit.test_score_outputs import MANIFEST, SCORING, _perfect, _write


def test_identical_arm_outputs_have_identical_scores(tmp_path: Path) -> None:
    ids = [s["sample_id"] for s in json.loads(MANIFEST.read_text(encoding="utf-8"))["samples"]]
    docs = [_perfect(i) for i in ids]
    _write(tmp_path / "arm_a", docs)
    _write(tmp_path / "arm_b", copy.deepcopy(docs))
    results = [score(tmp_path / arm, SCORING, MANIFEST, "dev", extra_labels="labels_cr1")
               for arm in ("arm_a", "arm_b")]  # fmt: skip
    for result in results:
        result.pop("workflow")  # 出力フォルダの名前は来歴であり、採点には使わない。
    assert results[0] == results[1]


def test_fabricated_quote_is_not_verified_by_offsets() -> None:
    assert _position(["abcdef"], {"page": 1, "start": 0, "end": 3,
                                  "quote": "fabricated", "verified": True}) is None  # fmt: skip
    assert _position(["abcdef"], {"page": 2, "quote": "abc"}) is None
    assert _position(["abcdef"], {"page": 1, "start": 0, "end": 3, "verified": True}) is None


def test_negative_offsets_cannot_expand_evidence_into_unrelated_gold() -> None:
    # Python の負のスライスを位置として採用すると、前半の無関係な正解と重なる。
    assert _position(["abcdef"], {"page": 1, "start": -3, "end": 6, "quote": "def"}) == (1, 3, 6)


def test_aggregate_removes_document_ids_and_values(tmp_path: Path) -> None:
    _write(tmp_path / "arm", [_perfect("con-0001")])
    result = score(tmp_path / "arm", SCORING, MANIFEST, "dev", extra_labels="labels_cr1")
    result["field_errors"] = [{"sample_id": "PRIVATE_SAMPLE", "gold": "PRIVATE_VALUE"}]
    result["silent_critical_errors"] = [{"sample_id": "PRIVATE_SAMPLE"}]
    result["missed_critical_rules"] = [{"sample_id": "PRIVATE_SAMPLE"}]
    aggregate = aggregate_only(result)
    assert set(aggregate) == {"dataset", "split", "samples", "manifest_sha256", "workflow", "rule_pack",
                              "metrics", "per_field_match", "rule_confusion"}  # fmt: skip
    assert "PRIVATE_" not in json.dumps(aggregate)
    assert aggregate["metrics"] == result["metrics"]
