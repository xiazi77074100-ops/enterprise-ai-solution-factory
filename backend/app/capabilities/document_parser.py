"""document_parser.v1 (local): page texts of a stored document (ADR-003, D-028, D-033).

Runs in the child process. The worker-side handler (app/adapters/resources.py) resolves `document_ref` to the
stored bytes; this function only sees bytes and returns the page texts that evidence offsets index into.
With `ocr: tesseract`, images and PDF pages without a text layer are read by OCR (`ocr_tesseract`). With
`ocr: none` they stay empty, so the extractor reports their fields as missing and a person checks them.
`ocr: llm` is not available (D-004): the node fails instead of pretending.
"""

from typing import Any

import pypdfium2 as pdfium

from app.capabilities import ocr
from app.capabilities.pdf_text import page_texts

MAX_PAGE_CHARS = 50_000  # output_schema: pages[].text maxLength


def _render(data: bytes, index: int) -> Any:
    document = pdfium.PdfDocument(data)
    try:
        page = document[index]
        image = page.render(scale=ocr.RENDER_DPI / 72).to_pil()
        page.close()
        return image
    finally:
        document.close()


def _pages(data: bytes, media_type: str, mode: str) -> list[tuple[str, str]]:
    if mode == "llm":
        raise NotImplementedError("LLM OCR is not available (D-004)")
    if media_type != "application/pdf":
        return [(ocr.ocr_image_bytes(data), "ocr_tesseract")] if mode == "tesseract" else [("", "text_layer")]
    pages = []
    for index, text in enumerate(page_texts(data)):
        if mode == "tesseract" and not text.strip():
            pages.append((ocr.ocr_image(_render(data, index)), "ocr_tesseract"))
        else:
            pages.append((text, "text_layer"))
    return pages


def parse_document(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    pages = _pages(inputs["data"], inputs["media_type"], config.get("ocr", "none"))
    if any(len(text) > MAX_PAGE_CHARS for text, _ in pages):
        # Truncating would silently shift evidence offsets; fail instead (fail closed).
        raise ValueError("page text too long")
    return {
        "document_id": inputs["document_id"],
        "document_sha256": inputs["sha256"],
        "pages": [{"page": i + 1, "text": text, "extraction_method": method} for i, (text, method) in enumerate(pages)],
    }
