"""rule_based_extractor.v1 (local, D-015): takes the value printed after a label, without an LLM.

Which labels to look for comes from the node config (`field_spec[].labels`), never from code, so the same
version serves any document type. For each field, every "label：value" line on every page is a candidate:
one distinct value -> found, several different values -> uncertain (value null), none -> missing.
Types this method cannot read (arrays, booleans) are reported as uncertain so a person checks them.
"""

import re
from typing import Any

from app.capabilities.values import nfkc, parse_amount, parse_date

MAX_STRING = 200
# label, then an optional parenthesized note such as "（10%）" or "（普通）", then a colon.
_NOTE = r"(?:[（(][^）)\r\n]{0,40}[）)])?"


def _pattern(label: str) -> re.Pattern[str]:
    return re.compile(re.escape(nfkc(label)) + _NOTE + r"\s*[：:]\s*(?P<value>[^\r\n]*)")


def _read(kind: str, raw: str) -> str | int | None:
    raw = raw.strip()
    if kind == "date":
        return parse_date(raw)
    if kind == "decimal":
        return parse_amount(raw)
    if kind == "integer":
        amount = parse_amount(raw)
        return int(amount) if amount is not None and amount.lstrip("-").isdigit() else None
    if kind == "string":
        return raw[:MAX_STRING] or None
    return None


def extract_by_labels(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    texts = [nfkc(page["text"]) for page in inputs["pages"]]
    fields: dict[str, Any] = {}
    status: dict[str, str] = {}
    for spec in config["field_spec"]:
        name, kind = spec["name"], spec["type"]
        if kind not in ("date", "decimal", "integer", "string"):
            fields[name], status[name] = None, "uncertain"
            continue
        candidates: list[str | int] = []
        unreadable = False
        for label in spec["labels"]:
            pattern = _pattern(label)
            for text in texts:
                for match in pattern.finditer(text):
                    value = _read(kind, match["value"])
                    if value is None:
                        unreadable = True
                    elif value not in candidates:
                        candidates.append(value)
        if len(candidates) == 1:
            fields[name], status[name] = candidates[0], "found"
        elif candidates or unreadable:
            fields[name], status[name] = None, "uncertain"
        else:
            fields[name], status[name] = None, "missing"
    return {"fields": fields, "field_status": status}
