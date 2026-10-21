"""ローカル assessment API の手動診断補助。秘密は環境変数で受け、表示しない。"""

import json
import os
from pathlib import Path

import httpx2 as httpx
import yaml

ROOT = Path(__file__).resolve().parents[3]
BASE = "http://127.0.0.1:8001"
ORIGIN = "http://localhost:5173"


def main() -> None:
    with httpx.Client(base_url=BASE, timeout=60) as client:
        for path in ("/health", "/docs", "/redoc", "/openapi.json", "/.env", "/.git/config"):
            r = client.get(path)
            expected = 200 if path == "/health" else 404
            assert r.status_code == expected, (path, r.status_code)
            print(f"F-03 {path}: {r.status_code}")
        r = client.get("/api/v1/projects")
        assert r.status_code == 401
        assert r.headers["x-content-type-options"] == "nosniff"
        assert r.headers["x-frame-options"] == "DENY"
        assert r.headers["cache-control"] == "no-store"
        assert "server" not in r.headers
        print("B-10/F-02/F-06: 401, nosniff, DENY, no-store, Server なし")
        r = client.post("/api/v1/session", headers={"Origin": ORIGIN},
                        json={"login_id": os.environ["EASF_P406_LOGIN"], "password": os.environ["EASF_NEW_USER_PASSWORD"]})
        assert r.status_code == 200, r.status_code
        token = r.json()["csrf_token"]
        headers = {"Origin": ORIGIN, "X-CSRF-Token": token}
        assert client.post("/api/v1/projects", json={"name": "p406"},
                           headers={"Origin": ORIGIN}).status_code == 403
        assert client.post("/api/v1/projects", json={"name": "p406"},
                           headers={**headers, "Origin": "https://evil.example"}).status_code == 403
        print("D-01: CSRF なし・異なる Origin は 403")
        r = client.post("/api/v1/projects", json={"name": "P4-06 assessment", "business_domain": "assessment"},
                        headers=headers)
        assert r.status_code == 201, r.status_code
        project = r.json()["id"]
        url = f"/api/v1/projects/{project}/documents"
        pdf = (ROOT / "fixtures/contract/dev/documents/con-0001.pdf").read_bytes()
        r = client.post(url, headers=headers, files={"file": ("probe.pdf", b"<script>x</script>", "application/pdf")},
                        data={"data_origin": "synthetic"})
        assert r.status_code == 415, r.status_code
        print("E-01: HTML の PDF 偽装は 415")
        r = client.post(url, headers=headers, files={"file": ("../../probe.pdf", pdf, "application/pdf")},
                        data={"data_origin": "synthetic"})
        assert r.status_code == 201, r.status_code
        document = r.json()["id"]
        r = client.get(f"/api/v1/documents/{document}/content")
        assert r.status_code == 200, r.status_code
        assert r.content == pdf
        assert r.headers["content-disposition"].startswith("attachment")
        assert r.headers["x-content-type-options"] == "nosniff"
        print("A-04/E-04: 表示名の ../ は保存パスに使われず、認可付き attachment は元の PDF と一致")
        assert client.get("/health", headers={"Origin": "https://evil.example"}).headers.get(
            "access-control-allow-origin") is None
        assert client.request("TRACE", "/health").status_code == 405
        print("D-05/F-05: 異なる Origin に CORS 許可なし、TRACE は 405")
        # セッションは ZAP の実行中だけ一時ディレクトリに置く。報告には含めない。
        temp = Path(os.environ["EASF_P406_TEMP"])
        cookie = "; ".join(f"{k}={v}" for k, v in client.cookies.items())
        replacer = []
        for index, (name, value) in enumerate((("Cookie", cookie), ("X-CSRF-Token", token), ("Origin", ORIGIN))):
            for key, setting in {"description": name, "enabled": "true", "matchtype": "REQ_HEADER",
                                 "matchstr": name, "regex": "false", "replacement": value}.items():
                replacer.append(f"replacer.full_list({index}).{key}={setting}")
        (temp / "zap-auth.properties").write_text("\n".join(replacer), encoding="utf-8")
        spec = yaml.safe_load((ROOT / "contracts/openapi.yaml").read_text(encoding="utf-8"))
        spec["servers"] = [{"url": "http://api:8000"}]
        spec["paths"].pop("/api/v1/session", None)  # ログアウトによる診断セッションの無効化を避ける。
        (temp / "openapi-auth.json").write_text(json.dumps(spec), encoding="utf-8")
        print("認証付き ZAP の一時設定を作成（秘密の表示なし）")


if __name__ == "__main__":
    main()
