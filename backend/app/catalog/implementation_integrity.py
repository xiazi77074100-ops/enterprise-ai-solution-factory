"""固定した業務ソースの照合。環境再現・実行中の改変防止を保証するものではない。"""

import hashlib
import json
import re
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.catalog.registry import IMPLEMENTATIONS

ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = "backend/app/catalog/implementation_manifest.json"
HUMAN_REVIEW = ("local", "human_review.v1")
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class ImplementationIntegrityError(RuntimeError):
    """内容・設定値を含めない固定コードだけを伝える。"""


class Binding(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    handler: str = Field(min_length=1, max_length=128)
    entry: str = Field(min_length=1, max_length=128)


class Implementation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    kind: Literal["local", "llm", "mcp_tool"]
    ref: str = Field(pattern=r"^[a-z][a-z0-9_.:-]{0,127}$")
    binding: Binding
    files: dict[str, Digest] = Field(min_length=1, max_length=64)


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal[1]
    implementations: list[Implementation] = Field(min_length=1, max_length=32)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ImplementationIntegrityError("manifest_duplicate_key")
        result[key] = value
    return result


def load_manifest(data: bytes) -> Manifest:
    if len(data) > 256 * 1024:
        raise ImplementationIntegrityError("manifest_too_large")
    try:
        manifest = Manifest.model_validate(json.loads(data, object_pairs_hook=_unique_object))
    except (ValueError, ValidationError):
        raise ImplementationIntegrityError("manifest_invalid") from None
    keys = [(item.kind, item.ref) for item in manifest.implementations]
    if len(keys) != len(set(keys)) or set(keys) != set(IMPLEMENTATIONS) - {HUMAN_REVIEW}:
        raise ImplementationIntegrityError("manifest_refs_mismatch")
    for item in manifest.implementations:
        for name in item.files:
            if not re.fullmatch(r"backend/app/(?:[a-z0-9_]+/)*[a-z0-9_]+\.(py|json)", name) or name == MANIFEST_PATH:
                raise ImplementationIntegrityError("manifest_path_invalid")
    return manifest


def _read_file(root: Path, name: str) -> bytes:
    path = root / name
    try:
        if not path.resolve().is_relative_to(root.resolve()) or any(
            parent.is_symlink() for parent in (path, *path.parents) if parent != root
        ):
            raise ImplementationIntegrityError("implementation_path_invalid")
        if path.stat().st_size > 2 * 1024 * 1024:
            raise ImplementationIntegrityError("implementation_file_too_large")
        return path.read_bytes()
    except OSError:
        raise ImplementationIntegrityError("implementation_file_missing") from None


def verify_files(root: Path = ROOT) -> Manifest:
    manifest = load_manifest(_read_file(root, MANIFEST_PATH))
    checked: dict[str, str] = {}
    for item in manifest.implementations:
        for name, expected in item.files.items():
            if name not in checked:
                checked[name] = hashlib.sha256(_read_file(root, name)).hexdigest()
            if checked[name] != expected:
                raise ImplementationIntegrityError("implementation_digest_mismatch")
    return manifest


def verify_bindings(manifest: Manifest, bindings: dict[tuple[str, str], Binding]) -> None:
    expected = {(item.kind, item.ref): item.binding for item in manifest.implementations}
    if bindings != expected:
        raise ImplementationIntegrityError("implementation_binding_mismatch")
