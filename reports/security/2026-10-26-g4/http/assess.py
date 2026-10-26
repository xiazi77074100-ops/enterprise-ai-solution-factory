"""使い捨ての専用DBとAPIでHTTP境界を診断し、自分の資源だけを後始末する。"""

import hashlib
import json
import os
import secrets
import socket
import subprocess
import time
import uuid
from pathlib import Path

import httpx2 as httpx

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
IMAGE = "sha256:776a46f480342fe9f07347471e8ee3a96b4a9a779ba02166cc39808b0681deac"
ORIGIN = "http://localhost:5173"


def main() -> int:
    suffix = uuid.uuid4().hex[:12]
    network = f"easf-p503f-{suffix}"
    database = f"{network}-db"
    api = f"{network}-api"
    db_name = "easf_p503f_test"
    owner_password, app_password, user_password, key = (
        secrets.token_hex(24) for _ in range(4)
    )
    credentials = (owner_password, app_password, user_password, key)
    env = {
        **os.environ,
        "POSTGRES_DB": db_name,
        "POSTGRES_USER": "easf_owner",
        "POSTGRES_PASSWORD": owner_password,
        "EASF_ENV": "assessment",
        "EASF_SECRET_KEY": key,
        "EASF_SITE_ORIGIN": ORIGIN,
        "EASF_STORAGE_DIR": "/data/documents",
        "EASF_DATABASE_URL": (
            f"postgresql+psycopg://easf_app:{app_password}@{database}:5432/{db_name}"
        ),
        "EASF_MIGRATION_DATABASE_URL": (
            f"postgresql+psycopg://easf_owner:{owner_password}@{database}:5432/{db_name}"
        ),
        "EASF_NEW_USER_PASSWORD": user_password,
    }
    commands: list[dict] = []
    checks: list[dict] = []
    startup_observations: list[dict] = []
    cleanup: list[dict] = []
    created: list[str] = []
    users: list[str] = []
    network_created = False
    failure = None

    def redact(text: str) -> str:
        for value in credentials:
            text = text.replace(value, "[REDACTED]")
        return text

    def docker(*args: str, stdin: str | None = None, timeout: int = 90) -> str:
        # 引数に秘密の値を渡さず、必要な環境変数名だけをDockerへ指定する。
        result = subprocess.run(
            ["docker", *args],
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=timeout,
            check=False,
        )
        commands.append(
            {
                "args": list(args),
                "exit_code": result.returncode,
                "stdout": redact(result.stdout),
                "stderr": redact(result.stderr),
                "stdin_recorded": False,
            }
        )
        if result.returncode:
            raise RuntimeError(f"docker {args[0]}: exit {result.returncode}")
        return result.stdout.strip()

    def app_command(*args: str) -> str:
        return docker(
            "run",
            "--rm",
            "--network",
            network,
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--tmpfs",
            "/tmp:size=64m",
            "--env",
            "EASF_ENV",
            "--env",
            "EASF_SECRET_KEY",
            "--env",
            "EASF_DATABASE_URL",
            "--env",
            "EASF_MIGRATION_DATABASE_URL",
            "--env",
            "EASF_NEW_USER_PASSWORD",
            IMAGE,
            *args,
        )

    def expect(label: str, response: httpx.Response, status: int) -> None:
        checks.append(
            {"check": label, "expected": status, "actual": response.status_code}
        )
        assert response.status_code == status, (label, response.status_code)
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert "server" not in response.headers
        assert "x-trace-id" in response.headers
        if response.request.url.path.startswith("/api/"):
            assert response.headers["cache-control"] == "no-store"

    try:
        docker("version", "--format", "{{.Server.Version}}", timeout=30)
        before = docker("ps", "--format", "{{.ID}} {{.Names}}")
        docker("image", "inspect", IMAGE, "--format", "{{.Id}} {{.Config.User}}")
        docker("network", "create", network)
        network_created = True
        created.append(database)
        docker(
            "run",
            "-d",
            "--name",
            database,
            "--network",
            network,
            "--memory",
            "512m",
            "--cpus",
            "1",
            "--env",
            "POSTGRES_DB",
            "--env",
            "POSTGRES_USER",
            "--env",
            "POSTGRES_PASSWORD",
            "--tmpfs",
            "/var/lib/postgresql/data:size=256m",
            "postgres:17-alpine",
        )
        for attempt in range(30):
            try:
                docker(
                    "exec", database, "pg_isready", "-U", "easf_owner", "-d", db_name
                )
                break
            except RuntimeError:
                if attempt == 29:
                    raise
                time.sleep(1)
        # ランダムhexの値だけをSQL標準入力へ渡す。SQL本文は証跡に残さない。
        docker(
            "exec",
            "-i",
            database,
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            "easf_owner",
            "-d",
            db_name,
            stdin=(
                f"CREATE ROLE easf_app LOGIN PASSWORD '{app_password}';\n"
                f"GRANT CONNECT ON DATABASE {db_name} TO easf_app;\n"
                "GRANT USAGE ON SCHEMA public TO easf_app;\n"
                "ALTER DEFAULT PRIVILEGES FOR ROLE easf_owner IN SCHEMA public "
                "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO easf_app;\n"
                "ALTER DEFAULT PRIVILEGES FOR ROLE easf_owner IN SCHEMA public "
                "GRANT USAGE, SELECT ON SEQUENCES TO easf_app;\n"
                "REVOKE CREATE ON SCHEMA public FROM PUBLIC;\n"
            ),
        )
        app_command("alembic", "upgrade", "head")
        for role in ("owner", "outsider"):
            login = f"assess_{role}_{suffix}"
            options = ["--admin"] if role == "owner" else []
            app_command(
                "python",
                "-m",
                "app.admin",
                "create-user",
                "--login-id",
                login,
                "--display-name",
                "診断専用 TEST ONLY",
                *options,
            )
            users.append(login)
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            api_port = reservation.getsockname()[1]
        created.append(api)
        docker(
            "run",
            "-d",
            "--name",
            api,
            "--network",
            network,
            "--memory",
            "512m",
            "--cpus",
            "1",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--tmpfs",
            "/tmp:size=64m",
            "--tmpfs",
            "/data/documents:size=64m,uid=10001,mode=0700",
            "--publish",
            f"127.0.0.1:{api_port}:8000",
            "--env",
            "EASF_ENV",
            "--env",
            "EASF_DATABASE_URL",
            "--env",
            "EASF_SECRET_KEY",
            "--env",
            "EASF_SITE_ORIGIN",
            "--env",
            "EASF_STORAGE_DIR",
            IMAGE,
        )
        address = docker("port", api, "8000/tcp")
        assert address == f"127.0.0.1:{api_port}", "公開ポート情報の不一致"
        base = f"http://{address}"
        with (
            httpx.Client(base_url=base, timeout=30, trust_env=False) as owner,
            httpx.Client(base_url=base, timeout=30, trust_env=False) as outsider,
        ):
            for attempt in range(120):
                try:
                    status = owner.get("/health").status_code
                    startup_observations.append({"attempt": attempt, "status": status})
                    if status == 200:
                        break
                except httpx.TransportError as exc:
                    startup_observations.append(
                        {"attempt": attempt, "error_type": type(exc).__name__}
                    )
                if attempt == 119:
                    raise RuntimeError("API起動待ち上限")
                time.sleep(1)
            for path, status in (
                ("/health", 200),
                ("/ready", 200),
                ("/docs", 404),
                ("/redoc", 404),
                ("/openapi.json", 404),
                ("/.env", 404),
                ("/.git/config", 404),
                ("/api/v1/projects", 401),
            ):
                expect(path, owner.get(path), status)
            for client, login in zip((owner, outsider), users, strict=True):
                response = client.post(
                    "/api/v1/session",
                    headers={"Origin": ORIGIN},
                    json={"login_id": login, "password": user_password},
                )
                expect("診断利用者ログイン", response, 200)
                cookie = response.headers["set-cookie"].lower()
                assert "httponly" in cookie and "samesite=lax" in cookie
                client.headers.update(
                    {"Origin": ORIGIN, "X-CSRF-Token": response.json()["csrf_token"]}
                )
            payload = {"name": "診断専用 TEST ONLY", "business_domain": "assessment"}
            expect("認証後一覧", owner.get("/api/v1/projects"), 200)
            expect(
                "CSRFなし",
                owner.post(
                    "/api/v1/projects", json=payload, headers={"X-CSRF-Token": ""}
                ),
                403,
            )
            expect(
                "異なるOrigin",
                owner.post(
                    "/api/v1/projects",
                    json=payload,
                    headers={"Origin": "https://evil.example"},
                ),
                403,
            )
            response = owner.post("/api/v1/projects", json=payload)
            expect("案件作成", response, 201)
            project = response.json()["id"]
            expect("他案件参照拒否", outsider.get(f"/api/v1/projects/{project}"), 404)
            listing = outsider.get("/api/v1/projects")
            expect("他利用者一覧", listing, 200)
            assert project not in listing.text
            pdf = (ROOT / "fixtures/contract/dev/documents/con-0001.pdf").read_bytes()
            url = f"/api/v1/projects/{project}/documents"
            response = owner.post(
                url,
                files={"file": ("probe.pdf", b"<script>x</script>", "application/pdf")},
                data={"data_origin": "synthetic"},
            )
            expect("PDF偽装拒否", response, 415)
            response = owner.post(
                url,
                files={"file": ("../../probe.pdf", pdf, "application/pdf")},
                data={"data_origin": "synthetic"},
            )
            expect("dev合成PDF登録", response, 201)
            document = response.json()["id"]
            response = owner.get(f"/api/v1/documents/{document}/content")
            expect("認可付きダウンロード", response, 200)
            assert response.content == pdf
            assert response.headers["content-disposition"].startswith("attachment")
            expect(
                "他利用者の文書拒否",
                outsider.get(f"/api/v1/documents/{document}/content"),
                404,
            )
            expect("TRACE拒否", owner.request("TRACE", "/health"), 405)
            response = owner.get("/health", headers={"Origin": "https://evil.example"})
            assert "access-control-allow-origin" not in response.headers
            checks.append({"check": "異なるOriginへのCORS許可なし", "passed": True})
            expect("ログアウト", owner.delete("/api/v1/session"), 204)
            expect("ログアウト後拒否", owner.get("/api/v1/projects"), 401)
            (OUT / "http-summary.json").write_text(
                json.dumps(
                    {
                        "base_url": base,
                        "project_id": project,
                        "document_id": document,
                        "dev_pdf_sha256": hashlib.sha256(pdf).hexdigest(),
                        "checks": checks,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
    except (
        RuntimeError,
        AssertionError,
        OSError,
        ValueError,
        KeyError,
        httpx.HTTPError,
        subprocess.SubprocessError,
    ) as exc:
        # 応答本文・Cookie・トークンは記録しない。
        failure = redact(f"{type(exc).__name__}: {exc}")
    finally:
        if api in created:
            try:
                docker(
                    "inspect",
                    api,
                    "--format",
                    "{{.State.Status}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}}",
                    timeout=30,
                )
                docker("logs", "--tail", "80", api, timeout=30)
            except (RuntimeError, OSError, subprocess.SubprocessError):
                # 後始末を優先し、取得できない場合も成功にしない。
                cleanup.append({"api_observation_unavailable": True})
        for login in reversed(users):
            try:
                app_command(
                    "python", "-m", "app.admin", "deactivate-user", "--login-id", login
                )
                cleanup.append({"user": login, "deactivated": True})
            except (
                RuntimeError,
                AssertionError,
                OSError,
                ValueError,
                KeyError,
                httpx.HTTPError,
                subprocess.SubprocessError,
            ) as exc:
                cleanup.append({"user": login, "error_type": type(exc).__name__})
        for name in reversed(created):
            try:
                docker("rm", "--force", "--volumes", name, timeout=30)
                cleanup.append({"container": name, "removed": True})
            except (
                RuntimeError,
                AssertionError,
                OSError,
                ValueError,
                KeyError,
                httpx.HTTPError,
                subprocess.SubprocessError,
            ) as exc:
                cleanup.append({"container": name, "error_type": type(exc).__name__})
        if network_created:
            try:
                docker("network", "rm", network, timeout=30)
                cleanup.append({"network": network, "removed": True})
            except (
                RuntimeError,
                AssertionError,
                OSError,
                ValueError,
                KeyError,
                httpx.HTTPError,
                subprocess.SubprocessError,
            ) as exc:
                cleanup.append({"network": network, "error_type": type(exc).__name__})
        try:
            after = docker("ps", "--format", "{{.ID}} {{.Names}}")
            if "before" in locals():
                assert set(before.splitlines()) == set(after.splitlines())
                cleanup.append({"existing_container_ids_unchanged": True})
        except (
            RuntimeError,
            AssertionError,
            OSError,
            ValueError,
            KeyError,
            httpx.HTTPError,
            subprocess.SubprocessError,
        ) as exc:
            cleanup.append({"verification_error_type": type(exc).__name__})
        output = {
            "source_commit": "a0fe780dff1b63f9a1a6b128cdda9124421e8410",
            "image": IMAGE,
            "failure": failure,
            "checks": checks,
            "startup_observations": startup_observations,
            "commands": commands,
            "cleanup": cleanup,
        }
        (OUT / "execution.json").write_text(
            json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    failed_cleanup = any(
        "error_type" in row or "verification_error_type" in row for row in cleanup
    )
    print(
        f"checks={len(checks)}, failed={failure is not None}, cleanup_failed={failed_cleanup}"
    )
    return 1 if failure or failed_cleanup else 0


if __name__ == "__main__":
    raise SystemExit(main())
