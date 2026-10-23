"""製品ASGIアプリの認証前の境界を確認する。DB・外部通信は使わない。"""

import asyncio
import json
import secrets
from pathlib import Path

from app.core.config import Settings
from app.main import create_app


async def main() -> None:
    settings = Settings(
        _env_file=None,
        env="assessment",
        database_url="postgresql+psycopg://unused@127.0.0.1:1/unused_test",
        secret_key=secrets.token_hex(32),
    )
    app = create_app(settings=settings)
    results = []
    for path, expected in (
        ("/health", 200),
        ("/docs", 404),
        ("/redoc", 404),
        ("/openapi.json", 404),
        ("/.env", 404),
        ("/.git/config", 404),
        ("/api/v1/projects", 401),
    ):
        messages = []

        async def receive() -> dict:
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict, output: list = messages) -> None:
            output.append(message)

        await app(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": path,
                "raw_path": path.encode(),
                "query_string": b"",
                "root_path": "",
                "headers": [(b"host", b"localhost")],
                "client": ("127.0.0.1", 1),
                "server": ("localhost", 8000),
            },
            receive,
            send,
        )
        response = next(m for m in messages if m["type"] == "http.response.start")
        headers = dict(response["headers"])
        assert response["status"] == expected, (path, response["status"])
        assert headers[b"x-content-type-options"] == b"nosniff"
        assert headers[b"x-frame-options"] == b"DENY"
        if path.startswith("/api/"):
            assert headers[b"cache-control"] == b"no-store"
        assert b"x-trace-id" in headers
        results.append({"path": path, "status": expected, "headers_passed": True})
    Path("/out/routes-result.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"ASGI routes={len(results)}, exit=0")


asyncio.run(main())
