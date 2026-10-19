"""Container settings the assessment depends on (VA-G2-001)."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_api_container_is_read_only_with_a_writable_tmp_and_document_volume() -> None:
    api = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))["services"]["api"]
    assert api["read_only"] is True
    # Uploads over 1 MB are spooled to /tmp by the multipart parser: without it they fail with 500.
    assert any(entry.startswith("/tmp:") for entry in api["tmpfs"])  # noqa: S108  # reads the compose file only
    assert "easf_documents:/data/documents" in " ".join(api["volumes"])
    assert api["environment"]["EASF_STORAGE_DIR"] == "/data/documents"
