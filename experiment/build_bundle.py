"""Assemble the baseline requirements package outside the repository and print its SHA-256 (P4-02).

    python experiment/build_bundle.py --out <folder outside the repository>
    python experiment/build_bundle.py --hash-only      # the SHA-256 without writing anything

Contents: experiment/baseline_bundle/*.md and the contract dev documents and labels (fixtures/contract/dev/
documents, labels). Not included: the CR-1 gold (labels_cr1), the generator, the manifest, anything else from EASF.
The SHA-256 is over the sorted list of "<path> <sha256 of the file>" lines, so it does not depend on the OS or on
file times. Standard library only.
"""

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "": ROOT / "experiment" / "baseline_bundle",
    "data/dev/documents": ROOT / "fixtures" / "contract" / "dev" / "documents",
    "data/dev/labels": ROOT / "fixtures" / "contract" / "dev" / "labels",
}


def files() -> list[tuple[str, Path]]:
    found = []
    for target, source in SOURCES.items():
        for path in sorted(p for p in source.iterdir() if p.is_file()):
            found.append((f"{target}/{path.name}".lstrip("/"), path))
    return sorted(found)


def bundle_sha256() -> str:
    lines = [f"{name} {hashlib.sha256(path.read_bytes()).hexdigest()}\n" for name, path in files()]
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--out", type=Path)
    group.add_argument("--hash-only", action="store_true")
    args = parser.parse_args()
    if args.out is not None:
        out = args.out.resolve()
        if out == ROOT or ROOT in out.parents:
            print("the bundle must be written outside the EASF repository", file=sys.stderr)
            return 2
        for name, path in files():
            (out / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, out / name)
        print(f"{len(files())} files written to {out}")
    print(f"bundle sha256: {bundle_sha256()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
