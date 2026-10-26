"""ZAPが観測したメソッド・パス・状態だけを保存する。ヘッダ値は保存しない。"""

import json
from pathlib import Path
from urllib.parse import urlsplit


def zap_pre_shutdown(zap):
    messages = zap.core.messages(
        baseurl="http://host.docker.internal:8000", start=0, count=10000
    )
    rows = []
    for message in messages:
        request = message["requestHeader"].splitlines()
        response = message["responseHeader"].splitlines()
        if not request or not response:
            continue
        parts = request[0].split()
        status = response[0].split()
        if len(parts) < 2 or len(status) < 2 or not status[1].isdigit():
            continue
        rows.append(
            {
                "method": parts[0],
                "path": urlsplit(parts[1]).path,
                "status": int(status[1]),
                "cookie_present": any(
                    line.lower().startswith("cookie:") for line in request[1:]
                ),
            }
        )
    Path("/zap/wrk/request-evidence.json").write_text(
        json.dumps({"message_limit": 10000, "requests": rows}, indent=2) + "\n",
        encoding="utf-8",
    )


def pre_exit(fail_count, warn_count, pass_count):
    Path("/zap/wrk/counts.json").write_text(
        json.dumps({"fail": fail_count, "warn": warn_count, "pass": pass_count}) + "\n",
        encoding="utf-8",
    )
