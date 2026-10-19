"""Local capability execution in a child process (run_execution.md §5).

The function is fixed in code (no dynamic import from contract data). It runs in a spawned child process so a
timeout, an endless loop or a crash cannot take the worker down: on timeout the child is killed. Only the
exception type crosses back, never its message (it may contain input values).
"""

import json
import multiprocessing
import sys
from collections.abc import Callable
from multiprocessing.connection import Connection
from typing import Any

from app.adapters.base import MAX_OUTPUT_BYTES, AdapterResult

LocalFunction = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]
_CONTEXT = multiprocessing.get_context("spawn")
_KILL_GRACE_S = 2.0


def _limit_memory(limit_bytes: int | None) -> None:
    """Address-space cap for the child (ADR-003). POSIX only: on Windows (local development) it is not set."""
    if limit_bytes is None or sys.platform == "win32":
        return
    import resource  # noqa: PLC0415  # POSIX-only module

    resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))


def _child(
    conn: Connection,
    func: LocalFunction,
    inputs: dict[str, Any],
    config: dict[str, Any],
    memory_limit_bytes: int | None = None,
) -> None:
    try:
        _limit_memory(memory_limit_bytes)
        payload = json.dumps(func(inputs, config), ensure_ascii=False, allow_nan=False).encode()
    except Exception as exc:  # reported as a code only
        conn.send(("error", type(exc).__name__))
        return
    if len(payload) > MAX_OUTPUT_BYTES:
        conn.send(("too_large", None))
    else:
        conn.send(("ok", payload))


class LocalHandler:
    def __init__(self, func: LocalFunction, memory_limit_bytes: int | None = None) -> None:
        self.func = func
        self.memory_limit_bytes = memory_limit_bytes

    def invoke(self, inputs: dict[str, Any], config: dict[str, Any], timeout_s: float) -> AdapterResult:
        receiver, sender = _CONTEXT.Pipe(duplex=False)
        process = _CONTEXT.Process(
            target=_child, args=(sender, self.func, inputs, config, self.memory_limit_bytes), daemon=True
        )
        process.start()
        sender.close()
        try:
            if not receiver.poll(timeout_s):
                process.kill()
                return AdapterResult(status="timeout", error_code="timeout")
            try:
                kind, value = receiver.recv()
            except EOFError:  # the child died without answering (crash, os._exit, killed)
                return AdapterResult(status="error", error_code="crashed")
        finally:
            receiver.close()
            process.join(_KILL_GRACE_S if process.is_alive() else None)
            if process.is_alive():
                process.kill()
                process.join()
        if kind == "too_large":
            return AdapterResult(status="too_large", error_code="output_too_large")
        if kind == "error":
            return AdapterResult(status="error", error_code=f"exception_{str(value).lower()[:40]}")
        output = json.loads(value)
        if not isinstance(output, dict):
            return AdapterResult(status="invalid_output", error_code="invalid_output")
        return AdapterResult(status="ok", output=output)
