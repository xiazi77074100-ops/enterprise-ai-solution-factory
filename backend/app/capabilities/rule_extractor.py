"""rule_based_extractor.v1 (local, D-015): takes the value printed after a label, without an LLM.

Which labels to look for comes from the node config (`field_spec[].labels`), never from code, so the same
version serves any document type. For each field, every "label：value" line on every page is a candidate:
one distinct value -> found, several different values -> uncertain (value null), none -> missing.
Types this method cannot read (arrays, booleans) are reported as uncertain so a person checks them.
A value read from an OCR page (`extraction_method` other than text_layer) is never `found`: OCR misreads
characters such as ¥ and separators, so the value is kept as a draft but reported as uncertain (D-034).
"""

import re
from dataclasses import dataclass
from typing import Any

from app.capabilities.values import nfkc, parse_amount, parse_date

MAX_STRING = 200
# label, then an optional parenthesized note such as "（10%）" or "（普通）", then a colon.
_NOTE = r"(?:[（(][^）)\r\n]{0,40}[）)])?"


def _pattern(label: str) -> re.Pattern[str]:
    return re.compile(re.escape(nfkc(label)) + _NOTE + r"\s*[：:]\s*(?P<value>[^\r\n]*)")


# OCR clean-up (D-036). Tesseract reads the yen thousands separator "," as "." ("8,400" -> "8.400"), and a
# value cell may be followed by a column gap and table rules ("こもれび信用金庫      -").
_OCR_THOUSANDS = re.compile(r"(?<=\d)\.(?=\d{3}(?!\d))")
_OCR_COLUMN_GAP = re.compile(r"\s{2,}.*$")


def _clean_ocr(raw: str) -> str:
    raw = _OCR_THOUSANDS.sub(",", _OCR_COLUMN_GAP.sub("", raw.strip()))
    return raw.strip(" -_|")


def _read(kind: str, raw: str, ocr_page: bool = False) -> str | int | None:
    raw = _clean_ocr(raw) if ocr_page else raw.strip()
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


MAX_BETWEEN = 60  # characters between `before` and `after` (one phrase, never across a sentence end)
MAX_HEADING = 30  # a heading is a short line; a long sentence that merely mentions the title is not one


@dataclass
class _Page:
    text: str  # NFKC
    joined: str  # NFKC without line breaks: phrases wrapped across lines still match
    lines: list[tuple[str, str]]  # (NFKC line, line as printed)
    ocr: bool


def _pages(inputs: dict[str, Any]) -> list[_Page]:
    pages = []
    for page in inputs["pages"]:
        raw_lines = [line.strip() for line in page["text"].splitlines()]
        text = nfkc(page["text"])
        pages.append(
            _Page(
                text=text,
                joined=re.sub(r"[\r\n]+", "", text),
                lines=[(nfkc(line), line) for line in raw_lines if line],
                ocr=page["extraction_method"] != "text_layer",
            )
        )
    return pages


def _between(page: _Page, before: str, after: str) -> list[str]:
    """Literal text between `before` and `after` (`before` empty: from the start of a line). No regex from config."""
    before, after = nfkc(before), nfkc(after)
    found = []
    if not before:
        for line, _ in page.lines:
            end = line.find(after)
            if end > 0:
                found.append(line[:end])
        return found
    start = 0
    while (at := page.joined.find(before, start)) != -1:
        begin = at + len(before)
        end = page.joined.find(after, begin)
        value = page.joined[begin:end] if end != -1 else ""
        if 0 < len(value) <= MAX_BETWEEN and "。" not in value:
            found.append(value)
        start = begin
    return found


def _candidates(spec: dict[str, Any], page: _Page) -> tuple[list[Any], bool]:
    """Values this field's settings find on one page, and whether something was found but could not be read."""
    kind = spec["type"]
    values: list[Any] = []
    unreadable = False
    if kind == "boolean":
        if any(nfkc(p) in page.joined for p in spec.get("true_if", [])):
            values.append(True)
        if any(nfkc(p) in page.joined for p in spec.get("false_if", [])):
            values.append(False)
        return values, False
    raws = [m["value"] for label in spec.get("labels", []) for m in _pattern(label).finditer(page.text)]
    raws += [v for pair in spec.get("between", []) for v in _between(page, pair["before"], pair["after"])]
    for raw in raws:
        value = _read(kind, raw, page.ocr)
        if value is None:
            unreadable = True
        else:
            values.append(value)
    if "heading" in spec:
        title = nfkc(spec["heading"])
        # The heading is returned as printed (not NFKC), so evidence can be located in the page text.
        values += [printed for line, printed in page.lines if title in line and len(line) <= MAX_HEADING]
    return values, unreadable


def extract_by_labels(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Version 1.0.0 settings (`labels` only) behave exactly as before. Version 1.1.0 adds `between`, `heading`,
    `true_if` / `false_if` (booleans) and `uncertain_if` (phrases meaning the value is not settled), all literal."""
    pages = _pages(inputs)
    fields: dict[str, Any] = {}
    status: dict[str, str] = {}
    for spec in config["field_spec"]:
        name, kind = spec["name"], spec["type"]
        boolean = kind == "boolean" and ("true_if" in spec or "false_if" in spec)
        if kind not in ("date", "decimal", "integer", "string") and not boolean:
            fields[name], status[name] = None, "uncertain"
            continue
        candidates: list[Any] = []
        unreadable = from_ocr = False
        for page in pages:
            values, page_unreadable = _candidates(spec, page)
            unreadable = unreadable or page_unreadable
            from_ocr = from_ocr or (page.ocr and (bool(values) or page_unreadable))
            for value in values:  # the same value found by two labels is one candidate
                if value not in candidates:
                    candidates.append(value)
        hedged = any(nfkc(p) in page.joined for p in spec.get("uncertain_if", []) for page in pages)
        if len(candidates) == 1 and not hedged:
            fields[name], status[name] = candidates[0], ("uncertain" if from_ocr else "found")
        elif candidates or unreadable or hedged:
            fields[name], status[name] = None, "uncertain"
        else:
            fields[name], status[name] = None, "missing"
    return {"fields": fields, "field_status": status}
