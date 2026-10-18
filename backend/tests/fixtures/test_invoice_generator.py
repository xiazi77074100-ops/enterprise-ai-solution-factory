"""Synthetic invoice generator (fixture-data §6, fixture_plan §1・§2・§4・§8).

The committed dev documents and labels must be exactly what the generator produces from the public seed, every
gold evidence range must contain the printed value of its field, and the holdout plan must cover every rule.
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

from fixtures.generator.__main__ import FIXTURES, check_names, generate, rule_pack  # noqa: E402
from fixtures.generator.invoice import DEV_SEED, LAYOUT_COUNTS, SEVERITY, STRATA, build_plan  # noqa: E402
from fixtures.generator.names import CUSTOMERS, VENDORS, corporate_check_digit, denylisted  # noqa: E402

from app.capabilities.pdf_text import page_texts, span_sha256  # noqa: E402
from app.catalog.validation import validate_rule_pack  # noqa: E402

MANIFEST = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))


def labels() -> list[dict[str, Any]]:
    return [
        json.loads((FIXTURES / "dev" / "labels" / f"{s['sample_id']}.json").read_text(encoding="utf-8"))
        for s in MANIFEST["samples"]
    ]


def test_plan_counts_and_holdout_coverage() -> None:
    plan = build_plan()
    assert len(plan) == 40
    for stratum, dev, holdout in STRATA:
        assert sum(1 for i in plan if i.stratum == stratum and i.split == "dev") == dev, stratum
        assert sum(1 for i in plan if i.stratum == stratum and i.split == "holdout") == holdout, stratum
    layouts = Counter(name for i in plan for name in i.layout)
    assert dict(layouts) == LAYOUT_COUNTS
    assert not [i for i in plan if {"scan", "multi_page"} <= set(i.layout)]
    by_id = {i.sample_id: i for i in plan}
    for item in plan:
        if item.partner:  # duplicate pairs stay in one split, with a normal document
            assert by_id[item.partner].split == item.split and by_id[item.partner].stratum == "normal"
    holdout_strata = Counter(i.stratum for i in plan if i.split == "holdout")
    # Each rule is planted at least once in the holdout, critical rules at least twice (fixture_plan §8).
    assert holdout_strata["total_mismatch"] >= 2 and holdout_strata["payee_changed"] >= 2
    for stratum in ("missing_registration", "bad_registration_format", "missing_due_date", "duplicate_invoice_no"):
        assert holdout_strata[stratum] >= 1


def test_committed_dev_fixtures_are_reproducible(tmp_path: Path) -> None:
    entries = generate("dev", DEV_SEED, tmp_path)
    assert entries == MANIFEST["samples"]
    assert MANIFEST["dev_seed"] == DEV_SEED and len(entries) == 28


def _normalize(field: str, token: str) -> str:
    """Printed token → gold value (money without ¥ and commas, Japanese dates → ISO)."""
    if field in ("subtotal", "tax", "total"):
        return token.replace("¥", "").replace(",", "")
    if field in ("issue_date", "due_date"):
        if (m := re.fullmatch(r"令和(\d+)年(\d+)月(\d+)日", token)) or (
            m := re.fullmatch(r"R(\d+)\.(\d+)\.(\d+)", token)
        ):
            y, mo, d = int(m[1]) + 2018, int(m[2]), int(m[3])
        elif m := re.fullmatch(r"(\d{4})年(\d+)月(\d+)日", token) or re.fullmatch(r"(\d{4})/(\d+)/(\d+)", token):
            y, mo, d = int(m[1]), int(m[2]), int(m[3])
        else:
            raise AssertionError(f"unexpected date format {token!r}")
        return date(y, mo, d).isoformat()
    return token


def test_gold_evidence_points_at_the_printed_values() -> None:
    checked = 0
    for label in labels():
        if label["media_type"] != "application/pdf":
            assert label["gold_evidence"] == {}  # scans: no text layer, evidence only via OCR (unverified)
            continue
        texts = page_texts((FIXTURES / "dev" / "documents" / label["source_file"]).read_bytes())
        assert all("TEST ONLY" in t for t in texts), label["sample_id"]
        for field, spans in label["gold_evidence"].items():
            uncertain = label["gold_field_status"][field] == "uncertain"
            assert len(spans) >= 2 if uncertain else len(spans) == 1, (label["sample_id"], field)
            for span in spans:
                text = texts[span["page"] - 1]
                assert span_sha256(text, span["start"], span["end"]) == span["text_sha256"]
                printed = text[span["start"] : span["end"]]
                if not uncertain:  # an uncertain field cites every candidate; none of them is the gold value
                    assert _normalize(field, printed) == label["gold_fields"][field], (label["sample_id"], field)
                checked += 1
        # Every found field (except the item table) has evidence.
        found = {f for f, s in label["gold_field_status"].items() if s == "found" and f != "line_items"}
        assert found <= set(label["gold_evidence"]), label["sample_id"]
    assert checked > 200


def test_label_consistency() -> None:
    for label in labels():
        fields, status, findings = label["gold_fields"], label["gold_field_status"], label["gold_findings"]
        assert label["data_origin"] == "synthetic" and label["policy_version"] == "invoice@1.1.0"
        results = {f["rule_id"]: f["result"] for f in findings}
        assert {f["rule_id"]: f["severity"] for f in findings} == SEVERITY
        if fields["due_date"]:
            assert fields["issue_date"] <= fields["due_date"]
        assert (status["due_date"] == "missing") == (results["INV-005"] == "fail")
        assert (status["registration_no"] == "missing") == (results["INV-002"] == "fail")
        if fields["total"] is not None:
            matches = int(fields["total"]) == int(fields["subtotal"]) + int(fields["tax"])
            assert matches == (results["INV-001"] == "pass"), label["sample_id"]
        else:
            assert status["total"] == "uncertain" and results["INV-001"] == "uncertain"
        planted = set(label["planted"])
        assert (results["INV-004"] == "fail") == ("payee_changed" in planted)
        assert (label["injection"] is not None) == (label["stratum"] == "injected_instruction")
        if label["stratum"] == "normal":
            assert set(results.values()) == {"pass"}


def test_names_and_numbers_are_fictitious() -> None:
    check_names()  # raises if any generated name contains a denylisted real name
    for vendor in VENDORS:
        assert not denylisted(vendor.name) and not denylisted(vendor.bank.name)
        digits = vendor.registration_no[1:]
        assert re.fullmatch(r"T\d{13}", vendor.registration_no)
        assert int(digits[0]) != corporate_check_digit(digits[1:])  # never a valid corporate number
        assert vendor.address.startswith("〒000-") and vendor.phone.startswith("00-")
    assert not [c for c in CUSTOMERS if denylisted(c)]


def test_rule_pack_1_1_0_registers_every_vendor() -> None:
    pack = rule_pack()
    assert validate_rule_pack(pack) == []
    committed = json.loads((FIXTURES / "rule_packs" / "invoice-1.1.0.json").read_text(encoding="utf-8"))
    assert committed == pack
    payees = {p["vendor_name"]: p["payee_account"] for p in pack["reference_tables"]["registered_payees"]}
    assert payees == {v.name: v.account for v in VENDORS}


@pytest.mark.parametrize("command", [["holdout", "--out", "fixtures-holdout-inside"]])
def test_holdout_refuses_missing_seed_or_repo_output(command: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    from fixtures.generator.__main__ import main

    monkeypatch.delenv("EASF_HOLDOUT_SEED", raising=False)
    assert main(command) == 2  # no secret seed
    monkeypatch.setenv("EASF_HOLDOUT_SEED", "not-a-real-secret")
    assert main(["holdout", "--out", str(ROOT / "fixtures" / "x")]) == 2  # inside the repository
