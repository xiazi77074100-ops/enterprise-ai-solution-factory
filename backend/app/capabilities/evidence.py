"""Evidence location (easf-capability-contract §1-6): where an extracted value is printed in the page text.

Evidence is never invented: a span is returned only when the page text at [start, end) is one of the printed
forms of the value, and it carries the SHA-256 of exactly those characters. A value with no such span gets no
evidence (shown as unconfirmed). Offsets index the parser's page texts (app/capabilities/pdf_text.py).
A span found in OCR text is `unverified` (ADR-003): the OCR text is not the document's own text layer.
"""

from typing import Any

from app.capabilities.pdf_text import span_sha256
from app.capabilities.values import amount_forms, date_forms, nfkc

MAX_SPANS = 10  # output_schema: evidence[name] maxItems
MIN_CHARS = 2  # a single character would match almost anywhere


def _forms(value: Any, match: str) -> list[str]:
    if isinstance(value, bool) or value is None:
        return []
    text = str(value)
    if match == "exact":
        return [text]
    forms = [text, nfkc(text), *date_forms(text), *amount_forms(text)]
    return sorted({f for f in forms if len(f) >= MIN_CHARS}, key=len, reverse=True)  # longest first


def _status(page: dict[str, Any]) -> str:
    return "verified" if page.get("extraction_method") == "text_layer" else "unverified"


def _whole_number(text: str, start: int, end: int) -> bool:
    """A span must not cut a number: "¥1" inside "¥104,060" or "4600" inside "94600" is not evidence."""
    before = text[start - 1] if start > 0 else ""
    after = text[end : end + 2]
    if text[start].isdigit() and before.isdigit():
        return False
    return not (text[end - 1].isdigit() and (after[:1].isdigit() or (after[:1] in ",." and after[1:2].isdigit())))


def locate(document_id: str, pages: list[dict[str, Any]], fields: dict[str, Any], match: str) -> dict[str, Any]:
    evidence: dict[str, list[dict[str, Any]]] = {}
    for name, value in fields.items():
        spans: list[dict[str, Any]] = []
        taken: list[tuple[int, int, int]] = []
        for form in _forms(value, match):
            for page in pages:
                text, start = page["text"], 0
                while len(spans) < MAX_SPANS and (start := text.find(form, start)) != -1:
                    end = start + len(form)
                    overlaps = any(p == page["page"] and s < end and start < e for p, s, e in taken)
                    if not overlaps and _whole_number(text, start, end):
                        taken.append((page["page"], start, end))
                        spans.append(
                            {"document_id": document_id, "page": page["page"], "start": start, "end": end,
                             "text_sha256": span_sha256(text, start, end), "status": _status(page)}
                        )  # fmt: skip
                    start = end
        evidence[name] = sorted(spans, key=lambda s: (s["page"], s["start"]))
    return {"evidence": evidence}
