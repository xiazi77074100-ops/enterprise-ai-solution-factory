"""Render a Record as an A4 invoice PDF (ReportLab, embedded BIZ UDPGothic; D-028), and scans as PNG.

The renderer returns anchors (page, label, printed token) for every gold field. Gold evidence is then located in
the text extracted by app.capabilities.pdf_text — the same function the document parser uses — so offsets agree.
"""

import io
import random
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageFilter
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from fixtures.generator.invoice import Record, format_date, yen
from fixtures.generator.names import INJECTIONS

# Embedded (subset) so every OS renders the same pixels: scans are rasterized from the PDF (D-028 v2).
# BIZ UDPGothic, SIL OFL 1.1 (fonts/OFL.txt).
FONT = "BIZUDPGothic"
pdfmetrics.registerFont(TTFont(FONT, str(Path(__file__).with_name("fonts") / "BIZUDPGothic-Regular.ttf")))
WIDTH, HEIGHT = A4
LEFT, RIGHT = 56, WIDTH - 56
MARK = "TEST ONLY／合成データ（架空の請求書です。実在の取引ではありません）"


@dataclass(frozen=True)
class Anchor:
    field: str
    page: int  # 1-based
    label: str  # text printed just before the token on the same line
    token: str  # the value exactly as printed


class _Doc:
    def __init__(self) -> None:
        self.buffer = io.BytesIO()
        # invariant=1: no creation date or random document id, so the same record gives the same bytes.
        self.canvas = canvas.Canvas(self.buffer, pagesize=A4, invariant=1)
        self.page = 1
        self.y = HEIGHT - 60
        self.anchors: list[Anchor] = []
        self._footer()

    def _footer(self) -> None:
        self.canvas.setFont(FONT, 8)
        self.canvas.drawString(LEFT, 30, MARK)
        self.canvas.drawRightString(RIGHT, 30, f"{self.page} ページ")

    def new_page(self) -> None:
        self.canvas.showPage()
        self.page += 1
        self.y = HEIGHT - 60
        self._footer()

    def line(self, text: str, size: float = 10.5, x: float = LEFT, gap: float = 18) -> None:
        if self.y < 80:
            self.new_page()
        self.canvas.setFont(FONT, size)
        self.canvas.drawString(x, self.y, text)
        self.y -= gap

    def labeled(self, field: str | None, label: str, token: str, size: float = 10.5) -> None:
        """Prints "label token" on one line and records the anchor for a gold field."""
        if self.y < 80:
            self.new_page()
        self.line(f"{label}{token}", size)
        if field:
            self.anchors.append(Anchor(field, self.page, label, token))

    def row(self, cells: tuple[str, str, str, str], size: float = 9.5, gap: float = 15) -> None:
        """Table row: description left, quantity / unit price / amount right-aligned in fixed columns."""
        if self.y < 80:
            self.new_page()
        self.canvas.setFont(FONT, size)
        self.canvas.drawString(LEFT, self.y, cells[0])
        for x, text in zip((LEFT + 300, LEFT + 380, RIGHT - 20), cells[1:], strict=True):
            self.canvas.drawRightString(x, self.y, text)
        self.y -= gap

    def save(self) -> bytes:
        self.canvas.showPage()
        self.canvas.save()
        return self.buffer.getvalue()


def render_pdf(record: Record) -> tuple[bytes, list[Anchor]]:
    doc = _Doc()
    style = record.date_style
    doc.line("請求書", size=18, gap=30)
    doc.line(f"{record.customer} 御中", size=12, gap=24)
    doc.labeled("invoice_no", "請求書番号：", record.invoice_no)
    doc.labeled("issue_date", "請求日：", format_date(record.issue_date, style))
    doc.line("")
    doc.labeled("vendor_name", "発行者：", record.vendor.name, size=11)
    doc.line(record.vendor.address, size=9, gap=14)
    doc.line(f"TEL {record.vendor.phone}　担当 {record.contact}", size=9, gap=14)
    if record.registration_no is not None:
        doc.labeled("registration_no", "登録番号：", record.registration_no, size=9)
    doc.line("")
    doc.line("下記のとおりご請求申し上げます。", gap=24)

    doc.row(("品名", "数量", "単価", "金額"), gap=16)
    for item in record.items:
        doc.row((item["description"], str(item["quantity"]), yen(item["unit_price"]), yen(item["amount"])))
    if "duplicate_label" in record.plan.layout:
        doc.line(f"合計 {sum(i['quantity'] for i in record.items)} 点", size=9.5)
    if "multi_page" in record.plan.layout:
        doc.new_page()
        doc.line("（前ページからの続き）", size=9, gap=24)
    doc.line("")
    doc.labeled("subtotal", "小計：", yen(record.subtotal))
    doc.labeled("tax", f"消費税（{10}%）：", yen(record.tax))
    doc.labeled("total", "合計金額：", yen(record.total), size=12)
    if record.second_total is not None:
        # Ambiguous: a second, different "total". Gold total is uncertain; evidence lists both candidates.
        doc.labeled("total", "ご請求金額（税込・税抜は別紙参照）：", yen(record.second_total), size=11)
    doc.line("")
    if record.due_date is not None:
        doc.labeled("due_date", "お支払期日：", format_date(record.due_date, style))
    doc.labeled("payee_bank", "振込先：", record.vendor.bank.name)
    doc.labeled("payee_branch", "支店：", record.vendor.bank.branch)
    doc.labeled("payee_account", "口座（普通）：", record.payee_account)
    doc.line("振込手数料は貴社にてご負担ください。", size=9)
    if record.injection is not None:
        doc.line("")
        doc.line(INJECTIONS[record.injection], size=8.5)
    return doc.save(), doc.anchors


def render_scan(pdf: bytes, sample_id: str) -> bytes:
    """First page as a low-quality grayscale scan: slight rotation, blur and noise (D-005). Deterministic."""
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(pdf)
    try:
        image = document[0].render(scale=100 / 72).to_pil().convert("L")
    finally:
        document.close()
    rng = random.Random(f"scan:{sample_id}")  # noqa: S311  # reproducible synthetic noise, not security
    image = image.rotate(rng.uniform(-3, 3), resample=Image.Resampling.BILINEAR, expand=True, fillcolor=255)
    image = image.filter(ImageFilter.GaussianBlur(0.6))
    pixels = image.load()
    if pixels is None:
        raise RuntimeError("image has no pixel access")
    width, height = image.size
    for _ in range(width * height // 150):
        x, y = rng.randrange(width), rng.randrange(height)
        pixels[x, y] = rng.choice([0, 96, 160])
    return encode_png_gray(width, height, image.tobytes())


def encode_png_gray(width: int, height: int, raw: bytes) -> bytes:
    """8-bit grayscale PNG with uncompressed (stored) deflate blocks.

    zlib builds differ between platforms (Windows vs Linux wheels), so compressed PNG bytes differed for the same
    pixels. Stored blocks make the file a pure function of the pixels, keeping the recorded SHA-256 stable.
    """
    rows = b"".join(b"\x00" + raw[y * width : (y + 1) * width] for y in range(height))  # filter type 0 per row
    blocks = []
    for offset in range(0, len(rows), 65535):
        chunk = rows[offset : offset + 65535]
        final = 1 if offset + 65535 >= len(rows) else 0
        blocks.append(struct.pack("<BHH", final, len(chunk), len(chunk) ^ 0xFFFF) + chunk)
    deflate = b"\x78\x01" + b"".join(blocks) + struct.pack(">I", zlib.adler32(rows))

    def png_chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", header) + png_chunk(b"IDAT", deflate) + png_chunk(b"IEND", b"")
