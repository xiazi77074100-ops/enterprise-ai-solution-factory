"""専用環境ヘルパーを再利用し、内部ネットワークでZAPを実行する。"""

import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
ZAP = "ghcr.io/zaproxy/zaproxy:2.16.1"
spec = importlib.util.spec_from_file_location(
    "assessment", OUT.parent / "http/assess.py"
)
assert spec is not None and spec.loader is not None
assessment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assessment)
assessment.OUT = OUT
assessment.SOURCE_COMMIT = "5db3134abe3b7d44bf1000120820d6452ca0ddfb"
assessment.RESOURCE_PREFIX = "easf-p503g"
assessment.DATABASE_NAME = "easf_p503g_test"


def scan(*, owner, network, api, project, document, credentials):
    del project, document
    credentials.extend(owner.cookies.values())
    credentials.append(owner.headers["X-CSRF-Token"])
    commands = []
    scanner_names = []
    scan_network = f"{network}-scan"
    results = []

    def redact(text):
        for value in credentials:
            text = text.replace(value, "[REDACTED]")
        return text

    def docker(*args, timeout=90, allowed=(0,)):
        result = subprocess.run(
            ["docker", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        commands.append(
            {
                "args": list(args),
                "exit_code": result.returncode,
                "stdout": redact(result.stdout),
                "stderr": redact(result.stderr),
            }
        )
        if result.returncode not in allowed:
            raise RuntimeError(f"ZAP docker {args[0]}: exit {result.returncode}")
        return result

    temp_parent = Path(tempfile.gettempdir()).resolve()
    temp = tempfile.TemporaryDirectory(prefix="easf-p503g-", dir=temp_parent)
    temp_path = Path(temp.name).resolve()
    assert temp_path.parent == temp_parent and temp_path.name.startswith("easf-p503g-")
    connected = False
    network_created = False
    try:
        docker("network", "create", "--internal", scan_network)
        network_created = True
        docker("network", "connect", scan_network, api)
        connected = True
        networks = json.loads(
            docker(
                "inspect", api, "--format", "{{json .NetworkSettings.Networks}}"
            ).stdout
        )
        address = networks[scan_network]["IPAddress"]
        assert re.fullmatch(r"\d+\.\d+\.\d+\.\d+", address)
        target = "http://host.docker.internal:8000"
        definition = yaml.safe_load(
            (ROOT / "contracts/openapi.yaml").read_text(encoding="utf-8")
        )
        definition["servers"] = [{"url": target}]
        for label in ("unauthenticated", "authenticated-passive"):
            work = temp_path / label
            work.mkdir()
            shutil.copyfile(OUT / "evidence_hook.py", work / "evidence_hook.py")
            (work / "openapi.json").write_text(json.dumps(definition), encoding="utf-8")
            config = [
                "autoupdate.checkOnStart=false",
                "autoupdate.downloadNewRelease=false",
                "ascan.threadPerHost=1",
                "ascan.maxScanDurationInMins=4",
                "ascan.maxRuleDurationInMins=1",
            ]
            if label == "authenticated-passive":
                cookie = "; ".join(f"{k}={v}" for k, v in owner.cookies.items())
                for index, (name, value) in enumerate(
                    (
                        ("Cookie", cookie),
                        ("X-CSRF-Token", owner.headers["X-CSRF-Token"]),
                        ("Origin", assessment.ORIGIN),
                    )
                ):
                    for key, setting in {
                        "description": name,
                        "enabled": "true",
                        "matchtype": "REQ_HEADER",
                        "matchstr": name,
                        "regex": "false",
                        "replacement": value,
                    }.items():
                        config.append(f"replacer.full_list({index}).{key}={setting}")
            (work / "scan.properties").write_text("\n".join(config), encoding="utf-8")
            scanner = f"{api}-zap-{label}"
            scanner_names.append(scanner)
            scan_args = (
                ["zap-api-scan.py", "-t", "/zap/wrk/openapi.json", "-f", "openapi"]
                if label == "unauthenticated"
                else [
                    "zap-baseline.py",
                    "--autooff",
                    "-t",
                    f"{target}/api/v1/projects",
                    "-m",
                    "1",
                ]
            )
            try:
                result = docker(
                    "run",
                    "--rm",
                    "--name",
                    scanner,
                    "--network",
                    scan_network,
                    "--add-host",
                    f"host.docker.internal:{address}",
                    "--memory",
                    "2g",
                    "--cpus",
                    "2",
                    "--cap-drop",
                    "ALL",
                    "--security-opt",
                    "no-new-privileges",
                    "-v",
                    f"{work}:/zap/wrk",
                    ZAP,
                    *scan_args,
                    "-T",
                    "3",
                    "-J",
                    "report.json",
                    "--hook",
                    "/zap/wrk/evidence_hook.py",
                    "-z",
                    "-configfile /zap/wrk/scan.properties",
                    timeout=600,
                    allowed=(0, 1, 2),
                )
                (OUT / f"{label}-run.txt").write_text(
                    redact(result.stdout + result.stderr), encoding="utf-8"
                )
            finally:
                docker("rm", "--force", scanner, allowed=(0, 1))
            for filename in ("report.json", "request-evidence.json", "counts.json"):
                source = work / filename
                if source.exists():
                    (OUT / f"{label}-{filename}").write_text(
                        redact(source.read_text(encoding="utf-8")), encoding="utf-8"
                    )
            counts = json.loads((work / "counts.json").read_text(encoding="utf-8"))
            evidence = json.loads(
                (work / "request-evidence.json").read_text(encoding="utf-8")
            )
            report = json.loads((work / "report.json").read_text(encoding="utf-8"))
            higher_risks = [
                alert["name"]
                for site in report.get("site", [])
                for alert in site.get("alerts", [])
                if int(alert.get("riskcode", "0")) >= 2
            ]
            reached = sum(
                row["path"] == "/api/v1/projects"
                and row["status"] == 200
                and row["cookie_present"]
                for row in evidence["requests"]
            )
            results.append(
                {
                    "label": label,
                    "exit_code": result.returncode,
                    "counts": counts,
                    "authenticated_projects_200": reached,
                    "medium_or_high_alerts": higher_risks,
                }
            )
            assert counts["fail"] == 0
            assert not higher_risks, "中以上のZAP指摘は要確認"
            if label == "authenticated-passive":
                assert reached > 0, "ZAP認証後到達の証拠なし"
    finally:
        cleanup_errors = []
        for scanner in scanner_names:
            try:
                docker("rm", "--force", scanner, allowed=(0, 1))
            except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
                cleanup_errors.append(type(exc).__name__)
        if connected:
            try:
                docker("network", "disconnect", scan_network, api)
            except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
                cleanup_errors.append(type(exc).__name__)
        if network_created:
            try:
                docker("network", "rm", scan_network)
            except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
                cleanup_errors.append(type(exc).__name__)
        assert temp_path.parent == temp_parent and temp_path.name.startswith(
            "easf-p503g-"
        )
        try:
            temp.cleanup()
        except OSError as exc:
            cleanup_errors.append(type(exc).__name__)
        (OUT / "zap-execution.json").write_text(
            json.dumps(
                {
                    "results": results,
                    "commands": commands,
                    "temporary_directory_removed": not temp_path.exists(),
                    "cleanup_errors": cleanup_errors,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        if cleanup_errors:
            raise RuntimeError("ZAP専用資源の後始末は要確認")


if __name__ == "__main__":
    raise SystemExit(assessment.main(after_checks=scan))
