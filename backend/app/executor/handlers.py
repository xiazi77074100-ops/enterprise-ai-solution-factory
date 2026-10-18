"""Implementation keys bound to code (run_execution.md §5). The only place where a key becomes executable.

`human_review.v1` is handled by the Executor itself (it pauses the run). Business capabilities are added in
Phase 3. app/catalog/registry.py marks exactly these keys (plus human review) as available; a test checks it.
"""

from app.executor.engine import HandlerTable


def production_handlers() -> HandlerTable:
    return {}
