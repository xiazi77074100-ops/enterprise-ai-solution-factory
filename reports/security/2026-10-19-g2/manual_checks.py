"""Manual upload checks E-01..E-04 against the assessment container (127.0.0.1:8001). Prints one line per check."""

import io
import struct
import sys
import zlib
from pathlib import Path

import httpx2 as httpx
import pypdfium2 as pdfium

BASE = "http://127.0.0.1:8001"
ORIGIN = {"Origin": "http://localhost:5173"}
ROOT = Path(sys.argv[2])
PDF = (ROOT / "fixtures/dev/documents/inv-0001.pdf").read_bytes()
PNG = (ROOT / "fixtures/dev/documents/inv-0008.png").read_bytes()

c = httpx.Client(base_url=BASE, timeout=60)
r = c.post("/api/v1/session", json={"login_id": "assess_admin", "password": sys.argv[1]}, headers=ORIGIN)
assert r.status_code == 200, r.text
H = {**ORIGIN, "X-CSRF-Token": r.json()["csrf_token"]}
project = c.post("/api/v1/projects", json={"name": "diag", "business_domain": "diag"}, headers=H).json()["id"]
URL = f"/api/v1/projects/{project}/documents"


def up(name, data, ctype, fields=None):
    return c.post(URL, files={"file": (name, data, ctype)}, data=fields or {"data_origin": "synthetic"}, headers=H)


def pages(n):
    d = pdfium.PdfDocument.new()
    for _ in range(n):
        d.new_page(100, 100)
    b = io.BytesIO()
    d.save(b)
    return b.getvalue()


def chunk(t, data):
    return struct.pack(">I", len(data)) + t + data + struct.pack(">I", zlib.crc32(t + data))


bomb = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 30000, 30000, 8, 0, 0, 0, 0)) + chunk(
    b"IDAT", zlib.compress(b"\0" * 10)
) + chunk(b"IEND", b"")
deep = b"%PDF-1.4\n1 0 obj " + b"[" * 100000 + b"]" * 100000 + b" endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n"
flate_bomb = b"%PDF-1.4\n1 0 obj << /Length 0 /Filter /FlateDecode >> stream\n" + zlib.compress(b"\0" * 50_000_000, 9) + b"\nendstream endobj\ntrailer << >>\n%%EOF\n"

checks = [
    ("E-01 HTML named .pdf", up("x.pdf", b"<html><script>alert(1)</script></html>", "application/pdf"), 415),
    ("E-01 SVG named .png", up("x.png", b"<svg xmlns='http://www.w3.org/2000/svg' onload='alert(1)'/>", "image/png"), 415),
    ("E-01 EXE named .pdf", up("x.pdf", b"MZ\x90\x00" + b"\0" * 100, "application/pdf"), 415),
    ("E-01 PDF declared as text/html", up("x.pdf", PDF, "text/html"), 415),
    ("E-01 PNG with .jpg extension", up("x.jpg", PNG, "image/jpeg"), 415),
    ("E-01 .html extension", up("x.html", PDF, "application/pdf"), 415),
    ("E-02 exactly 10 MB (PDF + padding)", up("max.pdf", PDF + b"\0" * (10 * 1024 * 1024 - len(PDF)), "application/pdf"), 201),
    ("E-02 10 MB + 1 byte", up("over.pdf", PDF + b"\0" * (10 * 1024 * 1024 + 1 - len(PDF)), "application/pdf"), 413),
    ("E-02 30 pages", up("p30.pdf", pages(30), "application/pdf"), 201),
    ("E-02 31 pages", up("p31.pdf", pages(31), "application/pdf"), 422),
    ("E-03 30000x30000 PNG header", up("bomb.png", bomb, "image/png"), 422),
    ("E-03 deeply nested PDF", up("deep.pdf", deep, "application/pdf"), 422),
    ("E-03 flate bomb PDF", up("flate.pdf", flate_bomb, "application/pdf"), 422),
    ("A-07 extra form field", up("a.pdf", PDF, "application/pdf", {"data_origin": "synthetic", "project_id": project}), 422),
    ("A-07 data_origin=real", up("a.pdf", PDF, "application/pdf", {"data_origin": "real"}), 422),
    ("D-01 upload without CSRF", c.post(URL, files={"file": ("a.pdf", PDF, "application/pdf")}, data={"data_origin": "synthetic"}, headers=ORIGIN), 403),
]
for label, res, want in checks:
    print(f"{'OK ' if res.status_code == want else 'NG '} {label}: {res.status_code} (expected {want}) {res.text[:80] if res.status_code >= 400 else ''}")

ok = up("請求書\r\nX-Evil: 1.pdf", PDF, "application/pdf")
doc = ok.json()
d = c.get(f"/api/v1/documents/{doc['id']}/content")
print("E-04 download status", d.status_code, "| CD:", d.headers.get("content-disposition"), "| nosniff:", d.headers.get("x-content-type-options"), "| cache:", d.headers.get("cache-control"), "| type:", d.headers.get("content-type"), "| same bytes:", d.content == PDF)
print("E-04 header injection absent:", "x-evil" not in d.headers)
for path in ("/data/documents/", f"/data/documents/{doc['id']}", "/var/documents/", f"/documents/{doc['id']}", f"/api/v1/documents/{doc['id']}"):
    print("E-04 not served:", path, c.get(path).status_code)
print("E-04 traversal in id:", c.get("/api/v1/documents/..%2F..%2Fetc%2Fpasswd/content").status_code)
anon = httpx.Client(base_url=BASE).get(f"/api/v1/documents/{doc['id']}/content")
print("C-01 anonymous download:", anon.status_code)
print("health after uploads:", c.get("/health").status_code)
