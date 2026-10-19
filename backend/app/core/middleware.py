"""Outermost ASGI middleware: trace id, request size limit, unexpected-error handling and security headers.

It must produce every response itself when something goes wrong, so that 413 and 500 responses carry the same
security headers as normal ones (Starlette's own error middleware sits outside user middleware).
"""

import json
import logging
import re

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import Settings
from app.core.errors import new_trace_id, trace_id_var
from app.documents.storage import MAX_DOCUMENT_BYTES

logger = logging.getLogger("easf.errors")

CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; font-src 'self'; "
    "connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
)


# VA-004: PostgreSQL text/jsonb cannot store NUL, so reject it up front (422) instead of failing in the DB (500).
# In JSON a NUL is the escape \u0000 preceded by an even number of backslashes (\\u0000 is literal text).
_JSON_NUL = re.compile(rb"(?<!\\)(?:\\\\)*\\u0000")


# uploadDocument is the only request allowed past max_request_bytes: one 10 MB file plus the multipart framing.
# The handler enforces the exact file limit (MAX_DOCUMENT_BYTES).
_UPLOAD_PATH = re.compile(r"^/api/v1/projects/[^/]+/documents$")
UPLOAD_REQUEST_BYTES = MAX_DOCUMENT_BYTES + 64 * 1024


def _has_nul(scope: Scope, body: bytes) -> bool:
    for part in (scope.get("raw_path") or scope["path"].encode(), scope.get("query_string", b"")):
        if b"\x00" in part or b"%00" in part:
            return True
    if "\x00" in scope["path"]:
        return True
    content_type = dict(scope.get("headers", [])).get(b"content-type", b"")
    return content_type.startswith(b"application/json") and (b"\x00" in body or bool(_JSON_NUL.search(body)))


class SecurityMiddleware:
    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app = app
        self.limit = settings.max_request_bytes
        self.headers = [
            (b"content-security-policy", CSP.encode()),
            (b"x-frame-options", b"DENY"),
            (b"x-content-type-options", b"nosniff"),
            (b"referrer-policy", b"strict-origin-when-cross-origin"),
            (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
            (b"cross-origin-opener-policy", b"same-origin"),
            (b"cross-origin-resource-policy", b"same-origin"),  # VA-003 (ZAP 90004)
        ]
        if settings.hsts_enabled:
            self.headers.append((b"strict-transport-security", b"max-age=31536000; includeSubDomains"))

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        token = trace_id_var.set(new_trace_id())
        started = False
        send_with_headers = self._with_headers(scope, send)

        async def tracking_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send_with_headers(message)

        try:
            body = await self._read_body(scope, receive)
            if body is None:
                await self._json(send_with_headers, 413, "payload_too_large", "送信データが大きすぎます。")
                return
            if _has_nul(scope, body):
                await self._json(send_with_headers, 422, "validation_error", "入力内容に誤りがあります。")
                return
            await self.app(scope, _replay(body, receive), tracking_send)
        except Exception as exc:
            logger.error("unhandled exception", extra={"error_type": type(exc).__name__}, exc_info=exc)
            if not started:
                await self._json(
                    send_with_headers,
                    500,
                    "internal_error",
                    f"処理中にエラーが発生しました。（trace_id: {trace_id_var.get()}）",
                )
        finally:
            trace_id_var.reset(token)

    async def _read_body(self, scope: Scope, receive: Receive) -> bytes | None:
        """Read the whole body up to the limit (None when exceeded). Bounded by max_request_bytes (uploads: 10 MB)."""
        limit = self.limit
        if scope["method"] == "POST" and _UPLOAD_PATH.match(scope["path"]):
            limit = max(limit, UPLOAD_REQUEST_BYTES)
        declared = dict(scope.get("headers", [])).get(b"content-length")
        if declared is not None and (not declared.isdigit() or int(declared) > limit):
            return None
        chunks: list[bytes] = []
        size = 0
        while True:
            message = await receive()
            if message["type"] != "http.request":
                break
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > limit:
                return None
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        return b"".join(chunks)

    def _with_headers(self, scope: Scope, send: Send) -> Send:
        no_store = scope["path"].startswith("/api/")

        async def wrapped(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = [
                    (k, v) for k, v in message.get("headers", []) if k.lower() not in (b"server", b"x-powered-by")
                ]
                headers += self.headers
                headers.append((b"x-trace-id", trace_id_var.get().encode()))
                if no_store:
                    headers.append((b"cache-control", b"no-store"))
                message["headers"] = headers
            await send(message)

        return wrapped

    @staticmethod
    async def _json(send: Send, status: int, code: str, message: str) -> None:
        body = json.dumps(
            {"code": code, "message": message, "trace_id": trace_id_var.get()}, ensure_ascii=False
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
            }
        )
        await send({"type": "http.response.body", "body": body})


def _replay(body: bytes, receive: Receive) -> Receive:
    sent = False

    async def wrapped() -> Message:
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return await receive()  # http.disconnect after the body

    return wrapped
