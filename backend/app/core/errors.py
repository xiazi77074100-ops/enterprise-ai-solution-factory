"""One error shape for every failure: {code, message, trace_id, details}. Never echo input values or internals."""

import uuid
from contextvars import ContextVar
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="0" * 32)

_STATUS_DEFAULTS = {
    400: ("bad_request", "リクエストの形式が正しくありません。"),
    401: ("unauthenticated", "ログインしてください。"),
    403: ("forbidden", "この操作を行う権限がありません。"),
    404: ("not_found", "対象が見つかりません。"),
    405: ("method_not_allowed", "この操作は利用できません。"),
    413: ("payload_too_large", "送信データが大きすぎます。"),
    415: ("unsupported_media_type", "このファイル形式は利用できません。"),
    422: ("validation_error", "入力内容に誤りがあります。"),
    429: ("too_many_requests", "しばらく待ってからもう一度お試しください。"),
    503: ("service_unavailable", "現在利用できません。しばらく待ってからお試しください。"),
}


class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, details: list[dict[str, str]] | None = None):
        super().__init__(code)
        self.code, self.message, self.status, self.details = code, message, status, details or []


def new_trace_id() -> str:
    return uuid.uuid4().hex


def error_response(status: int, code: str, message: str, details: list[dict[str, str]] | None = None) -> JSONResponse:
    body: dict[str, Any] = {"code": code, "message": message, "trace_id": trace_id_var.get()}
    if details:
        body["details"] = details
    return JSONResponse(status_code=status, content=body)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return error_response(exc.status, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Field path and error type only; the default handler would echo the submitted value.
        details = [
            {"field": ".".join(str(p) for p in err.get("loc", ())), "reason": str(err.get("type", "invalid"))}
            for err in exc.errors()[:50]
        ]
        code, message = _STATUS_DEFAULTS[422]
        return error_response(422, code, message, details)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code, message = _STATUS_DEFAULTS.get(exc.status_code, ("error", "処理できませんでした。"))
        return error_response(exc.status_code, code, message)

    # Unexpected exceptions are turned into 500 by SecurityMiddleware so the response keeps the security headers.
