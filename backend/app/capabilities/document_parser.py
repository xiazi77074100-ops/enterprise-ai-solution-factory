"""document_parser.v1 (local): page texts of a stored document (ADR-003, D-028).

Runs in the child process. The worker-side handler (app/adapters/resources.py) resolves `document_ref` to the
stored bytes; this function only sees bytes and returns the page texts that evidence offsets index into.
OCR is not available in the POC: an image (or a PDF page without a text layer) yields an empty text, so the
extractor reports its fields as missing and the run goes to human review.
"""

from typing import Any

from app.capabilities.pdf_text import page_texts

MAX_PAGE_CHARS = 50_000  # output_schema: pages[].text maxLength


def parse_document(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    # Images have no text layer and the POC has no OCR engine (docs/design/detail/capabilities.md).
    texts = page_texts(inputs["data"]) if inputs["media_type"] == "application/pdf" else [""]
    if any(len(text) > MAX_PAGE_CHARS for text in texts):
        # Truncating would silently shift evidence offsets; fail instead (fail closed).
        raise ValueError("page text too long")
    return {
        "document_id": inputs["document_id"],
        "document_sha256": inputs["sha256"],
        "pages": [{"page": i + 1, "text": text, "extraction_method": "text_layer"} for i, text in enumerate(texts)],
    }
