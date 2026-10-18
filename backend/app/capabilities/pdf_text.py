"""Page text of a PDF's text layer (D-028). The single definition of "character offsets" in EASF.

The document parser returns exactly these strings, and evidence offsets (start, end) index into them. The
synthetic-data generator uses the same function to place gold evidence, so labels and parsing cannot drift.
"""

import hashlib

import pypdfium2 as pdfium

MAX_PAGES = 30


def page_texts(pdf: bytes) -> list[str]:
    """Text of each page (pdfium's reading order, CRLF line breaks). Raises ValueError if not a readable PDF."""
    try:
        document = pdfium.PdfDocument(pdf)
    except pdfium.PdfiumError as exc:
        raise ValueError("not a readable PDF") from exc
    try:
        if len(document) > MAX_PAGES:
            raise ValueError("too many pages")
        texts = []
        for index in range(len(document)):
            page = document[index]
            textpage = page.get_textpage()
            texts.append(textpage.get_text_bounded())
            textpage.close()
            page.close()
        return texts
    finally:
        document.close()


def span_sha256(text: str, start: int, end: int) -> str:
    """SHA-256 of a page text range (UTF-8). Evidence stores this to prove which characters it points at."""
    return hashlib.sha256(text[start:end].encode("utf-8")).hexdigest()
