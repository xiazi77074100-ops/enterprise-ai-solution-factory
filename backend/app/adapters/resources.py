"""Worker-side handlers that hand stored resources to a local capability (run_execution.md §5).

Capabilities never read the database or the file system themselves. These handlers resolve a reference in
the worker (a document id -> the stored bytes, a Rule pack id and version -> its registered content) and then
run the capability function in the child process like any other local capability. A reference that cannot
be resolved fails the node (not retried).
"""

import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.base import AdapterResult
from app.adapters.local import LocalFunction, LocalHandler
from app.catalog.models import RulePackVersion
from app.documents import storage
from app.documents.models import Document

PARSER_MEMORY_BYTES = 1024 * 1024 * 1024  # native PDF/image parsing in the child (ADR-003)


class StoredDocumentHandler:
    """`document_ref` -> {data, media_type, document_id, sha256} for the child (the hash is checked on read)."""

    def __init__(self, func: LocalFunction, session_factory: Callable[[], Session], storage_dir: Path) -> None:
        self.local = LocalHandler(func, PARSER_MEMORY_BYTES)
        self.session_factory = session_factory
        self.storage_dir = storage_dir

    def invoke(self, inputs: dict[str, Any], config: dict[str, Any], timeout_s: float) -> AdapterResult:
        with self.session_factory() as db:
            document = db.get(Document, uuid.UUID(str(inputs["document_ref"])))
            if document is None:
                return AdapterResult(status="unavailable", error_code="document_not_found")
            try:
                data = storage.read(self.storage_dir, document.storage_name, document.sha256)
            except (OSError, ValueError):
                return AdapterResult(status="unavailable", error_code="document_unreadable")
            payload = {
                "data": data,
                "media_type": document.media_type,
                "document_id": str(document.id),
                "sha256": document.sha256,
            }
        return self.local.invoke(payload, config, timeout_s)


class RulePackHandler:
    """Adds the registered Rule pack named by config (rule_pack_id, rule_pack_version) as config["rule_pack"]."""

    def __init__(self, func: LocalFunction, session_factory: Callable[[], Session]) -> None:
        self.local = LocalHandler(func)
        self.session_factory = session_factory

    def invoke(self, inputs: dict[str, Any], config: dict[str, Any], timeout_s: float) -> AdapterResult:
        with self.session_factory() as db:
            pack = db.execute(
                select(RulePackVersion.rule_pack).where(
                    RulePackVersion.rule_pack_id == config["rule_pack_id"],
                    RulePackVersion.version == config["rule_pack_version"],
                )
            ).scalar_one_or_none()
        if pack is None:
            return AdapterResult(status="unavailable", error_code="rule_pack_not_found")
        return self.local.invoke(inputs, {**config, "rule_pack": pack}, timeout_s)
