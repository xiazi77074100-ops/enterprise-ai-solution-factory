"""DBへ接続せず、独立workerの未解決外部キーを確認する。製品修正ではない。"""

import importlib
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT.parents[2] / "backend"))

from app.core.db import Base
from sqlalchemy.exc import NoReferencedTableError


def missing() -> list[str]:
    failures = []
    for table in list(Base.metadata.tables.values()):
        for key in table.foreign_keys:
            try:
                _ = key.column
            except NoReferencedTableError:
                failures.append(str(key.parent) + " -> " + key.target_fullname)
    return sorted(failures)


importlib.import_module("app.executor.worker")
before = missing()
modules = ("app.auth.models",)
for module in modules:
    importlib.import_module(module)
after = missing()
result = {
    "standalone_worker_missing_foreign_keys": before,
    "diagnostic_only_added_imports": list(modules),
    "after_diagnostic_imports_missing_foreign_keys": after,
    "database_connected": False,
    "product_modified": False,
}
(OUT / "model-repro.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(result, ensure_ascii=False))
raise SystemExit(0 if before and not after else 1)
