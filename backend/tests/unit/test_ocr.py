"""P3-04 OCR (D-033). Images are drawn here with the repository's OFL font; no dev or holdout document is used.

Tests that need the Tesseract binary are skipped where it is not installed (Windows development); CI and the
container install it.
"""

import io
import shutil
from pathlib import Path
from typing import Any

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.capabilities import ocr
from app.capabilities.document_parser import parse_document
from app.capabilities.evidence import locate
from app.capabilities.rule_extractor import extract_by_labels

FONT = Path(__file__).resolve().parents[3] / "fixtures" / "generator" / "fonts" / "BIZUDPGothic-Regular.ttf"
LINES = ["請求書番号：2025-0001", "合計金額：¥104,060", "TEST ONLY"]
needs_tesseract = pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract is not installed")


def _page_image() -> Image.Image:
    image = Image.new("L", (1700, 600), 255)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(FONT), 56)
    for i, line in enumerate(LINES):
        draw.text((80, 80 + i * 140), line, font=font, fill=0)
    return image


def _bytes(image: Image.Image, fmt: str) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format=fmt)
    return buf.getvalue()


def _parse(data: bytes, media_type: str, mode: str) -> dict[str, Any]:
    return parse_document({"data": data, "media_type": media_type, "document_id": "d", "sha256": "h"}, {"ocr": mode})


@needs_tesseract
@pytest.mark.parametrize(
    ("fmt", "media_type"), [("PNG", "image/png"), ("JPEG", "image/jpeg"), ("PDF", "application/pdf")]
)
def test_ocr_reads_images_and_pdf_pages_without_a_text_layer(fmt: str, media_type: str) -> None:
    out = _parse(_bytes(_page_image(), fmt), media_type, "tesseract")
    (page,) = out["pages"]
    assert page["extraction_method"] == "ocr_tesseract"
    compact = page["text"].replace(" ", "")
    assert "2025-0001" in compact and "104" in compact  # "¥104,060" itself is often misread (e.g. "\104,.060")
    fields = extract_by_labels(
        {"document_id": "d", "pages": out["pages"]},
        {"field_spec": [{"name": "invoice_no", "type": "string", "label_ja": "番号", "critical": True,
                         "labels": ["請求書番号"]}]},
    )  # fmt: skip
    assert fields["fields"]["invoice_no"] == "2025-0001"
    assert fields["field_status"]["invoice_no"] == "uncertain"  # OCR values are drafts, never "found" (D-034)


def test_pdf_pages_with_a_text_layer_are_not_ocred() -> None:
    pdf = (Path(__file__).resolve().parents[3] / "fixtures" / "dev" / "documents" / "inv-0001.pdf").read_bytes()
    out = _parse(pdf, "application/pdf", "tesseract")  # needs no binary: the page has text
    assert {p["extraction_method"] for p in out["pages"]} == {"text_layer"}


def test_without_ocr_an_image_is_an_empty_page() -> None:
    out = _parse(_bytes(_page_image(), "PNG"), "image/png", "none")
    assert out["pages"] == [{"page": 1, "text": "", "extraction_method": "text_layer"}]


def test_missing_binary_and_llm_ocr_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(ocr.OcrUnavailableError):
        _parse(_bytes(_page_image(), "PNG"), "image/png", "tesseract")
    with pytest.raises(NotImplementedError):
        _parse(_bytes(_page_image(), "PNG"), "image/png", "llm")


def test_evidence_in_ocr_text_is_never_verified() -> None:
    text = "請求書番号：2025-0001"
    pages = [
        {"page": 1, "text": text, "extraction_method": "ocr_tesseract"},
        {"page": 2, "text": text, "extraction_method": "text_layer"},
    ]
    spans = locate("d", pages, {"invoice_no": "2025-0001"}, "normalized")["evidence"]["invoice_no"]
    assert [(s["page"], s["status"]) for s in spans] == [(1, "unverified"), (2, "verified")]


def test_ocr_text_is_normalized() -> None:
    # Tesseract 5.5 (Alpine) output seen in the container for a self-drawn "請求書番号：2025-0001".
    assert ocr.normalize("請 求 書 番 号 :②0②⑤-000①\f\n") == "請求書番号 :2025-0001"
    assert ocr.normalize("合計 金額 : 104,060\nTEST ONLY") == "合計金額 : 104,060\nTEST ONLY"


def test_values_from_ocr_pages_are_never_found() -> None:
    pages = [{"page": 1, "text": "合計金額：\\104,.060", "extraction_method": "ocr_tesseract"}]
    spec = [{"name": "total", "type": "decimal", "label_ja": "合計", "critical": True, "labels": ["合計金額"]}]
    out = extract_by_labels({"document_id": "d", "pages": pages}, {"field_spec": spec})
    assert out["field_status"]["total"] == "uncertain"  # a misread "104" must not look confirmed
