"""jp-secure-coding: headers, error shape, information leakage, size limit (checklist F-01..F-06)."""

from collections.abc import Iterator

from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict

from app.main import create_app
from tests.conftest import make_settings

SECURITY_HEADERS = {
    "content-security-policy",
    "x-frame-options",
    "x-content-type-options",
    "referrer-policy",
    "permissions-policy",
    "cross-origin-opener-policy",
    "cross-origin-resource-policy",
    "x-trace-id",
}


def assert_error_shape(body: dict[str, object], code: str) -> None:
    assert body["code"] == code
    assert isinstance(body["message"], str) and body["message"]
    assert isinstance(body["trace_id"], str) and len(body["trace_id"]) == 32


def test_health_ok_with_security_headers(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
    assert set(res.headers) >= SECURITY_HEADERS
    assert "frame-ancestors 'none'" in res.headers["content-security-policy"]
    assert "unsafe-inline" not in res.headers["content-security-policy"]
    assert res.headers["x-frame-options"] == "DENY"


def test_no_server_or_framework_header(client: TestClient) -> None:
    res = client.get("/health")
    assert "server" not in res.headers
    assert "x-powered-by" not in res.headers


def test_unknown_path_returns_error_shape_with_headers(client: TestClient) -> None:
    res = client.get("/no-such-path")
    assert res.status_code == 404
    assert_error_shape(res.json(), "not_found")
    assert set(res.headers) >= SECURITY_HEADERS


def test_trace_method_not_allowed(client: TestClient) -> None:
    res = client.request("TRACE", "/health")
    assert res.status_code == 405
    assert_error_shape(res.json(), "method_not_allowed")


def test_docs_closed_outside_dev(client: TestClient) -> None:
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404


def test_docs_open_only_in_dev() -> None:
    dev = TestClient(create_app(make_settings(env="dev")))
    assert dev.get("/openapi.json").status_code == 200


def test_hsts_only_when_enabled(client: TestClient) -> None:
    assert "strict-transport-security" not in client.get("/health").headers
    https = TestClient(create_app(make_settings(hsts_enabled=True)))
    assert https.get("/health").headers["strict-transport-security"].startswith("max-age=")


class _Echo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str


def _app_with_echo() -> TestClient:
    app = create_app(make_settings(max_request_bytes=2048))
    router = APIRouter()

    @router.post("/api/v1/_echo")
    def echo(body: _Echo) -> dict[str, str]:
        return {"name": body.name}

    @router.get("/api/v1/_boom")
    def boom() -> None:
        raise RuntimeError("secret internal detail /etc/passwd")

    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


def test_validation_error_does_not_echo_input() -> None:
    res = _app_with_echo().post("/api/v1/_echo", json={"name": "ok", "role": "<script>admin</script>"})
    assert res.status_code == 422
    body = res.json()
    assert_error_shape(body, "validation_error")
    assert "<script>" not in res.text
    assert body["details"][0]["field"].endswith("role")


def test_internal_error_hides_details_and_api_is_no_store() -> None:
    res = _app_with_echo().get("/api/v1/_boom")
    assert res.status_code == 500
    assert_error_shape(res.json(), "internal_error")
    assert "passwd" not in res.text and "RuntimeError" not in res.text
    assert res.headers["cache-control"] == "no-store"


def test_body_over_limit_rejected_by_content_length() -> None:
    res = _app_with_echo().post(
        "/api/v1/_echo", content=b'{"name":"' + b"a" * 4096 + b'"}', headers={"content-type": "application/json"}
    )
    assert res.status_code == 413
    assert_error_shape(res.json(), "payload_too_large")
    assert set(res.headers) >= SECURITY_HEADERS


def test_body_over_limit_rejected_when_streamed() -> None:
    def chunks() -> Iterator[bytes]:  # no content-length header
        for _ in range(8):
            yield b"a" * 512

    res = _app_with_echo().post("/api/v1/_echo", content=chunks(), headers={"content-type": "application/json"})
    assert res.status_code == 413
