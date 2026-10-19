"""rule_validator.v1 (local): evaluates a Rule pack (contracts/rule_pack.schema.json) without eval.

Every rule yields pass / fail / uncertain. Three-valued logic: a referenced value that is null or missing
gives the rule's `on_missing` result; a value that cannot be compared (not a number, unknown format, no
project context) gives uncertain. Expressions nest at most 8 levels (the schema says so; enforced here too).
The Rule pack content is supplied by the worker-side handler (app/adapters/resources.py) in config.
"""

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

MAX_DEPTH = 8
FORMATS = {
    "jp_invoice_registration_no": re.compile(r"^T[0-9]{13}$"),
    "jp_bank_account_no": re.compile(r"^[0-9]{7}$"),
    "jp_postal_code": re.compile(r"^[0-9]{3}-[0-9]{4}$"),
    "iso_date": re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"),
}
# Wording per result for the finding message (pass is the default).
RESULT_JA = {"fail": "不適合", "uncertain": "判定できません（要確認）"}


class _MissingValueError(Exception):
    """A referenced value is null or absent."""


class _UndecidableError(Exception):
    """The value exists but the rule cannot decide (wrong type, no context)."""


def _pointer(document: Any, pointer: str) -> Any:
    current = document
    for raw in pointer.split("/")[1:]:
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit() and int(token) < len(current):
            current = current[int(token)]
        else:
            raise _MissingValueError
    if current is None or current == "":
        raise _MissingValueError
    return current


def _number(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise _UndecidableError
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise _UndecidableError from exc


class _Evaluator:
    def __init__(self, fields: dict[str, Any], pack: dict[str, Any], context: dict[str, Any] | None) -> None:
        self.fields = fields
        self.tables: dict[str, list[dict[str, Any]]] = pack.get("reference_tables", {})
        self.context = context

    def operand(self, node: dict[str, Any], depth: int) -> Any:
        if depth > MAX_DEPTH:
            raise _UndecidableError
        if "field" in node:
            return _pointer(self.fields, node["field"])
        if "const" in node:
            return node["const"]
        if "sum_of" in node:
            items = _pointer(self.fields, node["sum_of"])
            if not isinstance(items, list):
                raise _UndecidableError
            return sum((_number(item) for item in items), Decimal(0))
        return sum((_number(self.operand(item, depth + 1)) for item in node["add"]), Decimal(0))

    def compare(self, op: str, left: Any, right: Any) -> bool:
        if op in ("eq", "ne") and isinstance(left, str) and isinstance(right, str):
            return (left == right) == (op == "eq")
        a, b = _number(left), _number(right)
        return {"eq": a == b, "ne": a != b, "lt": a < b, "le": a <= b, "gt": a > b, "ge": a >= b}[op]

    def expr(self, node: dict[str, Any], depth: int = 1) -> bool | None:
        """True / False, or None when undecidable (missing values are raised as _MissingValueError)."""
        if depth > MAX_DEPTH:
            raise _UndecidableError
        op = node["op"]
        if op == "present":
            try:
                _pointer(self.fields, node["field"])
            except _MissingValueError:
                return False
            return True
        if op in ("and", "or", "not"):
            return self.logic(op, node, depth)
        if op in ("eq", "ne", "lt", "le", "gt", "ge"):
            return self.compare(op, self.operand(node["left"], depth + 1), self.operand(node["right"], depth + 1))
        if op == "abs_diff_le":
            left = _number(self.operand(node["left"], depth + 1))
            right = _number(self.operand(node["right"], depth + 1))
            return abs(left - right) <= _number(node["tolerance"])
        if op == "in":
            return _pointer(self.fields, node["field"]) in node["values"]
        if op == "format":
            value = _pointer(self.fields, node["field"])
            if not isinstance(value, str):
                raise _UndecidableError
            ok = bool(FORMATS[node["format"]].fullmatch(value))
            if ok and node["format"] == "iso_date":
                try:
                    date.fromisoformat(value)
                except ValueError:
                    return False
            return ok
        if op == "matches_reference":
            value = _pointer(self.fields, node["field"])
            key = _pointer(self.fields, node["key_field"])
            rows = [r for r in self.tables.get(node["table"], []) if r.get(node["match_field"]) == key]
            return any(r.get(node["value_field"]) == value for r in rows)
        if op == "unique_in_project":
            value = _pointer(self.fields, node["field"])
            if self.context is None:
                raise _UndecidableError
            seen = self.context["values"].get(node["field"].lstrip("/"), [])
            return value not in seen
        raise _UndecidableError  # an operator this version does not know: never pass

    def logic(self, op: str, node: dict[str, Any], depth: int) -> bool | None:
        if op == "not":
            inner = self._three(node["arg"], depth + 1)
            return None if inner is None else not inner
        results = [self._three(arg, depth + 1) for arg in node["args"]]
        decisive = op == "or"  # Kleene logic: or is decided by any True, and by any False
        if decisive in results:
            return decisive
        return None if None in results else not decisive

    def _three(self, node: dict[str, Any], depth: int) -> bool | None:
        try:
            return self.expr(node, depth)
        except (_MissingValueError, _UndecidableError):
            return None


def validate_rules(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    pack = config["rule_pack"]
    evaluator = _Evaluator(inputs["fields"], pack, inputs.get("project_context"))
    findings = []
    for rule in pack["rules"]:
        try:
            outcome = evaluator.expr(rule["check"])
            result = "uncertain" if outcome is None else ("pass" if outcome else "fail")
        except _MissingValueError:
            result = rule["on_missing"]
        except _UndecidableError:
            result = "uncertain"
        findings.append(
            {
                "rule_id": rule["rule_id"],
                "severity": rule["severity"],
                "result": result,
                "message": f"{rule['title']}：{RESULT_JA.get(result, '適合')}"[:500],
            }
        )
    requires_review = any(
        f["result"] == "fail" or (f["severity"] == "critical" and f["result"] != "pass") for f in findings
    )
    return {"findings": findings, "requires_review": requires_review}
