"""Generate synthetic invoices, gold labels and the manifest.

# dev (public seed), from the repository root:
PYTHONPATH=backend uv run --project backend python -m fixtures.generator dev
# holdout (a person only; secret seed, output outside the repository) — fixtures/HOLDOUT.md:
EASF_HOLDOUT_SEED=... PYTHONPATH=backend uv run --project backend python -m fixtures.generator holdout --out <dir>
# rule pack with the registered-payee table for every vendor:
PYTHONPATH=backend uv run --project backend python -m fixtures.generator rule-pack
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from app.capabilities.pdf_text import page_texts, span_sha256
from fixtures.generator.invoice import (
    BASE_DATE,
    DEV_SEED,
    GENERATOR_VERSION,
    PLAN_SEED,
    PlanItem,
    Record,
    build_plan,
    expected_findings,
    gold_fields,
    make_record,
)
from fixtures.generator.names import CUSTOMERS, VENDORS, denylisted
from fixtures.generator.render import Anchor, render_pdf, render_scan

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures"
POLICY_VERSION = "invoice@1.1.0"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, data: object, *, ascii_only: bool = False) -> None:
    """UTF-8 with LF line endings on every OS, so recorded hashes do not depend on where it was generated."""
    path.write_bytes((json.dumps(data, ensure_ascii=ascii_only, indent=2) + "\n").encode("utf-8"))


def locate(texts: list[str], anchor: Anchor) -> dict[str, Any]:
    """Gold evidence: the printed token right after its label, as offsets into the parser's page text."""
    text = texts[anchor.page - 1]
    label_at = text.find(anchor.label)
    start = text.find(anchor.token, label_at + len(anchor.label)) if label_at >= 0 else -1
    if label_at < 0 or start != label_at + len(anchor.label):
        raise RuntimeError(f"anchor not found as rendered: {anchor.field} on page {anchor.page}")
    end = start + len(anchor.token)
    return {"page": anchor.page, "start": start, "end": end, "text_sha256": span_sha256(text, start, end)}


def build_sample(item: PlanItem, record: Record) -> tuple[bytes, str, dict[str, Any]]:
    pdf, anchors = render_pdf(record)
    texts = page_texts(pdf)
    evidence: dict[str, list[dict[str, Any]]] = {}
    for anchor in anchors:
        evidence.setdefault(anchor.field, []).append(locate(texts, anchor))
    if "scan" in item.layout:
        content, media_type = render_scan(pdf, item.sample_id), "image/png"
        evidence = {}  # no text layer: evidence can only come from OCR and stays unverified
    else:
        content, media_type = pdf, "application/pdf"
    fields, status = gold_fields(record)
    label = {
        "sample_id": item.sample_id,
        "scenario": "invoice",
        "split": item.split,
        "stratum": item.stratum,
        "layout": list(item.layout),
        "planted": record.planted,
        "injection": record.injection,
        "duplicate_of": item.partner,
        "source_file": f"{item.sample_id}{'.png' if media_type == 'image/png' else '.pdf'}",
        "media_type": media_type,
        "source_file_sha256": sha256(content),
        "page_count": 1 if media_type == "image/png" else len(texts),
        "gold_fields": fields,
        "gold_field_status": status,
        "gold_findings": expected_findings(record),
        "gold_evidence": evidence,
        "policy_version": POLICY_VERSION,
        "generator_version": GENERATOR_VERSION,
        "annotator": "generator",
        "reviewed_by": None,
        "data_origin": "synthetic",
    }
    return content, media_type, label


def generate(split: str, seed: int | str, out: Path) -> list[dict[str, Any]]:
    plan = build_plan()
    records: dict[str, Record] = {}
    entries = []
    (out / "documents").mkdir(parents=True, exist_ok=True)
    (out / "labels").mkdir(parents=True, exist_ok=True)
    for item in plan:
        if item.split != split:
            continue
        partner = records[item.partner] if item.partner else None
        record = make_record(item, seed, partner)
        records[item.sample_id] = record
        content, _, label = build_sample(item, record)
        label_bytes = (json.dumps(label, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        (out / "documents" / label["source_file"]).write_bytes(content)
        (out / "labels" / f"{item.sample_id}.json").write_bytes(label_bytes)
        entries.append(
            {
                "sample_id": item.sample_id,
                "split": split,
                "stratum": item.stratum,
                "layout": list(item.layout),
                "source_file": f"{split}/documents/{label['source_file']}",  # relative to fixtures/
                "source_file_sha256": label["source_file_sha256"],
                "label_sha256": sha256(label_bytes),
            }
        )
    return entries


def check_names() -> None:
    names = [v.name for v in VENDORS] + [v.bank.name for v in VENDORS] + CUSTOMERS
    hits = {n: denylisted(n) for n in names if denylisted(n)}
    if hits:
        raise SystemExit(f"denylisted names: {hits}")


def rule_pack() -> dict[str, Any]:
    """invoice@1.1.0: same rules as 1.0.0, registered payees = every vendor of the generator (config-only change)."""
    base: dict[str, Any] = json.loads(
        (ROOT / "contracts" / "examples" / "rule_packs" / "invoice-1.0.0.json").read_text(encoding="utf-8")
    )
    base["version"] = "1.1.0"
    base["reference_tables"] = {
        "registered_payees": [{"vendor_name": v.name, "payee_account": v.account} for v in VENDORS]
    }
    return base


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m fixtures.generator")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("dev")
    holdout = sub.add_parser("holdout")
    holdout.add_argument("--out", required=True, type=Path)
    sub.add_parser("rule-pack")
    args = parser.parse_args(argv)
    check_names()

    if args.command == "rule-pack":
        path = FIXTURES / "rule_packs" / "invoice-1.1.0.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, rule_pack())
        print(path)
        return 0

    if args.command == "dev":
        entries = generate("dev", DEV_SEED, FIXTURES / "dev")
        holdout_ids = [i.sample_id for i in build_plan() if i.split == "holdout"]
        manifest = {
            "dataset": "invoice",
            "generator_version": GENERATOR_VERSION,
            "base_date": BASE_DATE.isoformat(),
            "plan_seed": PLAN_SEED,
            "dev_seed": DEV_SEED,
            "policy_version": POLICY_VERSION,
            "samples": entries,
            "holdout": {
                "sample_ids": holdout_ids,
                "manifest": "fixtures/manifest.holdout.json (generated by a person)",
            },
        }
        write_json(FIXTURES / "manifest.json", manifest)
        print(f"dev: {len(entries)} samples")
        return 0

    secret = os.environ.get("EASF_HOLDOUT_SEED")
    if not secret:
        print("EASF_HOLDOUT_SEED is not set", file=sys.stderr)
        return 2
    out: Path = args.out.resolve()
    if ROOT in out.parents or out == ROOT:
        print("holdout output must be outside the repository", file=sys.stderr)
        return 2
    entries = generate("holdout", secret, out)
    hashes = [
        {k: e[k] for k in ("sample_id", "split", "stratum", "source_file_sha256", "label_sha256")} for e in entries
    ]
    write_json(
        FIXTURES / "manifest.holdout.json",
        {"dataset": "invoice", "generator_version": GENERATOR_VERSION, "samples": hashes},
        ascii_only=True,
    )
    print(f"holdout: {len(entries)} samples written outside the repository; only hashes were recorded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
