# 07 — Synthetic Test Data and Gold Set Specification

## Provenance
Use generated fictitious Japanese company names, invented T-registration-looking identifiers clearly marked TEST ONLY, fake bank details (never live account), fictional contracts, and fictional personal names. No real identifiable information, customer docs, real banking credentials or copyrighted templates without rights. Preserve fixture generator version and seed.

## Scenarios / sample matrix
For each scenario target 30–50 distinct documents across: normal, missing field/clause, ambiguous language, contradictory amounts/clauses, multi-page, rotated/scanned/low-quality, tables, Japanese era/date formats, OCR noise, duplicate labels, suspicious instructions embedded in document. Separate dev and holdout, stratify difficulty, freeze SHA-256 manifest before tuning.

## Invoice gold fields
vendor_name, invoice_no, issue_date, due_date, subtotal, tax, total, registration_no, payee_bank, payee_branch, payee_account (all fake), line_items, evidence spans; rule findings: total mismatch, missing registration, suspicious payee change, missing due date, duplicate invoice number (within synthetic fixture set). Explicit nullable/unknown states and normalization rules.

## Contract gold fields
party_a, party_b, effective_date, end_date, auto_renewal, confidentiality, liability_limit, termination_notice, governing_law, extracted clause citations; policy rule findings for missing required clauses, excessive liability, automatic renewal and missing notice. Policy packs are synthetic and NOT legal advice.

## Label format
`sample_id`, `scenario`, `split`, `source_file_sha256`, `gold_fields`, `gold_findings`, `gold_evidence` (page + offsets/text hash), `severity`, `annotator`, `reviewed_by`, `policy_version`. Two-pass review for critical labels where feasible. Keep held-out labels inaccessible to prompt/code-generation agents.

## Score reporting
Macro/micro field accuracy; per-critical-field miss rate; rule precision/recall by severity; evidence span correctness; review audit completeness; run success/error distribution; human minutes; LLM cost. Output examples of false positives/negatives, not just aggregate percentages. Pre-register thresholds at G0 and never edit after holdout evaluation.
