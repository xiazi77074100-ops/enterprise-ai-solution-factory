"""Render a contract Record as an A4 PDF (same font and invariant mode as the invoices; D-028・D-029).

Paragraphs are wrapped to the page width, but a gold value is never split across lines, so its evidence is one
range in the parser's page text (app.capabilities.pdf_text). The renderer returns, for each gold value, the line
it was drawn on and its offset in that line; the generator then locates the line in the extracted text.
"""

from dataclasses import dataclass

from fixtures.generator.contract import INJECTIONS, Record
from fixtures.generator.invoice import format_date
from fixtures.generator.render import FONT, LEFT, RIGHT, _Doc

MARK = "TEST ONLY／合成データ（架空の契約書です。実在の契約ではありません。法的助言ではありません）"
KANJI = "〇一二三四五六七八九十"


@dataclass(frozen=True)
class LineAnchor:
    field: str
    page: int  # 1-based
    line: str  # the whole line as drawn
    offset: int  # where the token starts in the line
    token: str


class _ContractDoc(_Doc):
    def __init__(self, size: float, gap: float) -> None:
        self.size, self.gap = size, gap
        self.line_anchors: list[LineAnchor] = []
        super().__init__()

    def _footer(self) -> None:
        self.canvas.setFont(FONT, 8)
        self.canvas.drawString(LEFT, 30, MARK)
        self.canvas.drawRightString(RIGHT, 30, f"{self.page} ページ")

    def para(self, *parts: str | tuple[str, str], indent: float = 0, size: float | None = None) -> None:
        """Draws text wrapped to the width. A (field, token) part is kept whole on one line and anchored."""
        size = size or self.size
        limit = (RIGHT - LEFT - indent) / size  # in full-width characters
        lines: list[tuple[str, list[tuple[str, int, str]]]] = []
        current, width = "", 0.0
        anchors: list[tuple[str, int, str]] = []

        def flush() -> None:
            nonlocal current, width, anchors
            if current:
                lines.append((current, anchors))
            current, width, anchors = "", 0.0, []

        for part in parts:
            if isinstance(part, tuple):
                field, token = part
                if width + _width(token) > limit:
                    flush()
                anchors.append((field, len(current), token))
                current += token
                width += _width(token)
                continue
            for char in part:
                if width + _width(char) > limit:
                    flush()
                current += char
                width += _width(char)
        flush()
        for text, line_anchors in lines:
            self.line(text, size, LEFT + indent, self.gap)
            for field, offset, token in line_anchors:
                self.line_anchors.append(LineAnchor(field, self.page, text, offset, token))


def _width(text: str) -> float:
    return sum(0.5 if ord(ch) < 0x2000 else 1.0 for ch in text)


def heading(numbering: str, number: int, title: str) -> str:
    if numbering == "article":
        return f"第{number}条（{title}）"
    if numbering == "arabic":
        return f"{number}.（{title}）"
    return f"{KANJI[number] if number <= 10 else '十' + KANJI[number - 10]}、{title}"


def amount(value: int, style: str) -> str:
    return f"{value:,}円" if style == "yen" else f"{value // 10_000:,}万円"


def render_pdf(record: Record) -> tuple[bytes, list[LineAnchor], dict[str, str]]:
    """PDF bytes, anchors of the gold values, and the printed headings of the clauses gold labels refer to."""
    multi = "multi_page" in record.plan.layout
    doc = _ContractDoc(size=10.5 if multi else 9, gap=17 if multi else 13)
    style = record.date_style
    headings: dict[str, str] = {}
    number = 0

    def article(title: str, key: str | None = None) -> None:
        nonlocal number
        number += 1
        text = heading(record.plan.numbering, number, title)
        if key:
            headings[key] = text
            doc.para((key, text), size=doc.size + 0.5)
        else:
            doc.para(text, size=doc.size + 0.5)

    doc.line(record.title, size=16, gap=28)
    doc.para(
        ("party_a", record.party_a), "（以下「甲」という。）と", ("party_b", record.party_b),
        "（以下「乙」という。）は、次のとおり契約（以下「本契約」という。）を締結する。",
    )  # fmt: skip
    article("目的")
    doc.para(f"甲は、乙に対し、{record.service}（以下「本業務」という。）を委託し、乙はこれを受託する。", indent=10)
    if "duplicate_label" in record.plan.layout:
        article("定義")
        doc.para("本契約において「契約期間」とは、本契約に定める有効期間をいい、更新後の期間を含む。", indent=10)
    article("委託料")
    doc.para(f"甲は、乙に対し、本業務の対価として月額金{record.monthly_fee:,}円（消費税別）を支払う。", indent=10)
    article("契約期間")
    doc.para(
        "本契約の有効期間は、", ("effective_date", format_date(record.effective, style)), "から",
        ("end_date", format_date(record.end, style)), "までとする。", indent=10,
    )  # fmt: skip
    if record.auto_renewal:
        doc.para(
            "期間満了の1か月前までにいずれの当事者からも書面による申出がないときは、本契約は",
            ("auto_renewal", "同一条件でさらに1年間更新"), "されるものとし、以後も同様とする。", indent=10,
        )  # fmt: skip
    else:
        doc.para("本契約は、期間満了をもって終了し、", ("auto_renewal", "自動更新はしない"), "。", indent=10)
    if record.confidentiality:
        article("秘密保持", "confidentiality")
        doc.para(
            "甲及び乙は、本契約に関して知り得た相手方の技術上又は営業上の情報を、相手方の書面による事前の承諾"
            "なく第三者に開示し、又は漏えいしてはならない。",
            indent=10,
        )
    if multi:
        article("再委託の禁止")
        doc.para("乙は、甲の書面による事前の承諾なく、本業務の全部又は一部を第三者に再委託してはならない。", indent=10)
        article("知的財産権")
        doc.para("本業務の遂行により生じた成果物の著作権は、委託料の支払の完了をもって甲に移転する。", indent=10)
    article("損害賠償")
    doc.para("甲又は乙は、本契約に違反して相手方に損害を与えたときは、その損害を賠償する。", indent=10)
    if record.cap_ambiguous:
        doc.para("ただし、賠償額の上限については、甲乙別途協議のうえ定める。", indent=10)
    elif record.liability_cap is not None:
        doc.para(
            "ただし、賠償額の上限は、金", ("liability_cap_jpy", amount(record.liability_cap, record.amount_style)),
            "とする。", indent=10,
        )  # fmt: skip
    if record.plan.antisocial:
        article("反社会的勢力の排除", "antisocial")
        doc.para(
            "甲及び乙は、自らが暴力団、暴力団員その他の反社会的勢力に該当しないことを表明し、相手方がこれに違反"
            "したときは、催告なく本契約を解除することができる。",
            indent=10,
        )
    article("解約")
    if record.notice_ambiguous:
        doc.para("甲又は乙は、相当の期間をもって相手方に予告することにより、本契約を解約することができる。", indent=10)
    elif record.notice_days is not None:
        doc.para(
            "甲又は乙は、", ("termination_notice_days", f"{record.notice_days}日前"),
            "までに相手方に書面で通知することにより、本契約を解約することができる。", indent=10,
        )  # fmt: skip
    else:
        doc.para("甲又は乙は、相手方が本契約に重大な違反をしたときは、直ちに本契約を解除することができる。", indent=10)
    if record.second_cap is not None:
        article("責任の制限")
        doc.para(
            "前各条の規定にかかわらず、甲及び乙が負う責任の総額は、金",
            ("liability_cap_jpy", amount(record.second_cap, record.amount_style)), "を上限とする。", indent=10,
        )  # fmt: skip
    if record.governing_law:
        article("準拠法")
        doc.para("本契約は、", ("governing_law", "日本法"), "に準拠し、同法に従って解釈される。", indent=10)
    article("合意管轄")
    doc.para("本契約に関する一切の紛争は、架空地方裁判所を第一審の専属的合意管轄裁判所とする。", indent=10)
    article("協議")
    doc.para("本契約に定めのない事項は、甲乙誠実に協議のうえ解決する。", indent=10)
    if record.injection is not None:
        doc.para("（備考）" + INJECTIONS[record.injection], size=doc.size - 1)
    doc.para("本契約の成立を証するため、本書2通を作成し、甲乙記名押印のうえ各1通を保有する。")
    doc.line(format_date(record.sign_date, style), doc.size, LEFT, doc.gap)
    for role, name, address, rep in (
        ("甲", record.party_a, record.party_a_address, record.rep_a),
        ("乙", record.party_b, record.party_b_address, record.rep_b),
    ):
        doc.line(f"（{role}）{address}", doc.size, LEFT + 180, doc.gap)
        doc.line(f"{name}　代表取締役　{rep}", doc.size, LEFT + 200, doc.gap)
    if record.spec_items:
        doc.new_page()
        doc.line("別紙　業務仕様書", 12, LEFT, 24)
        for item in record.spec_items:
            doc.para(item, size=9.5)
    return doc.save(), doc.line_anchors, headings
