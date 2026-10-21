"""P3-01c functions: evidence location, the local MCP tool, the Catalog's tool-schema check and the export."""

import copy
import csv
import io
import json
from pathlib import Path
from typing import Any

import pytest

from app.capabilities.evidence import locate
from app.capabilities.pdf_text import span_sha256
from app.capabilities.result_exporter import export_id, export_result, render_csv, safe_cell
from app.catalog.validation import validate_capability
from app.mcp_server import call

ROOT = Path(__file__).resolve().parents[3]
LOCATOR: dict[str, Any] = json.loads(
    (ROOT / "contracts" / "examples" / "capabilities" / "evidence_locator.json").read_text(encoding="utf-8")
)
TEXT = "請求書番号：2025-0001\r\n請求日：令和7年6月12日\r\n小計：¥94,600\r\n合計金額：¥104,060\r\n"
PAGES = [{"page": 1, "text": TEXT, "extraction_method": "text_layer"}]
DOC = "00000000-0000-0000-0000-000000000001"


def _spans(fields: dict[str, Any], match: str = "normalized") -> dict[str, list[dict[str, Any]]]:
    evidence: dict[str, list[dict[str, Any]]] = locate(DOC, PAGES, fields, match)["evidence"]
    return evidence


def test_evidence_points_at_the_printed_form_and_hashes_it() -> None:
    evidence = _spans({"invoice_no": "2025-0001", "issue_date": "2025-06-12", "subtotal": "94600"})
    for name, printed in (("invoice_no", "2025-0001"), ("issue_date", "令和7年6月12日"), ("subtotal", "¥94,600")):
        (span,) = evidence[name]
        assert TEXT[span["start"] : span["end"]] == printed
        assert span["text_sha256"] == span_sha256(TEXT, span["start"], span["end"])
        assert span["status"] == "verified" and span["document_id"] == DOC and span["page"] == 1


def test_values_not_in_the_text_get_no_evidence() -> None:
    evidence = _spans({"total": "999999", "missing": None, "flag": True, "x": "1"})
    assert evidence == {"total": [], "missing": [], "flag": [], "x": []}  # never invented


def test_exact_match_does_not_translate_formats() -> None:
    assert _spans({"issue_date": "2025-06-12"}, match="exact") == {"issue_date": []}


def test_overlapping_forms_are_reported_once_and_only_the_first_occurrence_is_cited() -> None:
    (span,) = _spans({"total": "104060"})["total"]  # "¥104,060" and "104,060" overlap: the longer one wins
    assert TEXT[span["start"] : span["end"]] == "¥104,060"
    many = [
        {"page": 1, "text": "前文 AB 本文 AB", "extraction_method": "text_layer"},
        {"page": 2, "text": "署名 AB", "extraction_method": "text_layer"},
    ]
    (first,) = locate(DOC, many, {"v": "AB"}, "exact")["evidence"]["v"]  # P4-03: a repeated name cites its first place
    assert (first["page"], first["start"]) == (1, 3)


def test_short_bare_numbers_are_not_searched() -> None:
    text = "2025年5月30日\r\n30日前までに通知する。\r\n税：¥840"
    pages = [{"page": 1, "text": text, "extraction_method": "text_layer"}]
    evidence = locate(DOC, pages, {"days": "30", "tax": "840"}, "normalized")["evidence"]
    assert evidence["days"] == []  # "30" alone would cite the day of a date
    (tax,) = evidence["tax"]
    assert text[tax["start"] : tax["end"]] == "¥840"  # a form with a symbol is still found


def test_mcp_tool_validates_input_and_denies_unknown_tools() -> None:
    out = call("locate_evidence", {"document_id": DOC, "pages": PAGES, "fields": {"a": "2025-0001"}, "match": "exact"})
    assert out["evidence"]["a"][0]["status"] == "verified"
    with pytest.raises(ValueError):
        call("locate_evidence", {"document_id": DOC, "pages": PAGES, "fields": {}, "match": "fuzzy"})
    with pytest.raises(KeyError):
        call("run_shell", {})


def test_catalog_rejects_a_contract_that_differs_from_the_advertised_tool() -> None:
    assert validate_capability(LOCATOR) == []
    changed = copy.deepcopy(LOCATOR)
    changed["output_schema"]["properties"]["evidence"]["maxProperties"] = 5
    assert [i.code for i in validate_capability(changed)] == ["tool_schema_mismatch"]
    other_tool = {**copy.deepcopy(LOCATOR), "implementation": {"ref": "easf_local_mcp:locate_evidence"}}
    other_tool["configuration_schema"]["properties"]["match"]["enum"] = ["exact"]
    assert [i.code for i in validate_capability(other_tool)] == ["tool_schema_mismatch"]


@pytest.mark.parametrize("value", ["=1+1", "+cmd", "-2", "@SUM(A1)", "\tx", "\rx"])
def test_csv_cells_that_excel_would_evaluate_get_a_quote(value: str) -> None:
    assert safe_cell(value) == "'" + value


def test_csv_export_is_bom_utf8_and_neutralized() -> None:
    content = {
        "decision": "approved_with_corrections",
        "fields": {"vendor_name": '=HYPERLINK("http://x")', "total": "104060", "none": None},
        "findings": [{"rule_id": "INV-001", "severity": "critical", "result": "pass", "message": "合計：適合"}],
    }
    body = render_csv(content, "請求書の確認結果")
    assert body.startswith("﻿".encode())
    rows = list(csv.reader(io.StringIO(body.decode("utf-8-sig"))))
    assert rows[0] == ["請求書の確認結果"]
    assert ["判定", "decision", "修正して承認", "", ""] in rows
    assert ["項目", "vendor_name", '\'=HYPERLINK("http://x")', "", ""] in rows
    assert ["項目", "none", "", "", ""] in rows
    assert ["ルール", "INV-001", "合計：適合", "critical", "pass"] in rows


def test_export_id_depends_only_on_content() -> None:
    inputs = {"reviewed_fields": {"a": "1"}, "findings": [], "decision": "approved"}
    first = export_result(inputs, {"format": "csv"})
    assert first == export_result(dict(reversed(list(inputs.items()))), {"format": "csv"})
    assert first["export_id"] != export_result({**inputs, "decision": "rejected"}, {"format": "csv"})["export_id"]
    assert first["export_id"] == export_id({"decision": "approved", "fields": {"a": "1"}, "findings": []})
