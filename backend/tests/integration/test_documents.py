"""Documents API (P3-01a): upload checks, storage and download (jp-vuln-assessment E-01〜E-04, upload-and-files.md)."""

import hashlib
import io
import struct
import uuid
import zlib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import pypdfium2 as pdfium
import pytest
from fastapi.testclient import TestClient
from httpx import Response
from PIL import Image
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.documents.storage import MAX_DOCUMENT_BYTES
from app.executor.engine import _check_inputs
from tests.conftest import STORAGE_DIR
from tests.integration.test_auth_projects import (  # noqa: F401  # shared fixtures
    ORIGIN,
    db,
    login,
    make_user,
    migrated,
    new_client,
)

pytestmark = pytest.mark.db
DEV_DOCUMENTS = Path(__file__).resolve().parents[3] / "fixtures" / "dev" / "documents"
PDF = (DEV_DOCUMENTS / "inv-0001.pdf").read_bytes()
PNG = (DEV_DOCUMENTS / "inv-0008.png").read_bytes()


def _jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), "white").save(buf, format="JPEG")
    return buf.getvalue()


def _pdf_pages(count: int) -> bytes:
    document = pdfium.PdfDocument.new()
    for _ in range(count):
        document.new_page(100, 100)
    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()


def _pdf_with_attachment() -> bytes:
    document = pdfium.PdfDocument.new()
    document.new_page(100, 100)
    document.new_attachment("note.txt").set_data(b"hello")
    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()


def _encrypted_pdf() -> bytes:
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, encrypt="secret")
    pdf.drawString(10, 10, "TEST ONLY")
    pdf.showPage()
    pdf.save()
    return buf.getvalue()


JAVASCRIPT_PDF = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R /Names << /JavaScript 4 0 R >> >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] >> endobj
4 0 obj << /Names [(a) 5 0 R] >> endobj
5 0 obj << /S /JavaScript /JS (app.alert(1)) >> endobj
trailer << /Root 1 0 R >>
%%EOF
"""


def _png_header_only(width: int, height: int) -> bytes:
    """A PNG whose header claims a huge image (decompression bomb shape) with almost no data."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(b"\0" * 10)) + chunk(b"IEND", b"")


@dataclass
class Env:
    project_id: str
    other_project_id: str
    lead: tuple[TestClient, dict[str, str]]
    other: tuple[TestClient, dict[str, str]]


@pytest.fixture
def setup(db: Session, db_url: str) -> Env:  # noqa: F811
    users = {name: make_user(db, name) for name in ("lead", "arch", "reviewer", "other")}
    admin_user = make_user(db, "admin", admin=True)
    admin = new_client(db_url)
    admin_headers = login(admin, "admin")
    ids = {}
    for name, members in (
        ("文書", {"lead": "solution_lead", "arch": "solution_architect", "reviewer": "business_reviewer"}),
        ("別案件", {"other": "solution_lead"}),
    ):
        created = admin.post("/api/v1/projects", json={"name": name, "business_domain": "経理"}, headers=admin_headers)
        ids[name] = created.json()["id"]
        body = [{"user_id": str(admin_user.id), "roles": ["solution_lead"]}] + [
            {"user_id": str(users[u].id), "roles": [role]} for u, role in members.items()
        ]
        put = admin.put(f"/api/v1/projects/{ids[name]}/members", json=body, headers=admin_headers)
        assert put.status_code == 200, put.text
    lead, other = new_client(db_url), new_client(db_url)
    lead_headers, other_headers = login(lead, "lead"), login(other, "other")
    project_id = ids["文書"]
    return Env(project_id, ids["別案件"], (lead, lead_headers), (other, other_headers))


def _upload(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    name: str,
    data: bytes,
    content_type: str,
    fields: dict[str, str] | None = None,
) -> Response:
    form = {"data_origin": "synthetic"} if fields is None else fields
    res: Response = client.post(
        f"/api/v1/projects/{project_id}/documents",
        files={"file": (name, data, content_type)},
        data=form,
        headers=headers,
    )
    return res


def test_upload_list_and_download_round_trip(setup: Env) -> None:
    client, headers = setup.lead
    project_id = setup.project_id
    res = _upload(client, headers, project_id, "請求書 0001.pdf", PDF, "application/pdf")
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["display_name"] == "請求書 0001.pdf"
    assert body["media_type"] == "application/pdf"
    assert body["size_bytes"] == len(PDF)
    assert body["page_count"] >= 1
    assert body["sha256"] == hashlib.sha256(PDF).hexdigest()
    assert body["data_origin"] == "synthetic"

    for name, data, media in (("scan.png", PNG, "image/png"), ("photo.JPG", _jpeg(), "image/jpeg")):
        uploaded = _upload(client, headers, project_id, name, data, media)
        assert uploaded.status_code == 201, uploaded.text
        assert uploaded.json()["page_count"] == 1

    listed = client.get(f"/api/v1/projects/{project_id}/documents?limit=2")
    assert listed.status_code == 200
    assert listed.json()["page"]["total"] == 3
    assert len(listed.json()["items"]) == 2
    assert listed.json()["page"]["next_cursor"]

    download = client.get(f"/api/v1/documents/{body['id']}/content")
    assert download.status_code == 200
    assert download.content == PDF
    assert download.headers["content-type"] == "application/pdf"
    assert download.headers["x-content-type-options"] == "nosniff"
    assert download.headers["cache-control"] == "no-store"
    disposition = download.headers["content-disposition"]
    assert disposition.startswith("attachment; ")
    assert f"filename*=UTF-8''{quote('請求書 0001.pdf', safe='')}" in disposition

    # Stored under a server-generated name only; the user's file name never reaches the file system.
    stored = [p.name for p in Path(STORAGE_DIR).iterdir()]
    assert all(len(n) == 32 and all(c in "0123456789abcdef" for c in n) for n in stored)


@pytest.mark.parametrize(
    ("name", "data", "content_type"),
    [
        ("png-as.pdf", PNG, "application/pdf"),  # magic bytes disagree with the extension
        ("pdf-as.png", PDF, "image/png"),
        ("real.pdf", PDF, "image/png"),  # declared type disagrees
        ("real.pdf", PDF, "application/octet-stream"),
        ("page.html", b"<html><script>alert(1)</script>", "text/html"),
        ("image.svg", b"<svg xmlns='http://www.w3.org/2000/svg'/>", "image/svg+xml"),
        ("tool.exe", b"MZ\x90\x00", "application/octet-stream"),
        ("no-extension", PDF, "application/pdf"),
        ("double.pdf.exe", PDF, "application/pdf"),
    ],
    ids=lambda v: v if isinstance(v, str) else "",
)
def test_spoofed_or_unsupported_types_are_415(setup: Env, name: str, data: bytes, content_type: str) -> None:
    client, headers = setup.lead
    res = _upload(client, headers, setup.project_id, name, data, content_type)
    assert res.status_code == 415, res.text
    assert res.json()["code"] == "unsupported_media_type"


@pytest.mark.parametrize(
    ("name", "data", "content_type", "code"),
    [
        ("pages.pdf", _pdf_pages(31), "application/pdf", "too_many_pages"),
        ("locked.pdf", _encrypted_pdf(), "application/pdf", "document_encrypted"),
        ("script.pdf", JAVASCRIPT_PDF, "application/pdf", "document_active_content"),
        ("attached.pdf", _pdf_with_attachment(), "application/pdf", "document_active_content"),
        ("broken.pdf", b"%PDF-1.4 not really a pdf", "application/pdf", "document_unreadable"),
        ("bomb.png", _png_header_only(20000, 20000), "image/png", "image_too_large"),
        ("cut.png", PNG[:5000], "image/png", "document_unreadable"),
        ("empty.pdf", b"", "application/pdf", "document_empty"),
    ],
    ids=lambda v: v if isinstance(v, str) else "",
)
def test_unsafe_or_unreadable_content_is_422(setup: Env, name: str, data: bytes, content_type: str, code: str) -> None:
    client, headers = setup.lead
    res = _upload(client, headers, setup.project_id, name, data, content_type)
    assert res.status_code == 422, res.text
    assert res.json()["code"] == code


def test_size_limits_are_413(setup: Env) -> None:
    client, headers = setup.lead
    project_id = setup.project_id
    just_over = PDF + b"\0" * (MAX_DOCUMENT_BYTES + 1 - len(PDF))
    res = _upload(client, headers, project_id, "big.pdf", just_over, "application/pdf")
    assert res.status_code == 413
    assert res.json()["code"] == "document_too_large"
    # Far beyond the limit: refused by the middleware before the form is parsed.
    huge = _upload(client, headers, project_id, "huge.pdf", PDF + b"\0" * (MAX_DOCUMENT_BYTES * 2), "application/pdf")
    assert huge.status_code == 413
    assert huge.json()["code"] == "payload_too_large"
    # Other routes keep the 1 MB request limit.
    other = client.post("/api/v1/projects", content=b"{" + b" " * 2_000_000 + b"}", headers=headers)
    assert other.status_code == 413
    assert client.get(f"/api/v1/projects/{project_id}/documents").json()["page"]["total"] == 0


@pytest.mark.parametrize(
    "fields",
    [
        {"data_origin": "real"},
        {},
        {"data_origin": "synthetic", "owner_id": str(uuid.uuid4())},  # mass assignment
    ],
)
def test_form_fields_are_strict(setup: Env, fields: dict[str, str]) -> None:
    client, headers = setup.lead
    res = _upload(client, headers, setup.project_id, "a.pdf", PDF, "application/pdf", fields)
    assert res.status_code == 422, res.text


def test_missing_or_repeated_file_is_422(setup: Env) -> None:
    client, headers = setup.lead
    url = f"/api/v1/projects/{setup.project_id}/documents"
    assert client.post(url, data={"data_origin": "synthetic"}, headers=headers).status_code == 422
    two = [("file", ("a.pdf", PDF, "application/pdf")), ("file", ("b.pdf", PDF, "application/pdf"))]
    assert client.post(url, files=two, data={"data_origin": "synthetic"}, headers=headers).status_code == 422
    assert client.post(url, json={"data_origin": "synthetic"}, headers=headers).status_code == 422


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("../../etc/passwd.pdf", "passwd.pdf"),
        ("C:\\Windows\\system32\\a.pdf", "a.pdf"),
        ("evil\x07\x1b[31m\x7f.pdf", "evil[31m.pdf"),  # control characters removed
        ("invoice\u202efdp.pdf", "invoicefdp.pdf"),  # right-to-left override removed
        ("ｶﾞ.pdf", "ｶﾞ.pdf"),
        ("e\u0301.pdf", "\u00e9.pdf"),  # NFC
    ],
)
def test_file_names_are_display_strings_only(setup: Env, raw: str, expected: str) -> None:
    client, headers = setup.lead
    # Built by hand: httpx would percent-encode control characters in the file name.
    boundary = "easf-test-boundary"
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="data_origin"\r\n\r\nsynthetic\r\n'
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{raw}"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
    )
    body = head.encode() + PDF + f"\r\n--{boundary}--\r\n".encode()
    res = client.post(
        f"/api/v1/projects/{setup.project_id}/documents",
        content=body,
        headers={**headers, "Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    assert res.status_code == 201, res.text
    assert res.json()["display_name"] == expected
    download = client.get(f"/api/v1/documents/{res.json()['id']}/content")
    disposition = download.headers["content-disposition"]
    assert disposition.isascii() and disposition.isprintable()


def test_long_file_name_is_truncated(setup: Env) -> None:
    client, headers = setup.lead
    res = _upload(client, headers, setup.project_id, "あ" * 300 + ".pdf", PDF, "application/pdf")
    assert res.status_code == 201
    assert len(res.json()["display_name"]) == 255


def test_other_projects_documents_are_invisible(setup: Env) -> None:
    client, headers = setup.lead
    other, other_headers = setup.other
    mine = _upload(client, headers, setup.project_id, "mine.pdf", PDF, "application/pdf").json()
    assert other.get(f"/api/v1/documents/{mine['id']}/content").status_code == 404
    assert other.get(f"/api/v1/projects/{setup.project_id}/documents").status_code == 404
    refused = _upload(other, other_headers, setup.project_id, "x.pdf", PDF, "application/pdf")
    assert refused.status_code == 404
    assert other.get(f"/api/v1/documents/{uuid.uuid4()}/content").status_code == 404
    assert other.get("/api/v1/documents/not-a-uuid/content").status_code == 422


def test_upload_requires_csrf_token(setup: Env) -> None:
    client, _ = setup.lead
    res = _upload(client, dict(ORIGIN), setup.project_id, "a.pdf", PDF, "application/pdf")
    assert res.status_code == 403


def test_run_inputs_accept_only_documents_of_the_same_project(setup: Env, db: Session) -> None:  # noqa: F811
    client, headers = setup.lead
    other, other_headers = setup.other
    project_id = uuid.UUID(setup.project_id)
    mine = _upload(client, headers, str(project_id), "mine.pdf", PDF, "application/pdf").json()
    theirs = _upload(other, other_headers, setup.other_project_id, "theirs.pdf", PDF, "application/pdf").json()
    workflow = {"inputs": [{"name": "doc", "type": "document_ref"}]}
    _check_inputs(db, project_id, workflow, {"doc": mine["id"]})
    for value in (theirs["id"], str(uuid.uuid4()), "not-a-uuid", 1, True):
        with pytest.raises(ApiError) as caught:
            _check_inputs(db, project_id, workflow, {"doc": value})
        assert caught.value.status == 422
