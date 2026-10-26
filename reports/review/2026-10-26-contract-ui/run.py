"""専用DB・API・worker・Viteだけを起動する実画面試験。"""

import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import httpx2 as httpx
import psycopg
from psycopg import sql

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main() -> int:
    docker = shutil.which("docker")
    node = shutil.which("node")
    if not docker or not node or (ROOT / "backend/.env").exists():
        raise RuntimeError("専用実行の前提を確認できない")
    if (OUT / "execution.json").exists():
        raise RuntimeError("前回の証拠を退避してから再実行する")
    name = "easf-p503l-" + uuid.uuid4().hex[:12]
    database = "easf_p503l_test"
    owner, app, key, password = (secrets.token_hex(24) for _ in range(4))
    hidden = [owner, app, key, password]
    db_port, api_port, ui_port = port(), port(), port()
    api = f"http://127.0.0.1:{api_port}"
    origin = f"http://127.0.0.1:{ui_port}"
    temporary = Path(tempfile.mkdtemp(prefix="easf-p503l-"))
    env = {
        **os.environ,
        "POSTGRES_USER": "easf_owner",
        "POSTGRES_PASSWORD": owner,
        "POSTGRES_DB": database,
        "EASF_ENV": "assessment",
        "EASF_SECRET_KEY": key,
        "EASF_DATABASE_URL": f"postgresql+psycopg://easf_app:{app}@127.0.0.1:{db_port}/{database}",
        "EASF_MIGRATION_DATABASE_URL": f"postgresql+psycopg://easf_owner:{owner}@127.0.0.1:{db_port}/{database}",
        "EASF_STORAGE_DIR": str(temporary / "documents"),
        "EASF_SITE_ORIGIN": origin,
        "EASF_COOKIE_SECURE": "false",
        "EASF_NEW_USER_PASSWORD": password,
        "E2E_UI_PORT": str(ui_port),
        "E2E_API_URL": api,
        "E2E_BASE_URL": origin,
        "E2E_CONTRACT_REAL": "1",
        "E2E_LOGIN_ID": "p503l_reviewer",
        "E2E_PASSWORD": password,
        "E2E_ARTIFACT_DIR": str(temporary / "playwright"),
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    result = {"database": database, "container": name, "failure": None}
    commands = []
    processes = []
    stops = []
    handles = []
    owned = False
    before = ""

    def redact(value: str) -> str:
        for secret in hidden:
            value = value.replace(secret, "[REDACTED]")
        return value

    def command(args: list[str], cwd: Path = ROOT, stdin: str | None = None) -> str:
        completed = subprocess.run(
            args,
            check=False,
            cwd=cwd,
            env=env,
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        commands.append(
            {
                "args": args,
                "exit_code": completed.returncode,
                "output": redact(completed.stdout + completed.stderr),
            }
        )
        if completed.returncode:
            raise RuntimeError("command_failed_" + str(len(commands)))
        return completed.stdout.strip()

    def start(label: str, args: list[str], cwd: Path) -> subprocess.Popen:
        handle = (temporary / (label + ".log")).open("wb")
        handles.append(handle)
        process = subprocess.Popen(
            args,
            cwd=cwd,
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        processes.append((label, process))
        return process

    def wait_http(url: str) -> None:
        with httpx.Client(trust_env=False, timeout=2) as client:
            for _ in range(90):
                if any(process.poll() is not None for _, process in processes):
                    raise RuntimeError("owned_service_exited_before_ready")
                try:
                    if client.get(url).status_code < 500:
                        return
                except httpx.HTTPError:
                    pass
                time.sleep(1)
        raise RuntimeError("localhost_startup_timeout")

    try:
        before = command([docker, "ps", "--format", "{{.ID}} {{.Names}}"])
        if command([docker, "ps", "-aq", "--filter", f"name=^/{name}$"]):
            raise RuntimeError("container_name_conflict")
        owned = True
        command(
            [
                docker,
                "run",
                "-d",
                "--name",
                name,
                "--memory",
                "512m",
                "--cpus",
                "1",
                "--publish",
                f"127.0.0.1:{db_port}:5432",
                "--env",
                "POSTGRES_USER",
                "--env",
                "POSTGRES_PASSWORD",
                "--env",
                "POSTGRES_DB",
                "--tmpfs",
                "/var/lib/postgresql/data:size=256m",
                "postgres:17-alpine",
            ]
        )
        for attempt in range(120):
            try:
                with psycopg.connect(
                    host="127.0.0.1",
                    port=db_port,
                    dbname=database,
                    user="easf_owner",
                    password=owner,
                    connect_timeout=2,
                ):
                    break
            except psycopg.OperationalError:
                if attempt == 119:
                    raise RuntimeError("database_startup_timeout") from None
                time.sleep(1)
        bootstrap = (
            sql.SQL(
                "CREATE ROLE easf_app LOGIN PASSWORD {}; GRANT CONNECT ON DATABASE {} TO easf_app; "
                "GRANT USAGE ON SCHEMA public TO easf_app; "
                "ALTER DEFAULT PRIVILEGES FOR ROLE easf_owner IN SCHEMA public "
                "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO easf_app; "
                "ALTER DEFAULT PRIVILEGES FOR ROLE easf_owner IN SCHEMA public "
                "GRANT USAGE, SELECT ON SEQUENCES TO easf_app; "
                "REVOKE CREATE ON SCHEMA public FROM PUBLIC;"
            )
            .format(sql.Literal(app), sql.Identifier(database))
            .as_string()
        )
        command(
            [
                docker,
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
            ],
            stdin=bootstrap,
        )
        backend = ROOT / "backend"
        command([sys.executable, "-m", "alembic", "upgrade", "head"], backend)
        for login, display, flags in (
            ("p503l_admin", "試験設計者", ["--admin"]),
            ("p503l_reviewer", "試験確認者", []),
        ):
            command(
                [
                    sys.executable,
                    "-m",
                    "app.admin",
                    "create-user",
                    "--login-id",
                    login,
                    "--display-name",
                    display,
                    *flags,
                ],
                backend,
            )
        start(
            "api",
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(api_port),
                "--no-server-header",
            ],
            backend,
        )
        start("worker", [sys.executable, "-m", "app.executor.worker"], backend)
        wait_http(api + "/api/v1/session")
        with (
            httpx.Client(base_url=api, trust_env=False, timeout=30) as admin,
            httpx.Client(base_url=api, trust_env=False, timeout=30) as reviewer,
        ):

            def request(
                client: httpx.Client, method: str, path: str, status: int, **kwargs
            ):
                response = client.request(method, path, **kwargs)
                if response.status_code != status:
                    raise RuntimeError(f"seed_{method}_{path}_{response.status_code}")
                return response.json()

            users = []
            for client, login in ((admin, "p503l_admin"), (reviewer, "p503l_reviewer")):
                client.headers["Origin"] = origin
                data = request(
                    client,
                    "POST",
                    "/api/v1/session",
                    200,
                    json={"login_id": login, "password": password},
                )
                hidden.append(data["csrf_token"])
                hidden.extend(client.cookies.values())
                client.headers["X-CSRF-Token"] = data["csrf_token"]
                users.append(data["user"]["id"])
            project = request(
                admin,
                "POST",
                "/api/v1/projects",
                201,
                json={
                    "name": "契約書の実画面検証",
                    "business_domain": "合成文書の専用試験",
                },
            )["id"]
            request(
                admin,
                "PUT",
                f"/api/v1/projects/{project}/members",
                200,
                json=[
                    {
                        "user_id": users[0],
                        "roles": ["solution_lead", "solution_architect"],
                    },
                    {
                        "user_id": users[1],
                        "roles": ["solution_lead", "business_reviewer"],
                    },
                ],
            )
            for path in sorted(
                (ROOT / "contracts/examples/capabilities").glob("*.json")
            ):
                request(
                    admin,
                    "POST",
                    "/api/v1/capabilities",
                    201,
                    json=json.loads(path.read_bytes()),
                )
            request(
                admin,
                "POST",
                "/api/v1/rule-packs",
                201,
                json=json.loads(
                    (ROOT / "fixtures/rule_packs/contract-1.1.0.json").read_bytes()
                ),
            )
            requirement = request(
                admin,
                "POST",
                f"/api/v1/projects/{project}/requirements",
                201,
                json={"content": "既存dev契約書の確認・修正・出力を画面で検証する。"},
            )["id"]
            request(
                reviewer, "POST", f"/api/v1/requirements/{requirement}/approve", 200
            )
            solution = request(
                admin,
                "POST",
                "/api/v1/solutions",
                201,
                json={
                    "project_id": project,
                    "requirement_revision_id": requirement,
                    "workflow": json.loads(
                        (ROOT / "fixtures/workflows/contract-v3.json").read_bytes()
                    ),
                },
            )["id"]
            validation = request(
                admin, "POST", f"/api/v1/solutions/{solution}/validate", 200
            )
            if not validation["valid"]:
                raise RuntimeError("seed_validation_failed")
            request(reviewer, "POST", f"/api/v1/solutions/{solution}/approve", 200)
        env["E2E_PROJECT_ID"] = project
        env["E2E_SOLUTION_ID"] = solution
        frontend = ROOT / "frontend"
        start(
            "vite",
            [
                node,
                str(frontend / "node_modules/vite/bin/vite.js"),
                "--config",
                str(OUT / "vite.config.mts"),
            ],
            frontend,
        )
        wait_http(origin)
        browser = start(
            "playwright",
            [
                node,
                str(frontend / "node_modules/@playwright/test/cli.js"),
                "test",
                "--config",
                "e2e/contract-real.config.ts",
            ],
            frontend,
        )
        result["playwright_exit_code"] = browser.wait(timeout=360)
        if browser.returncode:
            raise RuntimeError("browser_test_failed")
    except (RuntimeError, OSError, subprocess.SubprocessError, httpx.HTTPError) as exc:
        result["failure"] = redact(type(exc).__name__ + ": " + str(exc))
    finally:
        cleanup_errors = []
        for label, process in reversed(processes):
            try:
                if process.poll() is None:
                    taskkill = shutil.which("taskkill")
                    if not taskkill:
                        process.kill()
                        raise RuntimeError("子プロセスの停止を確認できない")
                    stopped = subprocess.run(
                        [taskkill, "/PID", str(process.pid), "/T", "/F"],
                        check=False,
                        capture_output=True,
                        timeout=30,
                    )
                    process.wait(timeout=30)
                    if stopped.returncode:
                        stops.append(
                            {
                                "service": label,
                                "taskkill_exit_code": stopped.returncode,
                                "parent_stopped": process.poll() is not None,
                            }
                        )
            except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
                cleanup_errors.append(label + ": " + type(exc).__name__)
        for handle in handles:
            handle.close()
        for log in temporary.glob("*.log"):
            text = redact(log.read_text(encoding="utf-8", errors="replace"))
            (OUT / log.name).write_text(text, encoding="utf-8", newline="\n")
        try:
            if owned:
                command([docker, "rm", "--force", "--volumes", name])
                result["container_removed"] = not bool(
                    command([docker, "ps", "-aq", "--filter", f"name=^/{name}$"])
                )
            result["existing_containers_unchanged"] = set(before.splitlines()) == set(
                command([docker, "ps", "--format", "{{.ID}} {{.Names}}"]).splitlines()
            )
        except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
            cleanup_errors.append("docker: " + type(exc).__name__)
        try:
            resolved = temporary.resolve()
            if (
                resolved.parent != Path(tempfile.gettempdir()).resolve()
                or not resolved.name.startswith("easf-p503l-")
                or temporary.is_symlink()
            ):
                raise RuntimeError("専用一時領域の削除範囲を確認できない")
            shutil.rmtree(resolved)
            result["temporary_storage_removed"] = not temporary.exists()
        except (RuntimeError, OSError) as exc:
            cleanup_errors.append("temporary_storage: " + type(exc).__name__)
        result["cleanup_errors"] = cleanup_errors
        result["stop_results"] = stops
        result["commands"] = commands
        (OUT / "execution.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(
        json.dumps(
            {k: v for k, v in result.items() if k != "commands"}, ensure_ascii=False
        )
    )
    return int(
        result["failure"] is not None
        or not result.get("container_removed")
        or not result.get("existing_containers_unchanged")
        or bool(result["cleanup_errors"])
    )


if __name__ == "__main__":
    raise SystemExit(main())
