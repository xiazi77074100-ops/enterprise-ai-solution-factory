"""別案件・exporterを含むDB保存済みtraceによる再利用の確認。実画面や精度評価ではない。"""

import hashlib
import json
import os
import shutil
import tempfile
import uuid
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select

from app.core.db import make_session_factory
from app.executor.events import verify_chain
from app.executor.models import NodeRun, Run, RunEvent
from tests import conftest
from tests.conftest import make_settings
from tests.integration.test_auth_projects import db, migrated  # noqa: F401
from tests.integration.test_contract_workflow import _upload, env  # noqa: F401
from tests.integration.test_invoice_workflow import _approve, _run_to_review
from tests.integration.test_runs import Env

pytestmark = pytest.mark.db
ROOT = Path(__file__).resolve().parents[3]
SHARED = ("parse", "validate", "locate", "review", "export")


@pytest.fixture(autouse=True)
def isolated_document_storage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    original = Path(conftest.STORAGE_DIR)
    storage = tmp_path / "reuse-documents"
    monkeypatch.setattr(conftest, "STORAGE_DIR", str(storage))
    try:
        yield
    finally:
        resolved = storage.resolve()
        if resolved.parent != tmp_path.resolve() or resolved.name != "reuse-documents" or storage.is_symlink():
            raise RuntimeError("試験文書の削除範囲を確認できない")
        count = sum(1 for path in storage.rglob("*") if path.is_file())
        if storage.exists():
            shutil.rmtree(resolved)
        if os.environ.get("EASF_CAPTURE_REUSE_EVIDENCE") == "1":
            # 単独の診断プロセスでだけ、import時に作った未使用の空領域も回収する。
            if original.resolve().parent != Path(tempfile.gettempdir()).resolve() or not original.name.startswith(
                "easf-test-documents-"
            ):
                raise RuntimeError("未使用領域の範囲を確認できない")
            original.rmdir()  # 空でなければ失敗し、他の内容を削除しない。
            output = ROOT / "reports/review/2026-10-26-reuse/storage-cleanup.json"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(
                    {
                        "uploaded_files_removed": count,
                        "storage_removed": not storage.exists(),
                        "unused_default_removed": True,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )


def _second_project(e: Env) -> Env:
    admin, headers = e.as_("admin")
    response = admin.post(
        "/api/v1/projects", json={"name": "別案件の再利用検証", "business_domain": "合成データの検証"}, headers=headers
    )
    assert response.status_code == 201, response.text
    project = response.json()["id"]
    members = e.get(f"/api/v1/projects/{e.project_id}/members", who="admin")
    body = [{"user_id": member["user_id"], "roles": member["roles"]} for member in members]
    assert admin.put(f"/api/v1/projects/{project}/members", json=body, headers=headers).status_code == 200
    arch, ah = e.as_("arch")
    response = arch.post(f"/api/v1/projects/{project}/requirements", json={"content": "再利用検証用の要件"}, headers=ah)
    assert response.status_code == 201, response.text
    requirement = response.json()["id"]
    assert admin.post(f"/api/v1/requirements/{requirement}/approve", headers=headers).status_code == 200
    return replace(e, project_id=project, requirement_id=requirement)


def _snapshot(e: Env, run_id: str) -> dict[str, Any]:
    # 実行時のセッションを使わず、コミット済みの値を別セッションで読み直す。
    with make_session_factory(make_settings(database_url=e.db_url))() as session:
        run = session.get(Run, uuid.UUID(run_id))
        assert run is not None and run.status == "succeeded" and str(run.project_id) == e.project_id
        assert run.execution_mode == "real"
        nodes = list(session.scalars(select(NodeRun).where(NodeRun.run_id == run.id).order_by(NodeRun.position)))
        rows = list(session.scalars(select(RunEvent).where(RunEvent.run_id == run.id).order_by(RunEvent.seq)))
        assert verify_chain(session, run.id)
        assert len(nodes) == 6 and all(n.status == "succeeded" and n.execution_mode == "real" for n in nodes)
        completed = {row.event["node_id"]: row.event for row in rows if row.event["event_type"] == "node.completed"}
        for node in nodes:
            event = completed[node.node_id]
            assert event["capability_version_id"] == str(node.capability_version_id)
            assert event["project_id"] == e.project_id and event["run_id"] == run_id
        client, _ = e.as_("lead")
        exported = client.get(f"/api/v1/runs/{run_id}/export?format=json")
        assert exported.status_code == 200, exported.text
        export_node = next(n for n in nodes if n.node_id == "export")
        assert export_node.output is not None
        assert exported.json()["export_id"] == export_node.output["export_id"]
        api_nodes = {n["node_id"]: n for n in e.get(f"/api/v1/runs/{run_id}/nodes")}
        for node in nodes:
            assert api_nodes[node.node_id]["capability_version_id"] == str(node.capability_version_id)
        return {
            "project_id": e.project_id,
            "solution_id": str(run.solution_id),
            "run_id": run_id,
            "trace_id": run.trace_id,
            "workflow_hash": run.workflow_hash,
            "status": run.status,
            "execution_mode": run.execution_mode,
            "export_id": exported.json()["export_id"],
            "export_response_sha256": hashlib.sha256(exported.content).hexdigest(),
            "nodes": {
                n.node_id: {
                    "capability_id": api_nodes[n.node_id]["capability_id"],
                    "capability_version": api_nodes[n.node_id]["capability_version"],
                    "capability_version_id": str(n.capability_version_id),
                    "status": n.status,
                    "output_sha256": n.output_sha256,
                    "completed_event_id": completed[n.node_id]["event_id"],
                }
                for n in nodes
            },
            "trace_chain_verified": True,
            "events": [{"seq": row.seq, "event_hash": row.event_hash, "event": row.event} for row in rows],
        }


def test_two_projects_share_five_completed_capability_versions(env: Env) -> None:  # noqa: F811
    second = _second_project(env)
    arch, headers = env.as_("arch")
    pack_path = ROOT / "fixtures/rule_packs/contract-1.1.0.json"
    assert arch.post("/api/v1/rule-packs", json=json.loads(pack_path.read_bytes()), headers=headers).status_code == 201
    results = []
    for e, workflow, document in (
        (env, "invoice-v3.json", "fixtures/dev/documents/inv-0001.pdf"),
        (second, "contract-v3.json", "fixtures/contract/dev/documents/con-0001.pdf"),
    ):
        workflow_path = ROOT / "fixtures/workflows" / workflow
        document_path = ROOT / document
        solution = e.solution(json.loads(workflow_path.read_bytes()))
        run_id, task = _run_to_review(e, solution, _upload(e, document_path.parent, document_path.name))
        _approve(e, run_id, task)
        result = _snapshot(e, run_id)
        result["workflow_file"] = str(workflow_path.relative_to(ROOT)).replace("\\", "/")
        result["workflow_file_sha256"] = hashlib.sha256(workflow_path.read_bytes()).hexdigest()
        result["dev_document_file"] = document
        result["dev_document_sha256"] = hashlib.sha256(document_path.read_bytes()).hexdigest()
        results.append(result)
    first, other = results
    assert first["project_id"] != other["project_id"] and first["trace_id"] != other["trace_id"]
    for node in SHARED:
        assert first["nodes"][node]["capability_version_id"] == other["nodes"][node]["capability_version_id"], node
    assert first["nodes"]["extract"]["capability_version_id"] != other["nodes"]["extract"]["capability_version_id"]
    if os.environ.get("EASF_CAPTURE_REUSE_EVIDENCE") == "1":
        # 明示した診断時だけ固定の提出先へ保存。URL・Cookie・本文・抽出値は含めない。
        output = ROOT / "reports/review/2026-10-26-reuse/evidence.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        evidence = {
            "captured_at": datetime.now(UTC).isoformat(),
            "product_source_base": "012e996340d69c1d2ce6815d8eeceb2774e0c626",
            "test_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "implementation_manifest_sha256": hashlib.sha256(
                (ROOT / "backend/app/catalog/implementation_manifest.json").read_bytes()
            ).hexdigest(),
            "shared_nodes": list(SHARED),
            "runs": results,
        }
        output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
