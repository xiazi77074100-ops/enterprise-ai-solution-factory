"""The allowlist's `available` flags and the handler table describe the same keys (run_execution.md §5)."""

from app.catalog.registry import IMPLEMENTATIONS
from app.executor.engine import HUMAN_REVIEW
from app.executor.handlers import production_handlers
from tests.conftest import make_settings


def test_available_keys_match_bound_code() -> None:
    available = {key for key, impl in IMPLEMENTATIONS.items() if impl.available}
    assert available == set(production_handlers(make_settings())) | {HUMAN_REVIEW}
