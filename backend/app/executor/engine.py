"""Executor: run state machine, node execution and human review (run_execution.md §3〜§6, ADR-001).

Generic by construction: the workflow document and the pinned contracts decide everything. Nothing here
knows a business domain. A run never becomes `succeeded` while a node failed, a review is pending or was
rejected, the budget was exceeded, a node timed out or an output broke its schema (easf-capability-contract §1-5).
"""

import graphlib
import re
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from jsonschema import Draft202012Validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapters.base import TRANSIENT, AdapterResult, Handler
from app.catalog.models import CapabilityVersion
from app.catalog.validation import content_sha256
from app.core.errors import ApiError
from app.documents.models import Document
from app.executor.events import append_event
from app.executor.models import ZERO_USAGE, NodeRun, ReviewTask, Run
from app.project.models import ProjectMember
from app.solution.models import Solution

HUMAN_REVIEW = ("local", "human_review.v1")
HandlerTable = Mapping[tuple[str, str], Handler]
LEASE_MARGIN = timedelta(seconds=30)
MAX_ATTEMPTS = 3
CLAIMABLE = ("pending", "running")
FIELD_PATH = re.compile(r"^/fields/([^/]{1,100})$")


def now() -> datetime:
    return datetime.now(UTC)


def _must[T](value: T | None) -> T:
    """Rows that must exist by construction (foreign keys); a missing one is a bug, not user input."""
    if value is None:
        raise RuntimeError("missing row referenced by a foreign key")
    return value


def is_available(key: tuple[str, str], handlers: HandlerTable) -> bool:
    return key == HUMAN_REVIEW or key in handlers


def _key(contract: dict[str, Any]) -> tuple[str, str]:
    return (contract["kind"], contract["implementation"]["ref"])


def _pointer_get(document: Any, pointer: str) -> Any:
    """Value at a JSON Pointer; KeyError if it does not exist."""
    current = document
    for raw in pointer.split("/")[1:]:
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            raise KeyError(pointer)
    return current


def _summary(output: dict[str, Any]) -> dict[str, Any]:
    """Display-safe shape of an output: sizes and types only, never values."""
    return {
        key: len(value) if isinstance(value, list | dict) else type(value).__name__
        for key, value in list(output.items())[:30]
    }


def _schema_errors(schema: dict[str, Any], instance: Any) -> int:
    return sum(1 for _ in Draft202012Validator(schema).iter_errors(instance))


# --- start ------------------------------------------------------------------------------------------


def _workflow_contracts(db: Session, workflow: dict[str, Any]) -> dict[str, CapabilityVersion]:
    rows: dict[str, CapabilityVersion] = {}
    for node in workflow["nodes"]:
        row = db.execute(
            select(CapabilityVersion).where(
                CapabilityVersion.capability_id == node["capability_id"],
                CapabilityVersion.version == node["capability_version"],
            )
        ).scalar_one()
        rows[node["node_id"]] = row
    return rows


def _is_project_document(db: Session, project_id: uuid.UUID, value: Any) -> bool:
    """document_ref values must be documents of the run's project (others look the same as non-existent)."""
    try:
        document_id = uuid.UUID(value) if isinstance(value, str) and len(value) == 36 else None
    except ValueError:
        return False
    if document_id is None:
        return False
    document = db.get(Document, document_id)
    return document is not None and document.project_id == project_id


def _check_inputs(db: Session, project_id: uuid.UUID, workflow: dict[str, Any], inputs: dict[str, Any]) -> None:
    declared = {item["name"]: item["type"] for item in workflow["inputs"]}
    if set(inputs) != set(declared):
        raise ApiError("invalid_run_inputs", "入力の項目が解決策の定義と一致しません。", 422)
    for name, kind in declared.items():
        value = inputs[name]
        if kind == "document_ref":
            if not _is_project_document(db, project_id, value):
                raise ApiError("invalid_run_inputs", f"入力 {name} の文書が見つかりません。", 422)
            continue
        ok = {
            "string": isinstance(value, str),
            "integer": isinstance(value, int) and not isinstance(value, bool),
            "boolean": isinstance(value, bool),
        }[kind]
        if not ok or (isinstance(value, str) and len(value) > 10000):
            raise ApiError("invalid_run_inputs", f"入力 {name} の形式が正しくありません。", 422)


def start_run(
    db: Session,
    solution: Solution,
    user_id: uuid.UUID,
    inputs: dict[str, Any],
    idempotency_key: uuid.UUID,
    handlers: HandlerTable,
) -> tuple[Run, bool]:
    """Creates a pending run (or returns the one created with the same key). Returns (run, created)."""
    request_sha = content_sha256({"inputs": inputs})
    existing = db.execute(
        select(Run).where(
            Run.solution_id == solution.id, Run.created_by == user_id, Run.idempotency_key == idempotency_key
        )
    ).scalar_one_or_none()
    if existing is not None:
        if existing.request_sha256 != request_sha:
            raise ApiError("idempotency_conflict", "同じ冪等キーで異なる内容が送られました。", 409)
        return existing, False

    workflow = solution.workflow
    runnable = solution.state == "approved" or (
        solution.state == "validated" and not workflow.get("requires_human_approval", True)
    )
    if not runnable:
        raise ApiError("solution_not_runnable", "承認された解決策だけを実行できます。", 409)
    contracts = _workflow_contracts(db, workflow)
    if not all(is_available(_key(c.contract), handlers) for c in contracts.values()):
        raise ApiError("implementation_unavailable", "実装がまだない Capability を含むため実行できません。", 409)
    _check_inputs(db, solution.project_id, workflow, inputs)

    sorter: graphlib.TopologicalSorter[str] = graphlib.TopologicalSorter(
        {n["node_id"]: set() for n in workflow["nodes"]}
    )
    for edge in workflow["edges"]:
        sorter.add(edge["to"], edge["from"])
    order = list(sorter.static_order())

    run = Run(
        solution_id=solution.id,
        project_id=solution.project_id,
        workflow_hash=solution.workflow_hash,
        status="pending",
        execution_mode="real",
        trace_id=uuid.uuid4().hex,
        inputs=inputs,
        input_sha256=content_sha256(inputs),
        usage=dict(ZERO_USAGE),
        created_by=user_id,
        idempotency_key=idempotency_key,
        request_sha256=request_sha,
    )
    db.add(run)
    db.flush()
    for node in workflow["nodes"]:
        db.add(
            NodeRun(
                run_id=run.id,
                node_id=node["node_id"],
                position=order.index(node["node_id"]),
                capability_version_id=contracts[node["node_id"]].id,
                status="pending",
                execution_mode="real",
                attempt=1,
            )
        )
    append_event(
        db, run, "run.started", "pending", actor=("user", str(user_id)), metadata={"input_sha256": run.input_sha256}
    )
    return run, True


PROJECT_CONTEXT = "project_context"
MAX_CONTEXT_FIELDS = 50
MAX_CONTEXT_VALUES = 10_000


def _project_context(db: Session, run: Run) -> dict[str, Any]:
    """Reserved input (capability.schema project_context): reviewed values of earlier succeeded runs of the
    same project. Only runs created before this one count, so the snapshot does not change on retry."""
    rows = db.execute(
        select(NodeRun.output)
        .join(Run, Run.id == NodeRun.run_id)
        .join(CapabilityVersion, CapabilityVersion.id == NodeRun.capability_version_id)
        .where(
            Run.project_id == run.project_id,
            Run.status == "succeeded",
            Run.created_at < run.created_at,
            NodeRun.status == "succeeded",
            CapabilityVersion.kind == HUMAN_REVIEW[0],
            CapabilityVersion.contract["implementation"]["ref"].astext == HUMAN_REVIEW[1],
        )
        .order_by(Run.created_at, Run.id)
    ).scalars()
    values: dict[str, list[str | int | float]] = {}
    for output in rows:
        for name, value in ((output or {}).get("reviewed_fields") or {}).items():
            if isinstance(value, bool) or not isinstance(value, str | int | float):
                continue
            if name not in values and len(values) >= MAX_CONTEXT_FIELDS:
                continue
            bucket = values.setdefault(name, [])
            if len(bucket) < MAX_CONTEXT_VALUES:
                bucket.append(value)
    return {"snapshot_at": run.created_at.isoformat(), "values": values}


# --- worker -----------------------------------------------------------------------------------------


@dataclass
class _Step:
    """A node call prepared inside a transaction and executed outside it."""

    run_id: uuid.UUID
    node_run_id: uuid.UUID
    handler: Handler
    inputs: dict[str, Any]
    config: dict[str, Any]
    timeout_s: float
    budget_limited: bool  # the timeout was shortened to the remaining processing budget


class Executor:
    def __init__(self, session_factory: Callable[[], Session], handlers: HandlerTable) -> None:
        self.session_factory = session_factory
        self.handlers = handlers

    def run_until_idle(self, max_runs: int = 100) -> int:
        """Processes claimable runs until none is left (tests, single-shot workers). Returns the count."""
        done = 0
        while done < max_runs and self.run_once():
            done += 1
        return done

    def run_once(self) -> bool:
        run_id = self._claim()
        if run_id is None:
            return False
        while (step := self._advance(run_id)) is not None:
            started = time.monotonic()
            result = step.handler.invoke(step.inputs, step.config, step.timeout_s)
            self._record(step, result, int((time.monotonic() - started) * 1000))
        return True

    def _claim(self) -> uuid.UUID | None:
        with self.session_factory() as db:
            run = db.execute(
                select(Run)
                .where(
                    Run.status.in_(CLAIMABLE),
                    (Run.lease_until.is_(None)) | (Run.lease_until < now()),
                )
                .order_by(Run.created_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            ).scalar_one_or_none()
            if run is None:
                return None
            run.lease_until = now() + LEASE_MARGIN
            if run.status == "pending":
                run.status = "running"
                run.started_at = now()
            run_id = run.id
            db.commit()
            return run_id

    def _advance(self, run_id: uuid.UUID) -> _Step | None:
        """Moves the run forward until a node call is needed (returned) or the run pauses/ends (None)."""
        with self.session_factory() as db:
            run = db.execute(select(Run).where(Run.id == run_id).with_for_update()).scalar_one()
            if run.status != "running":
                return None
            solution = db.get(Solution, run.solution_id)
            if solution is None or solution.workflow_hash != run.workflow_hash:
                self._fail_run(db, run, "workflow_changed")
                db.commit()
                return None
            workflow = solution.workflow
            nodes = {
                n.node_id: n
                for n in db.execute(
                    select(NodeRun).where(NodeRun.run_id == run.id).order_by(NodeRun.position)
                ).scalars()
            }
            specs = {n["node_id"]: n for n in workflow["nodes"]}
            contracts = {n.node_id: db.get(CapabilityVersion, n.capability_version_id) for n in nodes.values()}

            for node in nodes.values():
                # A node still "running" means the previous worker stopped mid-call (crash, kill).
                interrupted = node.status == "running"
                if interrupted and not self._retry(
                    db, run, node, _must(contracts[node.node_id]).contract, "interrupted"
                ):
                    db.commit()
                    return None

            if self._processing_ms(nodes) >= workflow["budget"]["max_duration_ms"]:
                self._fail_run(db, run, "budget_exceeded")
                db.commit()
                return None

            predecessors: dict[str, set[str]] = {n: set() for n in nodes}
            for edge in workflow["edges"]:
                predecessors[edge["to"]].add(edge["from"])
            ready = next(
                (
                    n
                    for n in nodes.values()
                    if n.status == "pending" and all(nodes[p].status == "succeeded" for p in predecessors[n.node_id])
                ),
                None,
            )
            if ready is None:
                if all(n.status == "succeeded" for n in nodes.values()):
                    self._succeed_run(db, run, workflow, nodes)
                else:  # nothing runnable and not finished: a node is waiting for review
                    run.lease_until = None
                db.commit()
                return None

            contract_row = _must(contracts[ready.node_id])
            contract = contract_row.contract
            try:
                inputs = self._inputs(workflow, ready.node_id, run.inputs, nodes)
            except KeyError:
                inputs = None
            if inputs is not None and PROJECT_CONTEXT in contract["input_schema"].get("properties", {}):
                inputs[PROJECT_CONTEXT] = _project_context(db, run)
            if inputs is None or _schema_errors(contract["input_schema"], inputs):
                self._fail_node(db, run, ready, "invalid_input", contract_row.id)
                db.commit()
                return None
            ready.input_sha256 = content_sha256(inputs)

            if _key(contract) == HUMAN_REVIEW:
                self._request_review(db, run, ready, workflow, contracts, inputs)
                db.commit()
                return None

            handler = self.handlers.get(_key(contract))
            if handler is None:
                self._fail_node(db, run, ready, "implementation_unavailable", contract_row.id)
                db.commit()
                return None

            remaining_ms = workflow["budget"]["max_duration_ms"] - self._processing_ms(nodes)
            node_timeout_ms = min(
                specs[ready.node_id].get("timeout_ms", contract["timeout_ms"]), contract["timeout_ms"]
            )
            timeout_ms = min(node_timeout_ms, remaining_ms)
            ready.status = "running"
            ready.started_at = now()
            run.lease_until = now() + timedelta(milliseconds=timeout_ms) + LEASE_MARGIN
            append_event(
                db, run, "node.started", "pending", node_id=ready.node_id, capability_version_id=contract_row.id,
                metadata={"attempt": ready.attempt, "input_sha256": ready.input_sha256},
            )  # fmt: skip
            db.commit()
            return _Step(
                run.id,
                ready.id,
                handler,
                inputs,
                specs[ready.node_id]["config"],
                timeout_ms / 1000,
                budget_limited=remaining_ms < node_timeout_ms,
            )

    def _record(self, step: _Step, result: AdapterResult, duration_ms: int) -> None:
        with self.session_factory() as db:
            run = db.execute(select(Run).where(Run.id == step.run_id).with_for_update()).scalar_one()
            node = _must(db.get(NodeRun, step.node_run_id))
            contract_row = _must(db.get(CapabilityVersion, node.capability_version_id))
            contract = contract_row.contract
            workflow_budget = _must(db.get(Solution, run.solution_id)).workflow["budget"]

            node.duration_ms = (node.duration_ms or 0) + duration_ms
            node.execution_mode = result.execution_mode
            node.llm = result.llm
            usage = dict(run.usage)
            usage["llm_input_tokens"] += result.llm_input_tokens
            usage["llm_output_tokens"] += result.llm_output_tokens
            if result.cost_jpy is None:
                usage["cost_known"] = False
            else:
                usage["cost_jpy"] = float(usage["cost_jpy"] or 0) + float(result.cost_jpy)
            run.usage = usage
            self._update_mode(db, run)

            over_budget = (
                usage["llm_input_tokens"] + usage["llm_output_tokens"] > workflow_budget["max_llm_tokens"]
                or float(usage["cost_jpy"] or 0) > workflow_budget["max_cost_jpy"]
            )
            if result.status == "ok" and result.output is not None and not over_budget:
                if _schema_errors(contract["output_schema"], result.output):
                    self._fail_node(db, run, node, "invalid_output", contract_row.id)
                else:
                    node.status = "succeeded"
                    node.output = result.output
                    node.output_sha256 = content_sha256(result.output)
                    node.output_summary = _summary(result.output)
                    node.error_code = None
                    node.finished_at = now()
                    append_event(
                        db, run, "node.completed", "ok", node_id=node.node_id, capability_version_id=contract_row.id,
                        metadata={"output_sha256": node.output_sha256, "duration_ms": node.duration_ms,
                                  "attempt": node.attempt},
                    )  # fmt: skip
            elif over_budget or result.status == "timeout" and step.budget_limited:
                self._fail_node(db, run, node, "budget_exceeded", contract_row.id)
            elif result.status in TRANSIENT:
                self._retry(db, run, node, contract, result.error_code or result.status)
            else:
                self._fail_node(db, run, node, result.error_code or result.status, contract_row.id)
            if run.status == "running":
                run.lease_until = now() + LEASE_MARGIN
            db.commit()

    # --- state changes ----------------------------------------------------------------------------

    @staticmethod
    def _processing_ms(nodes: Mapping[str, NodeRun]) -> int:
        """Execution time used so far (human review time is not processing time)."""
        return sum(n.duration_ms or 0 for n in nodes.values())

    def _retry(self, db: Session, run: Run, node: NodeRun, contract: dict[str, Any], code: str) -> bool:
        """Schedules another attempt if the capability allows it; otherwise fails the run. True if retried."""
        retry = contract.get("retry", {})
        # retry.max_attempts counts retries (0..2); NodeRun.attempt counts attempts (1..3).
        allowed = min(1 + int(retry.get("max_attempts", 0)), MAX_ATTEMPTS)
        if retry.get("idempotent") and node.attempt < allowed:
            append_event(
                db, run, "node.failed", "failed", node_id=node.node_id,
                capability_version_id=node.capability_version_id,
                metadata={"error_code": code, "attempt": node.attempt, "will_retry": True},
            )  # fmt: skip
            node.attempt += 1
            node.status = "pending"
            node.started_at = None
            return True
        self._fail_node(db, run, node, code, node.capability_version_id)
        return False

    def _fail_node(self, db: Session, run: Run, node: NodeRun, code: str, capability_version_id: uuid.UUID) -> None:
        node.status = "failed"
        node.error_code = code
        node.finished_at = now()
        append_event(
            db, run, "node.failed", "failed", node_id=node.node_id, capability_version_id=capability_version_id,
            metadata={"error_code": code, "attempt": node.attempt, "will_retry": False},
        )  # fmt: skip
        self._fail_run(db, run, "timeout" if code == "timeout" else code if code in RUN_CODES else "node_failed")

    def _fail_run(self, db: Session, run: Run, code: str) -> None:
        self._skip_pending(db, run)
        run.status = "failed"
        run.failure_code = code
        run.finished_at = now()
        run.lease_until = None
        append_event(db, run, "run.failed", "failed", metadata={"failure_code": code})

    @staticmethod
    def _skip_pending(db: Session, run: Run) -> None:
        for node in db.execute(select(NodeRun).where(NodeRun.run_id == run.id, NodeRun.status == "pending")).scalars():
            node.status = "skipped"

    def _succeed_run(self, db: Session, run: Run, workflow: dict[str, Any], nodes: Mapping[str, NodeRun]) -> None:
        outputs: dict[str, Any] = {}
        for item in workflow["outputs"]:
            try:
                outputs[item["name"]] = _pointer_get(nodes[item["from_node"]].output, item["from_path"])
            except KeyError:
                self._fail_run(db, run, "invalid_output")
                return
        run.outputs = outputs
        run.status = "succeeded"
        run.finished_at = now()
        run.lease_until = None
        append_event(db, run, "run.completed", "ok", metadata={"output_sha256": content_sha256(outputs)})

    @staticmethod
    def _update_mode(db: Session, run: Run) -> None:
        modes = set(
            db.execute(
                select(NodeRun.execution_mode).where(NodeRun.run_id == run.id, NodeRun.started_at.is_not(None))
            ).scalars()
        )
        run.execution_mode = "mixed" if len(modes) > 1 else (modes.pop() if modes else "real")

    @staticmethod
    def _inputs(
        workflow: dict[str, Any], node_id: str, run_inputs: dict[str, Any], nodes: Mapping[str, NodeRun]
    ) -> dict[str, Any]:
        inputs: dict[str, Any] = {}
        for item in workflow["inputs"]:
            for target in item["to"]:
                if target["node_id"] == node_id:
                    inputs[target["field"]] = run_inputs[item["name"]]
        for edge in workflow["edges"]:
            if edge["to"] == node_id:
                for mapping in edge["mapping"]:
                    inputs[mapping["to_field"]] = _pointer_get(nodes[edge["from"]].output, mapping["from_path"])
        return inputs

    def _request_review(
        self,
        db: Session,
        run: Run,
        node: NodeRun,
        workflow: dict[str, Any],
        contracts: Mapping[str, CapabilityVersion | None],
        inputs: dict[str, Any],
    ) -> None:
        reviewer = _pick_reviewer(db, run.project_id)
        if reviewer is None:
            self._fail_node(db, run, node, "no_reviewer", node.capability_version_id)
            return
        origin = "parser"
        for edge in workflow["edges"]:
            source = contracts.get(edge["from"])
            if edge["to"] == node.node_id and any(m["to_field"] == "fields" for m in edge["mapping"]) and source:
                origin = "ai_draft" if source.kind == "llm" else "parser"
        items = review_items(inputs, origin)
        node.status = "waiting_review"
        node.started_at = now()
        node.execution_mode = "real"
        run.status = "waiting_review"
        run.lease_until = None
        self._update_mode(db, run)
        task = ReviewTask(
            run_id=run.id,
            node_run_id=node.id,
            node_id=node.node_id,
            project_id=run.project_id,
            status="pending",
            assigned_to=reviewer,
            items=items,
        )
        db.add(task)
        append_event(
            db, run, "review.requested", "pending", node_id=node.node_id,
            capability_version_id=node.capability_version_id, metadata={"item_count": len(items)},
        )  # fmt: skip


# Node failure codes that are also the run's failure_code; anything else becomes "node_failed".
RUN_CODES = frozenset(
    {"timeout", "budget_exceeded", "invalid_input", "invalid_output", "no_reviewer", "implementation_unavailable",
     "interrupted"}
)  # fmt: skip


def _pick_reviewer(db: Session, project_id: uuid.UUID) -> uuid.UUID | None:
    """The project's business_reviewer with the fewest pending reviews (ties: lowest user id)."""
    reviewers = list(
        db.execute(
            select(ProjectMember.user_id).where(
                ProjectMember.project_id == project_id, ProjectMember.roles.contains(["business_reviewer"])
            )
        ).scalars()
    )
    if not reviewers:
        return None
    pending = dict(
        db.execute(
            select(ReviewTask.assigned_to, func.count())
            .where(ReviewTask.status == "pending", ReviewTask.assigned_to.in_(reviewers))
            .group_by(ReviewTask.assigned_to)
        ).all()
    )
    return min(reviewers, key=lambda u: (pending.get(u, 0), str(u)))


def _escape(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def review_items(inputs: dict[str, Any], origin: str) -> list[dict[str, Any]]:
    """Generic review items: one per field (with its evidence) and one per rule finding (run_execution.md §6)."""
    evidence = inputs.get("evidence") if isinstance(inputs.get("evidence"), dict) else {}
    required = {"document_id", "page", "start", "end", "text_sha256", "status"}
    items: list[dict[str, Any]] = []
    for name, value in (inputs.get("fields") or {}).items():
        cited = [e for e in (evidence or {}).get(name, []) if isinstance(e, dict) and required <= set(e)][:10]
        items.append(
            {
                "path": f"/fields/{_escape(name)}"[:256],
                "label": name[:100],
                "proposed_value": value,
                "origin": origin,
                "evidence": [{k: e[k] for k in required} for e in cited],
                "flags": [],
            }
        )
    for i, finding in enumerate(inputs.get("findings") or []):
        items.append(
            {
                "path": f"/findings/{i}",
                "label": finding["rule_id"],
                "proposed_value": finding["message"],
                "origin": "rule",
                "evidence": [],
                "flags": [{k: finding[k] for k in ("rule_id", "severity", "result")}],
            }
        )
    return items[:200]


# --- review decision --------------------------------------------------------------------------------


def decide_review(
    db: Session,
    task: ReviewTask,
    user_id: uuid.UUID,
    decision: str,
    corrections: list[dict[str, Any]],
    comment: str | None,
    idempotency_key: uuid.UUID,
) -> ReviewTask:
    """Records the decision and resumes (approved) or stops (rejected) the run. Caller holds the task lock."""
    request_sha = content_sha256({"decision": decision, "corrections": corrections, "comment": comment})
    if task.status == "completed":
        if task.idempotency_key == idempotency_key and task.request_sha256 == request_sha:
            return task
        raise ApiError("already_decided", "この確認は決定済みです。", 409)
    run = db.execute(select(Run).where(Run.id == task.run_id).with_for_update()).scalar_one()
    node = _must(db.get(NodeRun, task.node_run_id))
    if run.status != "waiting_review" or node.status != "waiting_review":
        raise ApiError("run_not_waiting", "この実行は確認待ちではありません。", 409)

    fields = {item["label"]: item["proposed_value"] for item in task.items if item["path"].startswith("/fields/")}
    names = {item["path"]: item["label"] for item in task.items if item["path"].startswith("/fields/")}
    reviewed = dict(fields)
    seen: set[str] = set()
    for correction in corrections:
        path = correction["path"]
        if path not in names or path in seen or not FIELD_PATH.match(path):
            raise ApiError("invalid_correction_path", "修正できない項目が指定されています。", 422)
        seen.add(path)
        reviewed[names[path]] = correction["corrected_value"]

    contract_row = _must(db.get(CapabilityVersion, node.capability_version_id))
    output = {"reviewed_fields": reviewed, "decision": decision, "corrections": corrections}
    if _schema_errors(contract_row.contract["output_schema"], output):
        raise ApiError("invalid_review_output", "確認の結果が出力の形式に合いません。", 422)

    decided_at = now()
    task.status = "completed"
    task.decision = decision
    task.corrections = corrections
    task.comment = comment
    task.decided_by = user_id
    task.decided_at = decided_at
    task.idempotency_key = idempotency_key
    task.request_sha256 = request_sha
    correction_sha = content_sha256(
        [{"path": c["path"], "before": fields[names[c["path"]]], "after": c["corrected_value"]} for c in corrections]
    )
    append_event(
        db, run, "review.completed", "rejected" if decision == "rejected" else "ok", actor=("user", str(user_id)),
        node_id=node.node_id, capability_version_id=node.capability_version_id,
        metadata={"decision": decision, "correction_count": len(corrections), "corrections_sha256": correction_sha,
                  "corrected_paths": ",".join(sorted(seen))[:500]},
    )  # fmt: skip
    node.finished_at = decided_at
    node.duration_ms = 0
    if decision == "rejected":
        node.status = "failed"
        node.error_code = "rejected"
        Executor._skip_pending(db, run)
        run.status = "rejected"
        run.finished_at = decided_at
        run.lease_until = None
        append_event(db, run, "run.completed", "rejected", metadata={"failure_code": "rejected"})
    else:
        node.status = "succeeded"
        node.output = output
        node.output_sha256 = content_sha256(output)
        node.output_summary = _summary(output)
        append_event(
            db, run, "node.completed", "ok", node_id=node.node_id, capability_version_id=node.capability_version_id,
            metadata={"output_sha256": node.output_sha256},
        )  # fmt: skip
        run.status = "running"
        run.lease_until = None
    return task
