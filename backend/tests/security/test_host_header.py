"""VA-005 (self-assessment 2026-10-18, ZAP): no redirect may build its Location from the Host header."""

from fastapi.testclient import TestClient


def test_trailing_slash_is_not_redirected_with_attacker_host(client: TestClient) -> None:
    res = client.get("/api/v1/projects/", headers={"Host": "evil.example"}, follow_redirects=False)
    assert res.status_code == 404
    assert "location" not in res.headers
