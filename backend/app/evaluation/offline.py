"""Offline evaluation of a document workflow on a labeled split (ADR-007 metrics, easf-eval-integrity §4).

`python -m app.evaluation.offline --workflow W --rule-pack R --manifest M --split dev --out DIR`

The automatic part of the workflow (parse → extract → validate → locate) is run with the same capability
functions and the node configs of the workflow file; human review and export are not simulated. Nothing here
knows a business domain: field names, labels and rules come from the workflow, the Rule pack and the labels.
The dev split is evaluated from fixtures/. The holdout is evaluated by a person with `--split holdout --data-dir
<decrypted folder>`: every file must match the frozen manifest's hashes and only aggregates are written (no
sample ids, values or examples), which is all the AI may see (easf-eval-integrity §2).
"""

import argparse
import hashlib
import json
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from app.capabilities.document_parser import parse_document
from app.capabilities.evidence import locate
from app.capabilities.rule_extractor import extract_by_labels
from app.capabilities.rule_validator import validate_rules
from app.capabilities.values import nfkc

MEDIA = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
DETECTED = ("fail", "uncertain")  # ADR-007: sent to review counts as detected


def _config(workflow: dict[str, Any], capability_id: str) -> dict[str, Any]:
    config: dict[str, Any] = next(n["config"] for n in workflow["nodes"] if n["capability_id"] == capability_id)
    return config


def _same(predicted: Any, gold: Any) -> bool:
    """Normalized match: NFKC and trimmed strings; numbers compared as decimals."""
    if predicted is None or gold is None:
        return predicted is gold
    a, b = nfkc(str(predicted)).strip(), nfkc(str(gold)).strip()
    try:
        return Decimal(a) == Decimal(b)
    except InvalidOperation:
        return a == b


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load(sample: dict[str, Any], base: Path, split: str, data_dir: Path | None) -> tuple[dict[str, Any], bytes, str]:
    """Label, document bytes and file suffix. With data_dir (the holdout, kept outside the repository), both files
    must match the frozen manifest's hashes."""
    if data_dir is None:
        label_path = base / split / "labels" / f"{sample['sample_id']}.json"
        if not label_path.exists():
            raise SystemExit(f"labels for {sample['sample_id']} are not available (holdout labels never are)")
        label = json.loads(label_path.read_text(encoding="utf-8"))
        return label, (base / sample["source_file"]).read_bytes(), Path(sample["source_file"]).suffix.lower()
    label_bytes = (data_dir / "labels" / f"{sample['sample_id']}.json").read_bytes()
    label = json.loads(label_bytes)
    data = (data_dir / "documents" / Path(label["source_file"]).name).read_bytes()
    if _sha256(label_bytes) != sample["label_sha256"] or _sha256(data) != sample["source_file_sha256"]:
        raise SystemExit(f"{sample['sample_id']}: files do not match the frozen manifest")
    return label, data, Path(label["source_file"]).suffix.lower()


def aggregate_only(result: dict[str, Any]) -> dict[str, Any]:
    """What a person may give the AI from a holdout run: counts and rates, no sample ids, values or examples."""
    keys = ("dataset", "split", "samples", "manifest_sha256", "workflow", "rule_pack", "metrics", "per_field_match")
    return {**{k: result[k] for k in keys}, "rule_confusion": result["rule_confusion"]}


def evaluate(
    workflow: dict[str, Any], pack: dict[str, Any], manifest_path: Path, split: str, data_dir: Path | None = None
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = manifest_path.parent
    parse_cfg = _config(workflow, "document.parser")
    extract_cfg = _config(workflow, "document.rule_extractor")
    locate_cfg = _config(workflow, "document.evidence_locator")
    critical = {f["name"] for f in extract_cfg["field_spec"] if f["critical"]}
    severity = {r["rule_id"]: r["severity"] for r in pack["rules"]}

    seen: dict[str, list[Any]] = defaultdict(list)  # project context: values of earlier documents (in order)
    field_hits: dict[str, list[bool]] = defaultdict(list)
    status_hits: list[bool] = []
    silent_critical: list[dict[str, Any]] = []
    rule_rows: list[dict[str, Any]] = []
    spans_total = spans_correct = 0
    ocr_spans = ocr_spans_unverified = 0
    examples: list[dict[str, Any]] = []
    samples = [s for s in manifest["samples"] if s["split"] == split]
    if not samples:
        raise SystemExit(f"no labeled samples for split {split!r}")

    for sample in samples:
        label, data, suffix = _load(sample, base, split, data_dir)
        document_id = sample["sample_id"]
        parsed = parse_document(
            {"data": data, "media_type": MEDIA[suffix], "document_id": document_id,
             "sha256": hashlib.sha256(data).hexdigest()},
            parse_cfg,
        )  # fmt: skip
        extracted = extract_by_labels({"document_id": document_id, "pages": parsed["pages"]}, extract_cfg)
        fields, status = extracted["fields"], extracted["field_status"]
        context = {"snapshot_at": "1970-01-01T00:00:00Z", "values": {k: list(v) for k, v in seen.items()}}
        validated = validate_rules(
            {"fields": fields, "field_status": status, "project_context": context}, {"rule_pack": pack}
        )
        located = locate(document_id, parsed["pages"], fields, locate_cfg["match"])["evidence"]

        for name, gold_value in label["gold_fields"].items():
            if name not in fields:
                continue
            gold_status = label["gold_field_status"].get(name)
            status_hits.append(status[name] == gold_status)
            if gold_status == "found" and not isinstance(gold_value, list):
                hit = _same(fields[name], gold_value)
                field_hits[name].append(hit)
                if not hit:
                    examples.append(
                        {"sample_id": document_id, "stratum": sample["stratum"], "field": name,
                         "predicted": fields[name], "predicted_status": status[name], "gold": gold_value}
                    )  # fmt: skip
                    if name in critical and status[name] == "found":
                        silent_critical.append(examples[-1])
        for finding in label["gold_findings"]:
            predicted = next(f["result"] for f in validated["findings"] if f["rule_id"] == finding["rule_id"])
            rule_rows.append({"sample_id": document_id, "rule_id": finding["rule_id"],
                              "severity": severity.get(finding["rule_id"], finding["severity"]),
                              "gold": finding["result"], "predicted": predicted})  # fmt: skip
        ocr_pages = {p["page"] for p in parsed["pages"] if p["extraction_method"] != "text_layer"}
        for name, spans in located.items():
            gold_spans = label.get("gold_evidence", {}).get(name, [])
            for span in spans:
                if span["page"] in ocr_pages:
                    ocr_spans += 1
                    ocr_spans_unverified += span["status"] == "unverified"
                if span["status"] != "verified":
                    continue
                spans_total += 1
                spans_correct += any(
                    g["page"] == span["page"] and g["start"] < span["end"] and span["start"] < g["end"]
                    for g in gold_spans
                )
        for name, value in fields.items():
            if isinstance(value, str | int | float) and not isinstance(value, bool):
                seen[name].append(value)

    per_field = {name: sum(hits) / len(hits) for name, hits in sorted(field_hits.items()) if hits}
    critical_rules = [r for r in rule_rows if r["severity"] == "critical" and r["gold"] == "fail"]
    by_rule: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rule_rows:
        by_rule[row["rule_id"]][f"{row['gold']}->{row['predicted']}"] += 1
    return {
        "dataset": manifest["dataset"],
        "split": split,
        "samples": len(samples),
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "workflow": {"workflow_id": workflow["workflow_id"], "version": workflow["version"]},
        "rule_pack": f"{pack['rule_pack_id']}@{pack['version']}",
        "metrics": {
            "field_macro_normalized_match": sum(per_field.values()) / len(per_field) if per_field else None,
            "field_status_agreement": sum(status_hits) / len(status_hits) if status_hits else None,
            "critical_fields_wrong_but_found": len(silent_critical),
            "critical_rule_recall": (
                sum(r["predicted"] in DETECTED for r in critical_rules) / len(critical_rules)
                if critical_rules
                else None
            ),
            "critical_rule_positives": len(critical_rules),
            "evidence_position_accuracy": spans_correct / spans_total if spans_total else None,
            "evidence_spans": spans_total,
            "ocr_evidence_spans": ocr_spans,
            "ocr_evidence_all_unverified": ocr_spans == ocr_spans_unverified,
        },
        "per_field_match": per_field,
        "rule_confusion": {k: dict(v) for k, v in sorted(by_rule.items())},
        "missed_critical_rules": [r for r in critical_rules if r["predicted"] not in DETECTED],
        "field_errors": examples,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workflow", type=Path, required=True)
    parser.add_argument("--rule-pack", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--split", default="dev", choices=["dev", "holdout"])
    parser.add_argument("--data-dir", type=Path, help="holdout only: the decrypted folder outside the repository")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if (args.split == "holdout") != (args.data_dir is not None):
        raise SystemExit("--data-dir is required for the holdout and only for it")
    result = evaluate(
        json.loads(args.workflow.read_text(encoding="utf-8")),
        json.loads(args.rule_pack.read_text(encoding="utf-8")),
        args.manifest,
        args.split,
        args.data_dir,
    )
    if args.split == "holdout":
        result = aggregate_only(result)  # the AI only ever sees aggregates (easf-eval-integrity §2)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
