"""Single-process worker (ADR-001): `python -m app.executor.worker`. Uses the DB as the queue."""

import logging
import time

from app.core.config import get_settings
from app.core.db import make_session_factory
from app.executor.engine import Executor
from app.executor.handlers import production_handlers

logger = logging.getLogger("easf.worker")
IDLE_SLEEP_S = 1.0


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    executor = Executor(make_session_factory(get_settings()), production_handlers())
    logger.info("worker started")
    while True:
        if not executor.run_once():
            time.sleep(IDLE_SLEEP_S)


if __name__ == "__main__":
    main()
