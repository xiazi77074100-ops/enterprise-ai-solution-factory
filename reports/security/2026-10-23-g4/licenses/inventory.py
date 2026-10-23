"""固定依存とローカルの配布メタデータを照合する（ネットワーク・インストールなし）。"""

import hashlib
import importlib.metadata as metadata
import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def license_files(paths: list[Path]) -> list[dict[str, str]]:
    return [
        {"path": path.relative_to(ROOT).as_posix(), "sha256": digest(path)}
        for path in sorted(set(paths))
        if path.is_file()
    ]


def main() -> None:
    lock = tomllib.loads((ROOT / "backend/uv.lock").read_text(encoding="utf-8"))
    installed = {normalized(d.metadata["Name"]): d for d in metadata.distributions()}
    python_rows = []
    for package in lock["package"]:
        dist = installed.get(normalized(package["name"]))
        fields = dist.metadata if dist else {}
        paths = (
            [
                Path(dist.locate_file(f))
                for f in (dist.files or [])
                if any(
                    part.lower().startswith(("license", "copying", "notice"))
                    for part in f.parts
                )
            ]
            if dist
            else []
        )
        python_rows.append(
            {
                "name": package["name"],
                "locked_version": package["version"],
                "installed_version": dist.version if dist else None,
                "version_match": dist.version == package["version"] if dist else False,
                "source": package.get("source"),
                "license_expression": fields.get("License-Expression"),
                "license": fields.get("License"),
                "license_classifiers": [
                    c
                    for c in fields.get_all("Classifier", [])
                    if c.startswith("License ::")
                ]
                if dist
                else [],
                "license_files": license_files(paths),
            }
        )
    node_lock = json.loads(
        (ROOT / "frontend/package-lock.json").read_text(encoding="utf-8")
    )
    node_rows = []
    for location, package in node_lock["packages"].items():
        if not location:
            continue
        folder = ROOT / "frontend" / location
        manifest = folder / "package.json"
        actual = (
            json.loads(manifest.read_text(encoding="utf-8"))
            if manifest.is_file()
            else {}
        )
        node_rows.append(
            {
                "location": location,
                "name": actual.get("name", location.split("node_modules/")[-1]),
                "locked_version": package.get("version"),
                "installed_version": actual.get("version"),
                "version_match": actual.get("version") == package.get("version"),
                "dev": package.get("dev", False),
                "optional": package.get("optional", False),
                "lock_license": package.get("license"),
                "installed_license": actual.get("license"),
                "resolved": package.get("resolved"),
                "integrity": package.get("integrity"),
                "license_files": license_files(
                    [
                        p
                        for p in folder.iterdir()
                        if p.name.lower().startswith(("license", "copying", "notice"))
                    ]
                )
                if folder.is_dir()
                else [],
            }
        )
    result = {
        "source_commit": "97e7c727ccc30b1b37caf3335be6db8c162c5696",
        "lock_sha256": {
            name: digest(ROOT / name)
            for name in ["backend/uv.lock", "frontend/package-lock.json"]
        },
        "scope": "全固定依存とローカル配布の照合。OS・内包依存は別途確認。",
        "python": python_rows,
        "node": node_rows,
    }
    (OUT / "inventory.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary = {
        "python_locked": len(python_rows),
        "python_version_match": sum(r["version_match"] for r in python_rows),
        "python_unmatched": [r["name"] for r in python_rows if not r["version_match"]],
        "node_locked": len(node_rows),
        "node_version_match": sum(r["version_match"] for r in node_rows),
        "node_unmatched": [r["location"] for r in node_rows if not r["version_match"]],
        "node_missing_lock_license": [
            r["location"] for r in node_rows if not r["lock_license"]
        ],
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
