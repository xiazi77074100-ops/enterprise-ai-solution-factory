"""既存の3ケースを製品イメージの実装で再実行する。DB接続はしない。"""

import asyncio
import hashlib
import importlib.util
import json
import os
from pathlib import Path

from app.core import middleware

spec = importlib.util.spec_from_file_location("checks", "/checks/check_logs.py")
assert spec is not None and spec.loader is not None
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)
checks.OUT = Path("/out")
result = asyncio.run(checks.main("candidate"))
path = checks.OUT / "candidate-result.json"
data = json.loads(path.read_text(encoding="utf-8"))
data["source_commit"] = "147584220ce7c2eff3e4bfac0c77ce0cf71f3cae"
data["uid"] = os.getuid()
data["middleware_path"] = middleware.__file__
data["middleware_sha256"] = hashlib.sha256(
    Path(middleware.__file__).read_bytes()
).hexdigest()
assert data["uid"] == 10001
assert data["middleware_path"] == "/app/backend/app/core/middleware.py"
assert data["middleware_sha256"] == (
    "4c5d424d0259dd26d14227dbd9a78aac361b8f10688a6db4d132e81f5b4837aa"
)
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"cases={len(data['cases'])}, uid={data['uid']}, exit={result}")
raise SystemExit(result)
