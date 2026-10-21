"""Score per-document outputs of either arm against the gold (P4-05; preregistration §5・§7・§8).

    python -m app.evaluation.score_outputs --outputs DIR --scoring ../experiment/contract_scoring.json \
        --manifest ../fixtures/contract/manifest.json --split dev --extra-labels labels_cr1 --out result.json

Both arms are scored by this one function from the same output format (experiment/baseline_bundle/requirements.md
§6: fields, field_status, findings, evidence with page + quote), so neither arm's internals matter. For the
holdout (`--split holdout --data-dir <decrypted folder>`) every file is checked against the frozen manifest and only
aggregates are written. Evidence is located in the parser's page text (pypdfium2): at the given start/end when the
quote is there, otherwise at the quote's first occurrence; a "verified" quote that is not in the text layer at all
(e.g. a scanned image) counts as a wrong position.
"""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.capabilities.pdf_text import page_texts
from app.evaluation.offline import DETECTED, _load, _merge_extra, _same, aggregate_only


def _position(texts: list[str], item: dict[str, Any]) -> tuple[int, int, int] | None:
    page, quote = item.get("page"), item.get("quote")
    if not isinstance(page, int) or not isinstance(quote, str) or not quote or not 1 <= page <= len(texts):
        return None
    text = texts[page - 1]
    start, end = item.get("start"), item.get("end")
    if isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(text) and text[start:end] == quote:
        return page, start, end
    at = text.find(quote)
    return (page, at, at + len(quote)) if at >= 0 else None


def score(
    outputs: Path,
    scoring: dict[str, Any],
    manifest_path: Path,
    split: str,
    data_dir: Path | None = None,
    extra_labels: str | None = None,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = manifest_path.parent
    critical_fields = set(scoring["critical_fields"])
    severity: dict[str, str] = scoring["rule_severity"]
    samples = [s for s in manifest["samples"] if s["split"] == split]
    if not samples:
        raise SystemExit(f"no labeled samples for split {split!r}")

    field_hits: dict[str, list[bool]] = defaultdict(list)
    status_hits: list[bool] = []
    silent: list[dict[str, Any]] = []
    rule_rows: list[dict[str, Any]] = []
    spans_total = spans_correct = unverified = missing_outputs = 0
    covered: list[bool] = []
    examples: list[dict[str, Any]] = []

    for sample in samples:
        label, data, suffix = _load(sample, base, split, data_dir)
        if extra_labels:
            _merge_extra(label, sample, base, split, data_dir, extra_labels)
        path = outputs / f"{sample['sample_id']}.json"
        if path.exists():
            out = json.loads(path.read_text(encoding="utf-8"))
        else:
            missing_outputs += 1
            out = {}
        fields, status = out.get("fields") or {}, out.get("field_status") or {}
        predicted_rules = {f.get("rule_id"): f.get("result") for f in out.get("findings") or []}
        texts = page_texts(data) if suffix == ".pdf" else []

        for name in scoring["fields"]:
            gold_value, gold_status = label["gold_fields"].get(name), label["gold_field_status"].get(name)
            value, state = fields.get(name), status.get(name, "missing")
            status_hits.append(state == gold_status)
            if gold_status == "found" and not isinstance(gold_value, list):
                hit = _same(value, gold_value)
                field_hits[name].append(hit)
                if not hit:
                    examples.append({"sample_id": sample["sample_id"], "field": name, "predicted": value,
                                     "predicted_status": state, "gold": gold_value})  # fmt: skip
            # A critical value shown as settled ("found") that is not the gold value is a silent error.
            if (
                name in critical_fields
                and state == "found"
                and not (gold_status == "found" and _same(value, gold_value))
            ):
                silent.append({"sample_id": sample["sample_id"], "field": name})
            gold_spans = label["gold_evidence"].get(name, [])
            correct_here = False
            for item in (out.get("evidence") or {}).get(name, []):
                if not item.get("verified"):
                    unverified += 1
                    continue
                spans_total += 1
                where = _position(texts, item)
                hit_span = where is not None and any(
                    g["page"] == where[0] and g["start"] < where[2] and where[1] < g["end"] for g in gold_spans
                )
                spans_correct += hit_span
                correct_here = correct_here or hit_span
            if gold_spans:
                covered.append(correct_here)

        for finding in label["gold_findings"]:
            rule_id = finding["rule_id"]
            rule_rows.append(
                {"rule_id": rule_id, "severity": severity.get(rule_id, finding["severity"]), "gold": finding["result"],
                 "predicted": predicted_rules.get(rule_id, "none"), "sample_id": sample["sample_id"]}
            )  # fmt: skip

    per_field = {name: sum(h) / len(h) for name, h in sorted(field_hits.items()) if h}
    critical_rules = [r for r in rule_rows if r["severity"] == "critical" and r["gold"] == "fail"]
    by_rule: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rule_rows:
        by_rule[row["rule_id"]][f"{row['gold']}->{row['predicted']}"] += 1
    return {
        "dataset": manifest["dataset"],
        "split": split,
        "samples": len(samples),
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "workflow": {"scored_outputs": outputs.name},
        "rule_pack": scoring["policy"],
        "metrics": {
            "field_macro_normalized_match": sum(per_field.values()) / len(per_field) if per_field else None,
            "field_status_agreement": sum(status_hits) / len(status_hits) if status_hits else None,
            "critical_fields_wrong_but_found": len(silent),
            "critical_rule_recall": (
                sum(r["predicted"] in DETECTED for r in critical_rules) / len(critical_rules)
                if critical_rules
                else None
            ),
            "critical_rule_positives": len(critical_rules),
            "evidence_position_accuracy": spans_correct / spans_total if spans_total else None,
            "evidence_spans": spans_total,
            "evidence_unverified_items": unverified,
            "evidence_coverage": sum(covered) / len(covered) if covered else None,
            "missing_outputs": missing_outputs,
        },
        "per_field_match": per_field,
        "rule_confusion": {k: dict(v) for k, v in sorted(by_rule.items())},
        "silent_critical_errors": silent,
        "missed_critical_rules": [r for r in critical_rules if r["predicted"] not in DETECTED],
        "field_errors": examples,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--scoring", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--split", default="dev", choices=["dev", "holdout"])
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--extra-labels")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if (args.split == "holdout") != (args.data_dir is not None):
        raise SystemExit("--data-dir is required for the holdout and only for it")
    result = score(
        args.outputs,
        json.loads(args.scoring.read_text(encoding="utf-8")),
        args.manifest,
        args.split,
        args.data_dir,
        args.extra_labels,
    )
    if args.split == "holdout":
        result = aggregate_only(result)  # sample ids, values and examples never leave the person's machine
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
