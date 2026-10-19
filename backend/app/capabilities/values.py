"""Reading Japanese business values from document text (jp-dev-standards: dates, wareki, yen amounts).

Shared by the rule-based extractor (printed text -> normalized value) and the evidence locator (normalized
value -> the printed forms to look for). Values are strings: ISO dates and plain decimals without separators.
"""

import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation

ERAS = {"令和": 2018, "R": 2018, "平成": 1988, "H": 1988}
_ISO = re.compile(r"(\d{4})\s*[年/.\-]\s*(\d{1,2})\s*[月/.\-]\s*(\d{1,2})\s*日?")
_WAREKI = re.compile(r"(令和|平成|R|H)\s*(\d{1,2}|元)\s*[年.]\s*(\d{1,2})\s*[月.]\s*(\d{1,2})\s*日?")
_AMOUNT = re.compile(r"(-)?\s*[¥\\]?\s*(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?\s*円?")


def nfkc(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def _iso(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def parse_date(text: str) -> str | None:
    """First date in the text as ISO 8601 (Gregorian or Reiwa/Heisei), None if there is none."""
    text = nfkc(text)
    wareki = _WAREKI.search(text)
    if wareki:
        era, year, month, day = wareki.groups()
        return _iso(ERAS[era] + (1 if year == "元" else int(year)), int(month), int(day))
    found = _ISO.search(text)
    return _iso(int(found[1]), int(found[2]), int(found[3])) if found else None


def parse_amount(text: str) -> str | None:
    """First amount in the text as a plain decimal string ("¥94,600" -> "94600"), None if there is none."""
    found = _AMOUNT.search(nfkc(text))
    if not found:
        return None
    sign, digits, fraction = found.groups()
    try:
        value = Decimal((sign or "") + digits.replace(",", "") + (fraction or ""))
    except InvalidOperation:
        return None
    return format(value, "f")


def date_forms(iso: str) -> list[str]:
    """Printed forms of an ISO date that may appear in a document."""
    try:
        d = date.fromisoformat(iso)
    except ValueError:
        return []
    reiwa = d.year - 2018
    forms = [
        iso,
        f"{d.year}年{d.month}月{d.day}日",
        f"{d.year}/{d.month:02d}/{d.day:02d}",
        f"{d.year}/{d.month}/{d.day}",
    ]
    if reiwa >= 1:
        forms += [f"令和{reiwa}年{d.month}月{d.day}日", f"R{reiwa}.{d.month}.{d.day}"]
    return forms


def amount_forms(value: str) -> list[str]:
    """Printed forms of a plain decimal amount ("94600" -> "¥94,600", "94,600", ...)."""
    try:
        number = Decimal(value)
    except InvalidOperation:
        return []
    if number != number.to_integral_value():
        return [value]
    grouped = f"{abs(int(number)):,}"
    sign = "-" if number < 0 else ""
    return [f"{sign}¥{grouped}", f"{sign}￥{grouped}", f"{sign}{grouped}円", f"{sign}{grouped}", value]
