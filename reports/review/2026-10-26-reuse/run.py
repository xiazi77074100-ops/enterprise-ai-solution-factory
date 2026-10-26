"""使い捨て_test DBで再利用試験を実行する。秘密は環境/標準入力だけに渡す。"""

import json
import os
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import psycopg
from psycopg import sql

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def main() -> int:
    docker = shutil.which("docker")
    if docker is None or (ROOT / "backend/.env").exists():
        raise RuntimeError("専用実行の前提を確認できない")
    name = f"easf-p503k-{uuid.uuid4().hex[:12]}"
    database = "easf_p503k_test"
    owner_password, app_password, key = (secrets.token_hex(24) for _ in range(3))
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    env = {
        **os.environ,
        "POSTGRES_USER": "easf_owner",
        "POSTGRES_PASSWORD": owner_password,
        "POSTGRES_DB": database,
        "EASF_ENV": "test",
        "EASF_SECRET_KEY": key,
        "EASF_TEST_DATABASE_URL": f"postgresql+psycopg://easf_app:{app_password}@127.0.0.1:{port}/{database}",
        "EASF_TEST_MIGRATION_DATABASE_URL": f"postgresql+psycopg://easf_owner:{owner_password}@127.0.0.1:{port}/{database}",
        "EASF_CAPTURE_REUSE_EVIDENCE": "1",
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    commands: list[dict] = []
    result = {
        "database_name": database,
        "container": name,
        "failure": None,
        "cleanup_success": False,
    }
    owned = False

    def redact(value: str) -> str:
        for secret in (owner_password, app_password, key):
            value = value.replace(secret, "[REDACTED]")
        return value

    def command(*args: str, stdin: str | None = None, check: bool = True) -> str:
        completed = subprocess.run(  # noqa: S603  # 固定Docker操作と自分のランダム名のみ。外部入力なし。
            [docker, *args],
            input=stdin,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
        commands.append(
            {
                "args": list(args),
                "exit_code": completed.returncode,
                "stderr": redact(completed.stderr),
            }
        )
        if check and completed.returncode:
            raise RuntimeError(f"docker_{args[0]}_failed")
        return completed.stdout.strip()

    try:
        before = command("ps", "--format", "{{.ID}} {{.Names}}")
        if command("ps", "-aq", "--filter", f"name=^/{name}$"):
            raise RuntimeError("container_name_conflict")
        owned = True
        command(
            "run",
            "-d",
            "--name",
            name,
            "--memory",
            "512m",
            "--cpus",
            "1",
            "--publish",
            f"127.0.0.1:{port}:5432",
            "--env",
            "POSTGRES_USER",
            "--env",
            "POSTGRES_PASSWORD",
            "--env",
            "POSTGRES_DB",
            "--tmpfs",
            "/var/lib/postgresql/data:size=256m",
            "postgres:17-alpine",
        )
        for attempt in range(120):
            try:
                with psycopg.connect(
                    host="127.0.0.1",
                    port=port,
                    dbname=database,
                    user="easf_owner",
                    password=owner_password,
                    connect_timeout=2,
                ):
                    break
            except psycopg.OperationalError:
                if attempt == 119:
                    raise RuntimeError("test_database_startup_timeout") from None
                time.sleep(1)
        command(
            "exec",
            "-i",
            name,
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            "easf_owner",
            "-d",
            database,
            stdin=(
                sql.SQL(
                    "CREATE ROLE easf_app LOGIN PASSWORD {};\nGRANT CONNECT ON DATABASE {} TO easf_app;\n"
                    "GRANT USAGE ON SCHEMA public TO easf_app;\n"
                    "ALTER DEFAULT PRIVILEGES FOR ROLE easf_owner IN SCHEMA public "
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO easf_app;\n"
                    "ALTER DEFAULT PRIVILEGES FOR ROLE easf_owner IN SCHEMA public "
                    "GRANT USAGE, SELECT ON SEQUENCES TO easf_app;\n"
                    "REVOKE CREATE ON SCHEMA public FROM PUBLIC;\n"
                )
                .format(sql.Literal(app_password), sql.Identifier(database))
                .as_string()
            ),
        )
        args = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/integration/test_reuse_evidence.py",
        ]
        options = (
            {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
            if os.name == "nt"
            else {"start_new_session": True}
        )
        process = subprocess.Popen(  # noqa: S603  # 現在のPythonと固定した単独テストだけを起動。
            args,
            cwd=ROOT / "backend",
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **options,
        )
        try:
            stdout, stderr = process.communicate(timeout=900)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                taskkill = shutil.which("taskkill")
                if taskkill is None:
                    process.kill()
                else:
                    subprocess.run(  # noqa: S603  # 自分が起動し所有するpytestプロセスのPIDのみ。
                        [taskkill, "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True,
                        timeout=30,
                    )
            else:
                os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate(timeout=30)
            raise RuntimeError("owned_pytest_process_timeout") from None
        finally:
            if process.poll() is not None:
                process.wait()
        log = redact((stdout + stderr).decode("utf-8", errors="replace"))
        (OUT / "pytest.log").write_text(log, encoding="utf-8", newline="\n")
        result["pytest_exit_code"] = process.returncode
        result["pytest_args"] = args[1:]
        if process.returncode:
            raise RuntimeError("reuse_test_failed")
        if not (OUT / "evidence.json").is_file():
            raise RuntimeError("reuse_evidence_missing")
        storage_cleanup = json.loads((OUT / "storage-cleanup.json").read_bytes())
        if (
            not storage_cleanup["storage_removed"]
            or not storage_cleanup["unused_default_removed"]
        ):
            raise RuntimeError("reuse_storage_cleanup_failed")
        result["storage_cleanup"] = storage_cleanup
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        result["failure"] = type(exc).__name__ + ": " + redact(str(exc))
    finally:
        if owned:
            try:
                if command("ps", "-aq", "--filter", f"name=^/{name}$"):
                    command("rm", "--force", "--volumes", name)
                result["cleanup_success"] = not bool(
                    command("ps", "-aq", "--filter", f"name=^/{name}$")
                )
            except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
                result["cleanup_error"] = type(exc).__name__
        try:
            result["existing_containers_unchanged"] = set(before.splitlines()) == set(
                command("ps", "--format", "{{.ID}} {{.Names}}").splitlines()
            )
        except (RuntimeError, OSError, subprocess.SubprocessError, UnboundLocalError):
            result["existing_containers_unchanged"] = False
        result["commands"] = commands
        (OUT / "execution.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != "commands"},
            ensure_ascii=False,
        )
    )
    return (
        0
        if result["failure"] is None
        and result["cleanup_success"]
        and result["existing_containers_unchanged"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
