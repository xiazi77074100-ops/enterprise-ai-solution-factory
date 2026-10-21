"""P4-03: the contract workflow end to end with the production handlers, and reuse evidence (AC-04, AC-06).

The contract workflow (fixtures/workflows/contract-v2.json) is configuration only. It runs the same registered
capability versions as the invoice workflow for parsing, rule validation, evidence, review and export; only the
extractor is a newer minor version (document.rule_extractor@1.1.0). The test proves it from the runs themselves.
"""

import csv
import io
import json
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.orm import Session

from app.executor.handlers import production_handlers
from tests.conftest import make_settings
from tests.integration.test_auth_projects import db, migrated  # noqa: F401  # shared fixtures
from tests.integration.test_invoice_workflow import _approve, _output, _run_to_review
from tests.integration.test_runs import Env, build_env

pytestmark = pytest.mark.db
ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = ROOT / "contracts" / "examples"
CONTRACT_WF: dict[str, Any] = json.loads((ROOT / "fixtures" / "workflows" / "contract-v2.json").read_text("utf-8"))
INVOICE_WF: dict[str, Any] = json.loads((ROOT / "fixtures" / "workflows" / "invoice-v3.json").read_text("utf-8"))
GOLD: dict[str, Any] = json.loads(
    (ROOT / "fixtures" / "contract" / "dev" / "labels" / "con-0001.json").read_text("utf-8")
)


@pytest.fixture
def env(db: Session, db_url: str, monkeypatch: pytest.MonkeyPatch) -> Env:  # noqa: F811
    e = build_env(db, db_url, monkeypatch, production_handlers(make_settings(database_url=db_url)))
    arch, h = e.as_("arch")
    for path in sorted((EXAMPLES / "capabilities").glob("*.json")):
        if path.name != "human_review.json":  # registered by build_env
            assert (
                arch.post("/api/v1/capabilities", json=json.loads(path.read_text("utf-8")), headers=h).status_code
                == 201
            )
    for pack in (
        ROOT / "fixtures" / "rule_packs" / "invoice-1.1.0.json",
        EXAMPLES / "rule_packs" / "contract-1.0.0.json",
    ):
        assert arch.post("/api/v1/rule-packs", json=json.loads(pack.read_text("utf-8")), headers=h).status_code == 201
    return e


def _upload(e: Env, folder: Path, name: str) -> str:
    client, h = e.as_("lead")
    res = client.post(
        f"/api/v1/projects/{e.project_id}/documents",
        files={"file": (name, (folder / name).read_bytes(), "application/pdf")},
        data={"data_origin": "synthetic"},
        headers=h,
    )
    assert res.status_code == 201, res.text
    document_id: str = res.json()["id"]
    return document_id


def test_contract_workflow_end_to_end(env: Env) -> None:
    sid = env.solution(CONTRACT_WF)
    run_id, task = _run_to_review(
        env, sid, _upload(env, ROOT / "fixtures" / "contract" / "dev" / "documents", "con-0001.pdf")
    )
    nodes = env.get(f"/api/v1/runs/{run_id}/nodes")
    assert {n["execution_mode"] for n in nodes} == {"real"}

    extract = _output(env, run_id, "extract")
    for field in ("party_a", "party_b", "effective_date", "end_date", "governing_law", "liability_cap_jpy"):
        assert str(extract["fields"][field]) == GOLD["gold_fields"][field], field
    assert extract["fields"]["auto_renewal"] is GOLD["gold_fields"]["auto_renewal"]
    findings = {f["rule_id"]: f["result"] for f in _output(env, run_id, "validate")["findings"]}
    assert findings == {g["rule_id"]: g["result"] for g in GOLD["gold_findings"]}  # incl. CON-003 on a boolean
    evidence = _output(env, run_id, "locate")["evidence"]
    span = evidence["party_a"][0]  # the preamble, not the signature block
    assert {k: span[k] for k in ("page", "start", "end", "text_sha256")} == GOLD["gold_evidence"]["party_a"][0]

    _approve(env, run_id, task)
    assert env.get(f"/api/v1/runs/{run_id}")["status"] == "succeeded"
    client, _ = env.as_("lead")
    rows = list(
        csv.reader(io.StringIO(client.get(f"/api/v1/runs/{run_id}/export?format=csv").content.decode("utf-8-sig")))
    )
    assert rows[0] == ["契約書レビュー結果"]
    assert ["ルール", "CON-001", "秘密保持条項がある：適合", "critical", "pass"] in rows


def test_contract_and_invoice_runs_share_capability_versions(env: Env) -> None:
    """AC-04 reuse evidence: the same capability_version_id ran in both workflows (by trace, not by claim)."""
    invoice_run, _ = _run_to_review(
        env, env.solution(INVOICE_WF), _upload(env, ROOT / "fixtures" / "dev" / "documents", "inv-0001.pdf")
    )
    contract_run, _ = _run_to_review(
        env,
        env.solution(CONTRACT_WF),
        _upload(env, ROOT / "fixtures" / "contract" / "dev" / "documents", "con-0001.pdf"),
    )
    versions = {}
    for run_id in (invoice_run, contract_run):
        versions[run_id] = {n["node_id"]: (n["capability_id"], n["capability_version"], n["capability_version_id"])
                            for n in env.get(f"/api/v1/runs/{run_id}/nodes")}  # fmt: skip
    for node in ("parse", "validate", "locate", "review"):
        assert versions[invoice_run][node] == versions[contract_run][node], node  # unchanged, config only
    assert versions[invoice_run]["extract"][1] == "1.0.0" and versions[contract_run]["extract"][1] == "1.1.0"


def _pinned(workflow: dict[str, Any]) -> dict[str, tuple[str, str]]:
    return {n["node_id"]: (n["capability_id"], n["capability_version"]) for n in workflow["nodes"]}


def test_requirement_change_cr1_is_configuration_only(env: Env) -> None:
    """AC-10 / CR-1: the anti-social-forces clause and CON-006 come from configuration (workflow v3, Rule pack
    contract@1.1.0) on exactly the same capability versions as v2; con-0001 has no such clause."""
    arch, h = env.as_("arch")
    pack = json.loads((ROOT / "fixtures" / "rule_packs" / "contract-1.1.0.json").read_text("utf-8"))
    assert arch.post("/api/v1/rule-packs", json=pack, headers=h).status_code == 201
    v3: dict[str, Any] = json.loads((ROOT / "fixtures" / "workflows" / "contract-v3.json").read_text("utf-8"))
    assert _pinned(v3) == _pinned(CONTRACT_WF)  # no new capability version for CR-1

    folder = ROOT / "fixtures" / "contract" / "dev" / "documents"
    run_id, _ = _run_to_review(env, env.solution(v3), _upload(env, folder, "con-0001.pdf"))
    extract = _output(env, run_id, "extract")
    assert extract["field_status"]["antisocial_exclusion"] == "missing"
    findings = {f["rule_id"]: f for f in _output(env, run_id, "validate")["findings"]}
    assert (findings["CON-006"]["result"], findings["CON-006"]["severity"]) == ("fail", "critical")
