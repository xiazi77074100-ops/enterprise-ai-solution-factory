"""Structural check of an uploaded file, run in a child process (ADR-003, upload-and-files.md).

Native parsers (pdfium, Pillow's decoders) only ever see uploaded bytes inside the child started by
`LocalHandler`, so a hang or crash is a timeout/crash result there, not a broken API process. The result is a
status code and the page count; nothing from the document's contents crosses back.
"""

import io
import warnings
from typing import Any

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
from PIL import Image, UnidentifiedImageError

from app.capabilities.pdf_text import MAX_PAGES

MAX_IMAGE_PIXELS = 40_000_000  # A4 at 600 dpi is about 35 M pixels
PIL_FORMATS = {"image/png": "PNG", "image/jpeg": "JPEG"}


def inspect_document(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    data: bytes = inputs["data"]
    if inputs["media_type"] == "application/pdf":
        return _inspect_pdf(data)
    return _inspect_image(data, PIL_FORMATS[inputs["media_type"]])


def _inspect_pdf(data: bytes) -> dict[str, Any]:
    try:
        document = pdfium.PdfDocument(data)
    except pdfium.PdfiumError as exc:
        return {"status": "encrypted" if exc.err_code == pdfium_c.FPDF_ERR_PASSWORD else "unreadable"}
    try:
        if pdfium_c.FPDF_GetSecurityHandlerRevision(document.raw) != -1:
            return {"status": "encrypted"}
        javascript = pdfium_c.FPDFDoc_GetJavaScriptActionCount(document.raw)
        if javascript < 0:
            return {"status": "unreadable"}
        if javascript > 0 or document.count_attachments() > 0:
            return {"status": "active_content"}
        pages = len(document)
        if pages == 0:
            return {"status": "unreadable"}
        if pages > MAX_PAGES:
            return {"status": "too_many_pages"}
        return {"status": "ok", "page_count": pages}
    finally:
        document.close()


def _inspect_image(data: bytes, pil_format: str) -> dict[str, Any]:
    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data), formats=[pil_format]) as image:  # reads the header only
                width, height = image.size
                if width * height > MAX_IMAGE_PIXELS:
                    return {"status": "too_many_pixels"}
                image.verify()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        return {"status": "too_many_pixels"}
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        return {"status": "unreadable"}
    return {"status": "ok", "page_count": 1}
