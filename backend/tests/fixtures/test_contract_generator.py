"""Synthetic contract generator (P4-01; fixture-data §6, fixture_plan §1・§2.2・§2.3・§8).

The committed dev contracts and labels must be exactly what the generator produces from the public seed, every
gold evidence range must contain the printed value, labels must agree with the policy, and the CR-1 gold must stay
in its own files.
"""

import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from fixtures.generator import contract  # noqa: E402
from fixtures.generator.__main__ import CONTRACT_DIR, generate_contracts, main  # noqa: E402

from app.capabilities.pdf_text import page_texts, span_sha256  # noqa: E402

MANIFEST = json.loads((CONTRACT_DIR / "manifest.json").read_text(encoding="utf-8"))


def _load(folder: str) -> list[dict[str, Any]]:
    return [
        json.loads((CONTRACT_DIR / "dev" / folder / f"{s['sample_id']}.json").read_text(encoding="utf-8"))
        for s in MANIFEST["samples"]
    ]


def test_plan_counts_and_holdout_coverage() -> None:
    plan = contract.build_plan()
    assert len(plan) == 40
    for stratum, dev, holdout in contract.STRATA:
        assert sum(1 for i in plan if i.stratum == stratum and i.split == "dev") == dev, stratum
        assert sum(1 for i in plan if i.stratum == stratum and i.split == "holdout") == holdout, stratum
    assert dict(Counter(name for i in plan for name in i.layout)) == contract.LAYOUT_COUNTS
    assert not [i for i in plan if {"scan", "multi_page"} <= set(i.layout)]
    numbering = Counter(i.numbering for i in plan)
    assert set(numbering) == set(contract.NUMBERING) and max(numbering.values()) - min(numbering.values()) <= 1
    holdout_strata = Counter(i.stratum for i in plan if i.split == "holdout")
    # The critical rule (CON-001) is planted at least twice in the holdout, every other rule at least once.
    assert holdout_strata["missing_confidentiality"] + holdout_strata["injected_instruction"] >= 2
    for stratum in ("excessive_liability", "auto_renewal", "missing_notice", "missing_governing_law"):
        assert holdout_strata[stratum] >= 1
    for split, absent in contract.CR1_ABSENT.items():
        assert sum(1 for i in plan if i.split == split and not i.antisocial) == absent


def test_committed_dev_contracts_are_reproducible(tmp_path: Path) -> None:
    entries = generate_contracts("dev", contract.DEV_SEED, tmp_path)
    assert entries == MANIFEST["samples"]
    assert MANIFEST["dev_seed"] == contract.DEV_SEED and len(entries) == 28


def _normalize(field: str, token: str) -> Any:
    """Printed token → gold value."""
    if field == "liability_cap_jpy":
        if token.endswith("万円"):
            return str(int(token[:-2].replace(",", "")) * 10_000)
        return token.removesuffix("円").replace(",", "")
    if field == "termination_notice_days":
        return token.removesuffix("日前")
    if field == "auto_renewal":
        return {"自動更新はしない": False, "同一条件でさらに1年間更新": True}[token]
    if field in ("effective_date", "end_date"):
        if (m := re.fullmatch(r"令和(\d+)年(\d+)月(\d+)日", token)) or (
            m := re.fullmatch(r"R(\d+)\.(\d+)\.(\d+)", token)
        ):
            y, mo, d = int(m[1]) + 2018, int(m[2]), int(m[3])
        elif m := re.fullmatch(r"(\d{4})年(\d+)月(\d+)日", token):
            y, mo, d = int(m[1]), int(m[2]), int(m[3])
        else:
            raise AssertionError(f"unexpected date format {token!r}")
        return date(y, mo, d).isoformat()
    return token


def test_gold_evidence_points_at_the_printed_values() -> None:
    checked = 0
    for label in _load("labels"):
        if label["media_type"] != "application/pdf":
            assert label["gold_evidence"] == {} and label["page_count"] == 1
            continue
        texts = page_texts((CONTRACT_DIR / "dev" / "documents" / label["source_file"]).read_bytes())
        assert all("TEST ONLY" in t and "法的助言ではありません" in t for t in texts), label["sample_id"]
        assert label["page_count"] == len(texts)
        for field, spans in label["gold_evidence"].items():
            uncertain = label["gold_field_status"][field] == "uncertain"
            assert len(spans) == (2 if uncertain else 1), (label["sample_id"], field)
            for span in spans:
                text = texts[span["page"] - 1]
                assert span_sha256(text, span["start"], span["end"]) == span["text_sha256"]
                if not uncertain:
                    printed = text[span["start"] : span["end"]]
                    assert _normalize(field, printed) == label["gold_fields"][field], (label["sample_id"], field)
                checked += 1
        found = {f for f, s in label["gold_field_status"].items() if s == "found"}
        assert found <= set(label["gold_evidence"]), label["sample_id"]
    assert checked > 180


def test_label_consistency() -> None:
    for label in _load("labels"):
        fields, status = label["gold_fields"], label["gold_field_status"]
        results = {f["rule_id"]: f["result"] for f in label["gold_findings"]}
        assert {f["rule_id"]: f["severity"] for f in label["gold_findings"]} == contract.SEVERITY
        assert label["data_origin"] == "synthetic" and label["policy_version"] == "contract@1.0.0"
        assert fields["effective_date"] < fields["end_date"]
        assert (status["confidentiality"] == "missing") == (results["CON-001"] == "fail")
        assert (fields["auto_renewal"] is True) == (results["CON-003"] == "fail")
        assert (status["governing_law"] == "missing") == (results["CON-005"] == "fail")
        assert (status["termination_notice_days"] == "missing") == (results["CON-004"] == "fail")
        assert (status["liability_cap_jpy"] == "uncertain") == (results["CON-002"] == "uncertain")
        if fields["liability_cap_jpy"] is not None:
            over = int(fields["liability_cap_jpy"]) > contract.LIABILITY_LIMIT
            assert over == (results["CON-002"] == "fail"), label["sample_id"]
        assert (label["injection"] is not None) == (label["stratum"] == "injected_instruction")
        if label["stratum"] == "injected_instruction":
            assert results["CON-001"] == "fail"  # the planted instruction must not hide the missing clause
        if label["stratum"] == "normal":
            assert set(results.values()) == {"pass"}
        assert "antisocial_exclusion" not in json.dumps(label, ensure_ascii=False)  # CR-1 is not revealed


def test_cr1_gold_is_separate_and_consistent() -> None:
    plan = {i.sample_id: i for i in contract.build_plan()}
    for cr1 in _load("labels_cr1"):
        present = plan[cr1["sample_id"]].antisocial
        assert cr1["field"] == "antisocial_exclusion" and cr1["status"] == ("found" if present else "missing")
        assert cr1["finding"] == {"rule_id": "CON-006", "severity": "critical", "result": "pass" if present else "fail"}
        assert (cr1["value"] is not None) == present


@pytest.mark.parametrize("inside", [False, True])
def test_contract_holdout_refuses_missing_seed_or_repo_output(inside: bool, monkeypatch: pytest.MonkeyPatch) -> None:
    if inside:
        monkeypatch.setenv("EASF_HOLDOUT_SEED", "not-a-real-secret")
        assert main(["contract-holdout", "--out", str(ROOT / "fixtures" / "x")]) == 2  # inside the repository
    else:
        monkeypatch.delenv("EASF_HOLDOUT_SEED", raising=False)
        assert main(["contract-holdout", "--out", "anywhere"]) == 2  # no secret seed
