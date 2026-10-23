"""VA-G4-001：例外値を隠し、型とtrace_idによる追跡を維持する。"""

import json
import logging
from typing import NoReturn

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import StatementError
from starlette.types import Receive, Scope, Send

from app.core.middleware import SecurityMiddleware
from tests.conftest import make_settings


def _raise_error(kind: str, value: str) -> NoReturn:
    if kind == "chained":
        try:
            raise ValueError(value)
        except ValueError as exc:
            raise RuntimeError("TEST ONLY outer exception") from exc
    if kind == "database":
        # 例外の構成だけ。SQLの実行・DBへの接続はしない。
        raise StatementError("TEST ONLY database failure", "SELECT :value", {"value": value}, RuntimeError(value))
    raise RuntimeError(f"{value}\nTEST ONLY log continuation")


@pytest.mark.parametrize("kind", ["plain", "chained", "database"])
def test_unexpected_error_hides_values_and_keeps_trace(kind: str, caplog: pytest.LogCaptureFixture) -> None:
    marker = f"TEST_ONLY_SYNTHETIC_VALUE_{kind.upper()}"

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        message = await receive()
        _raise_error(kind, json.loads(message["body"])["value"])

    settings = make_settings(_env_file=None, database_url="TEST_ONLY_UNUSED_DATABASE_URL")
    client = TestClient(SecurityMiddleware(app, settings))
    try:
        with caplog.at_level(logging.ERROR, logger="easf.errors"):
            response = client.post("/api/v1/test-only", json={"value": marker})
    finally:
        client.close()

    records = [record for record in caplog.records if record.name == "easf.errors"]
    assert len(records) == 1
    record = records[0]
    rendered = logging.Formatter("%(levelname)s %(message)s").format(record)
    expected_type = "StatementError" if kind == "database" else "RuntimeError"

    assert marker not in rendered
    assert marker not in response.text
    assert "TEST ONLY outer exception" not in rendered
    assert "SELECT :value" not in rendered
    assert record.exc_info is None
    assert getattr(record, "error_type", None) == expected_type
    assert expected_type in rendered
    assert response.status_code == 500
    assert response.json()["code"] == "internal_error"
    trace_id = response.json()["trace_id"]
    assert len(trace_id) == 32
    assert getattr(record, "trace_id", None) == trace_id
    assert trace_id in rendered
    assert response.headers["x-trace-id"] == trace_id
    assert response.headers["cache-control"] == "no-store"
