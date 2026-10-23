"""実ミドルウェアに合成例外を渡す。DB・ネットワーク・環境ファイルを使わない。"""

import argparse
import asyncio
import json
import logging
import secrets
from collections.abc import Callable
from pathlib import Path

from app.core.config import Settings
from app.core.errors import trace_id_var
from app.core.middleware import SecurityMiddleware
from sqlalchemy.exc import StatementError
from starlette.types import Message, Receive, Scope, Send

OUT = Path(__file__).resolve().parent


class Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []
        self.context_ids: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)
        self.context_ids.append(trace_id_var.get())


def plain(value: str) -> None:
    raise RuntimeError(f"TEST_ONLY exception value={value}\nTEST_ONLY log continuation")


def chained(value: str) -> None:
    try:
        raise ValueError(value)
    except ValueError as exc:
        raise RuntimeError("TEST_ONLY outer error") from exc


def database(value: str) -> None:
    # SQLAlchemy例外の文字列化だけ。SQLは実行せず、接続もしない。
    raise StatementError(
        "TEST_ONLY database failure",
        "SELECT :value",
        {"value": value},
        RuntimeError(value),
    )


async def check(
    case: str, fail: Callable[[str], None]
) -> tuple[dict[str, object], str]:
    marker = f"TEST_ONLY_SYNTHETIC_VALUE_{case.upper()}"
    body = json.dumps({"value": marker}).encode()
    messages: list[Message] = []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        request = await receive()
        value = json.loads(request["body"])["value"]
        fail(value)

    async def receive() -> Message:
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: Message) -> None:
        messages.append(message)

    settings = Settings(
        _env_file=None,
        env="test",
        database_url="TEST_ONLY_UNUSED_DATABASE_URL",
        secret_key=secrets.token_hex(32),
        max_request_bytes=1024,
        cookie_secure=True,
        hsts_enabled=True,
    )
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/test-only",
        "raw_path": b"/api/v1/test-only",
        "query_string": b"",
        "headers": [(b"content-type", b"application/json")],
    }
    capture = Capture()
    logger = logging.getLogger("easf.errors")
    previous = logger.handlers[:], logger.level, logger.propagate, logger.disabled
    before_trace = trace_id_var.get()
    try:
        logger.handlers = [capture]
        logger.setLevel(logging.ERROR)
        logger.propagate = False
        logger.disabled = False
        await SecurityMiddleware(app, settings)(scope, receive, send)
    finally:
        logger.handlers, level, logger.propagate, logger.disabled = previous
        logger.setLevel(level)
    text = "\n".join(
        logging.Formatter("%(levelname)s %(message)s").format(r)
        for r in capture.records
    )
    start = next(m for m in messages if m["type"] == "http.response.start")
    response = b"".join(
        m.get("body", b"") for m in messages if m["type"] == "http.response.body"
    ).decode()
    parsed = json.loads(response)
    expected_type = "StatementError" if case == "database" else "RuntimeError"
    return {
        "case": case,
        "http_status": start["status"],
        "response_code": parsed["code"],
        "synthetic_value_in_log": marker in text,
        "synthetic_value_in_response": marker in response,
        "record_count": len(capture.records),
        "error_type_matches_expected": all(
            getattr(r, "error_type", None) == expected_type for r in capture.records
        ),
        "exception_attached": any(r.exc_info is not None for r in capture.records),
        "structured_trace_id_present": all(
            hasattr(r, "trace_id") for r in capture.records
        ),
        "structured_trace_matches_response": all(
            getattr(r, "trace_id", None) == parsed["trace_id"] for r in capture.records
        ),
        "response_trace_matches_capture_context": capture.context_ids
        == [parsed["trace_id"]],
        "trace_context_restored": trace_id_var.get() == before_trace,
    }, text


async def main(label: str) -> int:
    rows = []
    logs = []
    for case, fail in {
        "plain": plain,
        "chained": chained,
        "database": database,
    }.items():
        result, log = await check(case, fail)
        rows.append(result)
        logs.append(f"=== TEST ONLY {case} ===\n{log}\n")
    output = {
        "source_commit": "fe581a5d84f0581712fe71afa8f68d9126c9bd54",
        "label": label,
        "cases": rows,
    }
    (OUT / f"{label}-result.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / f"{label}-synthetic-logs.txt").write_text("\n".join(logs), encoding="utf-8")
    unsafe = any(
        row["synthetic_value_in_log"]
        or row["synthetic_value_in_response"]
        or row["http_status"] != 500
        or row["response_code"] != "internal_error"
        or row["record_count"] != 1
        or not row["error_type_matches_expected"]
        or not row["structured_trace_matches_response"]
        or not row["trace_context_restored"]
        for row in rows
    )
    return 1 if unsafe else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--label", choices=("baseline", "candidate"), default="baseline"
    )
    raise SystemExit(asyncio.run(main(parser.parse_args().label)))
