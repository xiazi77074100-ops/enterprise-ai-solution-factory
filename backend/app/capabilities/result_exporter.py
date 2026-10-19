"""result_exporter.v1 (local): the reviewed result as JSON or CSV (upload-and-files.md: CSV injection).

The capability fixes the content and returns its id (a UUID derived from the content hash). The file itself
is rendered again by exportRunResult from the stored node outputs with the same functions, and the id is
compared, so what is downloaded is exactly what the run produced.
"""

import csv
import hashlib
import io
import json
import uuid
from typing import Any

EXPORT_NAMESPACE = uuid.UUID("6f1d2a4e-4c1b-5b8e-9a51-2f0c7d3e8a10")
CSV_COLUMNS = ("区分", "名前", "値", "重要度", "結果")
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")
DECISION_JA = {"approved": "承認", "approved_with_corrections": "修正して承認", "rejected": "却下"}


def document(inputs: dict[str, Any]) -> dict[str, Any]:
    """The canonical export content (also the JSON export)."""
    return {
        "decision": inputs["decision"],
        "fields": inputs["reviewed_fields"],
        "findings": inputs["findings"],
    }


def export_id(content: dict[str, Any]) -> str:
    canonical = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(uuid.uuid5(EXPORT_NAMESPACE, hashlib.sha256(canonical.encode()).hexdigest()))


def safe_cell(value: Any) -> str:
    """A cell Excel will not evaluate: a leading = + - @ tab or CR gets a quote in front."""
    if value is None:
        return ""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return "'" + text if text.startswith(_FORMULA_START) else text


def render_csv(content: dict[str, Any], title: str | None = None) -> bytes:
    """UTF-8 with BOM (opened in Excel), CRLF, every cell passed through safe_cell."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    if title:
        writer.writerow([safe_cell(title)])
    writer.writerow(CSV_COLUMNS)
    writer.writerow(["判定", "decision", safe_cell(DECISION_JA.get(content["decision"], content["decision"])), "", ""])
    for name, value in content["fields"].items():
        writer.writerow(["項目", safe_cell(name), safe_cell(value), "", ""])
    for finding in content["findings"]:
        writer.writerow(
            ["ルール", safe_cell(finding["rule_id"]), safe_cell(finding["message"]), finding["severity"],
             finding["result"]]
        )  # fmt: skip
    return ("﻿" + buf.getvalue()).encode("utf-8")


def export_result(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    return {"export_id": export_id(document(inputs)), "format": config["format"]}
