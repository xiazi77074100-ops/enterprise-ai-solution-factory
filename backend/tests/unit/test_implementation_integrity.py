"""固定ソースの逸脱と起動拒否。製品ファイル・DBは変更しない。"""

import json
import runpy
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from app.adapters.llm import LlmHandler
from app.adapters.local import LocalHandler
from app.adapters.mcp import McpToolHandler
from app.capabilities.result_exporter import export_result
from app.catalog.implementation_integrity import (
    MANIFEST_PATH,
    ROOT,
    ImplementationIntegrityError,
    load_manifest,
    verify_bindings,
    verify_files,
)
from app.core.config import Settings
from app.executor import handlers


@pytest.fixture
def copied_release(tmp_path: Path) -> Path:
    manifest = load_manifest((ROOT / MANIFEST_PATH).read_bytes())
    names = {MANIFEST_PATH} | {name for item in manifest.implementations for name in item.files}
    for name in names:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
    return tmp_path


@pytest.mark.parametrize(
    "name",
    [
        "backend/app/capabilities/rule_validator.py",
        "backend/app/capabilities/values.py",
        "backend/app/mcp_tools/locate_evidence.json",
        "backend/app/executor/handlers.py",
        "backend/app/catalog/implementation_integrity.py",
    ],
)
def test_changed_source_is_rejected(copied_release: Path, name: str) -> None:
    with (copied_release / name).open("ab") as stream:
        stream.write(b"\n ")
    with pytest.raises(ImplementationIntegrityError, match="implementation_digest_mismatch"):
        verify_files(copied_release)


def test_missing_file_is_rejected(copied_release: Path) -> None:
    (copied_release / "backend/app/capabilities/values.py").unlink()
    with pytest.raises(ImplementationIntegrityError, match="implementation_file_missing"):
        verify_files(copied_release)


def test_missing_manifest_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ImplementationIntegrityError, match="implementation_file_missing"):
        verify_files(tmp_path)


def test_symlink_source_is_rejected(copied_release: Path, tmp_path: Path) -> None:
    source = copied_release / "backend/app/capabilities/values.py"
    target = tmp_path / "values-copy.py"
    shutil.copyfile(source, target)
    source.unlink()
    try:
        source.symlink_to(target)
    except OSError:
        pytest.skip("このWindows環境ではsymlink作成権限がない。CIで実施する")
    with pytest.raises(ImplementationIntegrityError, match="implementation_path_invalid"):
        verify_files(copied_release)


@pytest.mark.parametrize("change", ["duplicate", "unknown", "missing", "path", "digest", "extra"])
def test_invalid_manifest_is_rejected(change: str) -> None:
    data = json.loads((ROOT / MANIFEST_PATH).read_bytes())
    first = data["implementations"][0]
    if change == "duplicate":
        data["implementations"].append(first)
    elif change == "unknown":
        first["ref"] = "unknown.v1"
    elif change == "missing":
        data["implementations"].pop()
    elif change == "path":
        first["files"] = {"backend/app/../../outside.py": "0" * 64}
    elif change == "digest":
        first["files"] = {"backend/app/example.py": "not-a-digest"}
    else:
        data["extra"] = True
    with pytest.raises(ImplementationIntegrityError):
        load_manifest(json.dumps(data).encode())


def test_duplicate_json_keys_are_rejected() -> None:
    with pytest.raises(ImplementationIntegrityError, match="manifest_duplicate_key"):
        load_manifest(b'{"schema_version":1,"schema_version":1}')


def test_changed_binding_is_rejected() -> None:
    with pytest.raises(ImplementationIntegrityError, match="implementation_binding_mismatch"):
        verify_bindings(verify_files(), {})


def test_current_release_and_repeated_handler_creation() -> None:
    settings = Settings(
        _env_file=None,
        env="test",
        database_url="postgresql+psycopg://unused@127.0.0.1:1/unused",
        secret_key="test-only-implementation-integrity-0123456789",
    )
    assert len(verify_files().implementations) == 6
    assert set(handlers.production_handlers(settings)) == set(handlers.production_handlers(settings))


def test_startup_stops_before_handler_creation(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject() -> None:
        raise ImplementationIntegrityError("implementation_digest_mismatch")

    monkeypatch.setattr(handlers, "verify_files", reject)
    with pytest.raises(ImplementationIntegrityError, match="implementation_digest_mismatch"):
        handlers.production_handlers(
            Settings(
                _env_file=None,
                env="test",
                database_url="postgresql+psycopg://unused@127.0.0.1:1/unused",
                secret_key="test-only-integrity-secret-0123456789",
            )
        )


@pytest.mark.parametrize("entry", ["api", "worker"])
def test_api_and_worker_stop_on_integrity_failure(monkeypatch: pytest.MonkeyPatch, entry: str) -> None:
    from app import main
    from app.executor import worker

    settings = Settings(
        _env_file=None,
        env="test",
        database_url="postgresql+psycopg://unused@127.0.0.1:1/unused",
        secret_key="test-only-implementation-integrity-0123456789",
    )

    def reject() -> None:
        raise ImplementationIntegrityError("implementation_digest_mismatch")

    monkeypatch.setattr(handlers, "verify_files", reject)
    monkeypatch.setattr(worker, "get_settings", lambda: settings)
    with pytest.raises(ImplementationIntegrityError, match="implementation_digest_mismatch"):
        if entry == "api":
            main.create_app(settings)
        else:
            worker.main()


@pytest.mark.parametrize("target", ["local", "mcp", "llm"])
def test_rebound_handler_is_rejected(target: str) -> None:
    settings = Settings(
        _env_file=None,
        env="test",
        database_url="postgresql+psycopg://unused@127.0.0.1:1/unused",
        secret_key="test-only-implementation-integrity-0123456789",
    )
    table = handlers.production_handlers(settings)
    if target == "local":
        local = table[("local", "rule_based_extractor.v1")]
        assert isinstance(local, LocalHandler)
        local.func = export_result
    elif target == "mcp":
        mcp = table[("mcp_tool", "easf_local_mcp:locate_evidence")]
        assert isinstance(mcp, McpToolHandler)
        # 共有LOCAL_SERVERも同時に変わるが、文字列定数の比較で拒否する。
        original = mcp.server.model_copy(deep=True)
        try:
            mcp.server.args = ["-m", "other_server"]
            with pytest.raises(ImplementationIntegrityError):
                handlers._bindings(table)
        finally:
            mcp.server.args = original.args
        return
    else:
        llm = table[("llm", "structured_extractor.v1")]
        assert isinstance(llm, LlmHandler)
        llm.instructions = "TEST ONLY: changed instruction"
    with pytest.raises(ImplementationIntegrityError, match="implementation_binding_mismatch"):
        handlers._bindings(table)


@pytest.mark.parametrize("change", ["sha", "binding", "remove", "remove_file"])
def test_ci_comparison_rejects_old_ref_changes(change: str) -> None:
    compare = runpy.run_path(str(ROOT / "scripts/check_implementation_manifest.py"))["compare_manifests"]
    previous = (ROOT / MANIFEST_PATH).read_bytes()
    data = json.loads(previous)
    first = data["implementations"][0]
    if change == "sha":
        first["files"][next(iter(first["files"]))] = "0" * 64
    elif change == "binding":
        first["binding"]["entry"] = "other.entry"
    elif change == "remove_file":
        first["files"].pop(next(iter(first["files"])))
    else:
        data["implementations"].pop()
    with pytest.raises(ValueError, match="manifest_existing_ref_changed"):
        compare(previous, json.dumps(data).encode())


def test_ci_comparison_preserves_old_rows_and_allows_addition() -> None:
    compare = runpy.run_path(str(ROOT / "scripts/check_implementation_manifest.py"))["compare_manifests"]
    previous = (ROOT / MANIFEST_PATH).read_bytes()
    compare(previous, previous)
    data = json.loads(previous)
    added = dict(data["implementations"][0], ref="future.v2")
    data["implementations"].append(added)
    compare(previous, json.dumps(data).encode())


@pytest.mark.parametrize(
    ("bootstrap", "commit_exists", "manifest_exists", "expected"),
    [(True, True, False, 0), (False, True, False, 1), (True, False, False, 1), (False, True, True, 0)],
)
def test_ci_main_requires_trusted_existing_base(
    monkeypatch: pytest.MonkeyPatch, bootstrap: bool, commit_exists: bool, manifest_exists: bool, expected: int
) -> None:
    script = runpy.run_path(str(ROOT / "scripts/check_implementation_manifest.py"))
    base = script["BOOTSTRAP_BASE"] if bootstrap else "a" * 40
    monkeypatch.setattr(sys, "argv", ["check_implementation_manifest.py", "--base-ref", base])
    monkeypatch.setattr(shutil, "which", lambda name: "/trusted/git")

    def git_result(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        if args[1] == "cat-file":
            return subprocess.CompletedProcess(args, 0 if commit_exists else 1, stdout=b"", stderr=b"")
        return subprocess.CompletedProcess(
            args,
            0 if manifest_exists else 1,
            stdout=(ROOT / MANIFEST_PATH).read_bytes() if manifest_exists else b"",
            stderr=b"",
        )

    monkeypatch.setattr(subprocess, "run", git_result)
    assert script["main"]() == expected
