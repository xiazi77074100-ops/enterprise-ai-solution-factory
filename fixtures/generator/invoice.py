"""Synthetic invoices: plan → record (the single source of truth) → rendered document + gold label.

fixture_plan §2.1 (strata), §2.3 (layout), §5 (label format), §6 (dev / holdout), fixture-data §1・§2・§5.
Each sample has its own random stream seeded by (split seed, sample_id), so changing one sample never changes
another. Holdout records come from a secret seed known only to a person (fixtures/HOLDOUT.md).
"""

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from fixtures.generator.names import CUSTOMERS, INDUSTRY_ITEMS, INJECTIONS, PEOPLE, VENDORS, Vendor

GENERATOR_VERSION = "0.1.0"
BASE_DATE = date(2025, 4, 1)
PLAN_SEED = 20261019  # public: which sample is in which stratum / split / layout
DEV_SEED = 1101  # public (fixture_plan §6)
TAX_RATE_PERCENT = 10
RULE_IDS = ("INV-001", "INV-002", "INV-003", "INV-004", "INV-005", "INV-006")
SEVERITY = {"INV-001": "critical", "INV-002": "major", "INV-003": "major", "INV-004": "critical",
            "INV-005": "major", "INV-006": "major"}  # fmt: skip
FIELDS = ("vendor_name", "invoice_no", "issue_date", "due_date", "subtotal", "tax", "total", "registration_no",
          "payee_bank", "payee_branch", "payee_account", "line_items")  # fmt: skip

# (stratum, dev count, holdout count) — fixture_plan §1・§2.1・§8 (each rule ≥1 in holdout, critical ≥2).
STRATA = [
    ("normal", 8, 2),
    ("missing_registration", 3, 1),
    ("bad_registration_format", 2, 1),
    ("total_mismatch", 3, 2),
    ("payee_changed", 3, 2),
    ("missing_due_date", 3, 1),
    ("duplicate_invoice_no", 2, 1),
    ("ambiguous", 2, 1),
    ("injected_instruction", 2, 1),
]
LAYOUT_COUNTS = {"scan": 5, "multi_page": 6, "wareki": 8, "table_heavy": 8, "duplicate_label": 3}


@dataclass(frozen=True)
class PlanItem:
    sample_id: str
    stratum: str
    split: str
    layout: tuple[str, ...]
    partner: str | None = None  # duplicate_invoice_no: the earlier normal document it duplicates


def build_plan() -> list[PlanItem]:
    rng = random.Random(PLAN_SEED)  # noqa: S311  # reproducible synthetic data, not security
    rows: list[tuple[str, str]] = []
    for stratum, dev, holdout in STRATA:
        rows += [(stratum, "dev")] * dev + [(stratum, "holdout")] * holdout
    ids = [f"inv-{i + 1:04d}" for i in range(len(rows))]
    layouts: dict[str, set[str]] = {sid: set() for sid in ids}
    for name, count in LAYOUT_COUNTS.items():
        candidates = [sid for sid in ids if not ({"scan", "multi_page"} <= layouts[sid] | {name})]
        for sid in rng.sample(candidates, count):
            layouts[sid].add(name)
    plan: list[PlanItem] = []
    normals = {split: [sid for sid, (s, sp) in zip(ids, rows, strict=True) if s == "normal" and sp == split]
               for split in ("dev", "holdout")}  # fmt: skip
    used: dict[str, int] = {"dev": 0, "holdout": 0}
    for sid, (stratum, split) in zip(ids, rows, strict=True):
        partner = None
        if stratum == "duplicate_invoice_no":  # pairs stay in the same split (fixture_plan §1)
            partner = normals[split][used[split]]
            used[split] += 1
        plan.append(PlanItem(sid, stratum, split, tuple(sorted(layouts[sid])), partner))
    return plan


@dataclass
class Record:
    """Everything the rendered document says, plus what was planted and what the rules must conclude."""

    plan: PlanItem
    vendor: Vendor
    customer: str
    contact: str
    invoice_no: str
    issue_date: date
    due_date: date | None
    items: list[dict[str, Any]]
    subtotal: int
    tax: int
    total: int  # as printed (may be planted to mismatch)
    second_total: int | None  # ambiguous: a second, different amount labeled as the total
    registration_no: str | None  # as printed
    payee_account: str  # as printed
    injection: int | None  # index into INJECTIONS
    planted: list[str] = field(default_factory=list)
    date_style: str = "western"


def _rng(seed: int | str, sample_id: str) -> random.Random:
    return random.Random(f"{seed}:{sample_id}")  # noqa: S311  # reproducible synthetic data, not security


def make_record(item: PlanItem, seed: int | str, partner: "Record | None") -> Record:
    rng = _rng(seed, item.sample_id)
    vendor = partner.vendor if partner else VENDORS[rng.randrange(len(VENDORS))]
    customer = CUSTOMERS[rng.randrange(len(CUSTOMERS))]
    contact = PEOPLE[rng.randrange(len(PEOPLE))]
    issue = BASE_DATE + timedelta(days=rng.randrange(0, 300))
    due = issue + timedelta(days=rng.choice([30, 45, 60]))
    n_items = rng.randint(10, 14) if "table_heavy" in item.layout else rng.randint(2, 5)
    catalog = INDUSTRY_ITEMS[vendor.industry]
    items: list[dict[str, Any]] = []
    for _ in range(n_items):
        name, price = catalog[rng.randrange(len(catalog))]
        qty = rng.randint(1, 12)
        items.append({"description": name, "quantity": qty, "unit_price": price, "amount": qty * price})
    subtotal = sum(i["amount"] for i in items)
    tax = subtotal * TAX_RATE_PERCENT // 100
    # Draw every random value even when unused, so later draws do not shift (fixture-data §5).
    delta = rng.choice([1, 10, 100, 1000, 4800]) * rng.choice([1, -1])
    other_account = f"{rng.randrange(10**7):07d}"
    injection_index = rng.randrange(len(INJECTIONS))
    injection_target = rng.choice(["total_mismatch", "payee_changed"])
    bad_style = rng.choice(["no_t", "short"])
    date_style = (
        rng.choice(["wareki_kanji", "wareki_r"]) if "wareki" in item.layout else rng.choice(["western", "slash"])
    )
    invoice_no = partner.invoice_no if partner else f"{rng.randrange(2025, 2026)}-{rng.randrange(10000):04d}"

    record = Record(
        plan=item,
        vendor=vendor,
        customer=customer,
        contact=contact,
        invoice_no=invoice_no,
        issue_date=issue,
        due_date=due,
        items=items,
        subtotal=subtotal,
        tax=tax,
        total=subtotal + tax,
        second_total=None,
        registration_no=vendor.registration_no,
        payee_account=vendor.account,
        injection=None,
        date_style=date_style,
    )
    plants = {item.stratum}
    if item.stratum == "injected_instruction":
        record.injection = injection_index
        plants.add(injection_target)
    if "missing_registration" in plants:
        record.registration_no = None
    if "bad_registration_format" in plants:
        digits = vendor.registration_no[1:]
        record.registration_no = digits if bad_style == "no_t" else "T" + digits[:12]
    if "total_mismatch" in plants:
        record.total = subtotal + tax + delta
    if "payee_changed" in plants:
        record.payee_account = (
            other_account if other_account != vendor.account else f"{(int(other_account) + 1) % 10**7:07d}"
        )
    if "missing_due_date" in plants:
        record.due_date = None
    if "ambiguous" in plants:
        record.second_total = subtotal + tax + abs(delta)
    record.planted = sorted(plants - {"normal"})
    return record


def expected_findings(record: Record) -> list[dict[str, str]]:
    """Gold rule results for INV-001〜006 (rule pack invoice@1.1.0)."""
    planted = set(record.planted)
    result = dict.fromkeys(RULE_IDS, "pass")
    if "total_mismatch" in planted:
        result["INV-001"] = "fail"
    if "ambiguous" in planted:
        result["INV-001"] = "uncertain"
    if "missing_registration" in planted:
        result["INV-002"] = "fail"
        result["INV-003"] = "uncertain"
    if "bad_registration_format" in planted:
        result["INV-003"] = "fail"
    if "payee_changed" in planted:
        result["INV-004"] = "fail"
    if "missing_due_date" in planted:
        result["INV-005"] = "fail"
    if "duplicate_invoice_no" in planted:
        result["INV-006"] = "fail"
    return [{"rule_id": r, "result": result[r], "severity": SEVERITY[r]} for r in RULE_IDS]


def format_date(d: date, style: str) -> str:
    if style == "wareki_kanji":
        return f"令和{d.year - 2018}年{d.month}月{d.day}日"
    if style == "wareki_r":
        return f"R{d.year - 2018}.{d.month}.{d.day}"
    if style == "slash":
        return f"{d.year}/{d.month:02d}/{d.day:02d}"
    return f"{d.year}年{d.month}月{d.day}日"


def yen(amount: int) -> str:
    return f"¥{amount:,}" if amount >= 0 else f"-¥{-amount:,}"


def gold_fields(record: Record) -> tuple[dict[str, Any], dict[str, str]]:
    """Values a perfect extractor returns (strings for money and ISO dates), and found/missing/uncertain."""
    fields: dict[str, Any] = {
        "vendor_name": record.vendor.name,
        "invoice_no": record.invoice_no,
        "issue_date": record.issue_date.isoformat(),
        "due_date": record.due_date.isoformat() if record.due_date else None,
        "subtotal": str(record.subtotal),
        "tax": str(record.tax),
        "total": str(record.total) if record.second_total is None else None,
        "registration_no": record.registration_no,
        "payee_bank": record.vendor.bank.name,
        "payee_branch": record.vendor.bank.branch,
        "payee_account": record.payee_account,
        "line_items": [{k: str(v) for k, v in item.items()} for item in record.items],
    }
    status = {name: "found" for name in FIELDS}
    if record.due_date is None:
        status["due_date"] = "missing"
    if record.registration_no is None:
        status["registration_no"] = "missing"
    if record.second_total is not None:
        status["total"] = "uncertain"
    return fields, status
