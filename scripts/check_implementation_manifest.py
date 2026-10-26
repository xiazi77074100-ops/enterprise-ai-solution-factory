"""信頼する統合先の表と比較し、旧refの削除・変更を拒否する。"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "backend/app/catalog/implementation_manifest.json"
BOOTSTRAP_BASE = "b513ec46d807a8b397461d5078b992b8a9a98fe5"


def compare_manifests(previous: bytes, current: bytes) -> None:
    old: dict[str, Any] = json.loads(previous)
    new: dict[str, Any] = json.loads(current)
    if old["schema_version"] != new["schema_version"]:
        raise ValueError("manifest_schema_changed")
    old_rows = {(row["kind"], row["ref"]): row for row in old["implementations"]}
    new_rows = {(row["kind"], row["ref"]): row for row in new["implementations"]}
    if any(new_rows.get(key) != row for key, row in old_rows.items()):
        raise ValueError("manifest_existing_ref_changed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-ref", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.base_ref):
        parser.error("base-refには信頼する40桁のGit SHAを指定してください")
    # リポジトリ内の固定モジュールだけをロードする。refからimport先を作らない。
    sys.path.insert(0, str(ROOT / "backend"))
    from app.catalog.implementation_integrity import verify_files  # noqa: PLC0415

    try:
        verify_files(ROOT)
        git = shutil.which("git")
        if git is None:
            raise ValueError("git_unavailable")
        commit = subprocess.run(  # noqa: S603  # 検証済みSHAと固定引数だけを渡す。
            [git, "cat-file", "-e", f"{args.base_ref}^{{commit}}"],
            cwd=ROOT,
            capture_output=True,
            timeout=20,
            check=False,
        )
        if commit.returncode:
            raise ValueError("manifest_base_unavailable")
        result = subprocess.run(  # noqa: S603  # SHAは上で検証し、パスは固定。
            [git, "show", f"{args.base_ref}:{MANIFEST}"],
            cwd=ROOT,
            capture_output=True,
            timeout=20,
            check=False,
        )
        if result.returncode:
            if args.base_ref != BOOTSTRAP_BASE:
                raise ValueError("manifest_base_unavailable")
            print("初期基準導入：承認された基点にのみ表が未存在")
        else:
            compare_manifests(result.stdout, (ROOT / MANIFEST).read_bytes())
            print("旧refの固定値を保持、現行ファイルの照合成功")
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        # 入力やGit stderrは出さず、失敗の種別だけを報告する。
        print(f"実装固定の検査失敗：{type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
