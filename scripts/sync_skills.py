"""Copy .claude/skills (canonical) to .agents/skills (Codex) and validate SKILL.md frontmatter.

Usage:
    python scripts/sync_skills.py          # validate, then overwrite .agents/skills
    python scripts/sync_skills.py --check  # validate and fail if the two trees differ
"""

from __future__ import annotations

import filecmp
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / ".claude" / "skills"
DST = ROOT / ".agents" / "skills"
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
MAX_DESCRIPTION = 1024


def frontmatter_errors(skill_dir: Path) -> list[str]:
    path = skill_dir / "SKILL.md"
    if not path.is_file():
        return [f"{skill_dir.name}: SKILL.md がありません"]
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return [f"{skill_dir.name}: frontmatter（--- で囲む）がありません"]
    fields: dict[str, str] = {}
    key = None
    for line in match.group(1).splitlines():
        if line.startswith((" ", "\t")) and key:  # continuation of a folded/literal block scalar
            fields[key] = f"{fields[key]} {line.strip()}".strip()
        elif ":" in line:
            key, value = (part.strip() for part in line.split(":", 1))
            fields[key] = "" if value in (">", "|", ">-", "|-") else value
    name = fields.get("name", "")
    description = fields.get("description", "")
    errors = []
    if name != skill_dir.name or not NAME_RE.match(name):
        errors.append(f"{skill_dir.name}: name はフォルダ名と同じ英小文字・数字・ハイフンにしてください（現在: {name!r}）")
    if not description:
        errors.append(f"{skill_dir.name}: description がありません")
    elif len(description) > MAX_DESCRIPTION:
        errors.append(f"{skill_dir.name}: description が {MAX_DESCRIPTION} 文字を超えています（{len(description)}）")
    return errors


def trees_equal(a: Path, b: Path) -> bool:
    if not b.is_dir():
        return False
    files_a = sorted(p.relative_to(a) for p in a.rglob("*") if p.is_file())
    files_b = sorted(p.relative_to(b) for p in b.rglob("*") if p.is_file())
    if files_a != files_b:
        return False
    return all(filecmp.cmp(a / f, b / f, shallow=False) for f in files_a)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    errors = [e for d in sorted(SRC.iterdir()) if d.is_dir() for e in frontmatter_errors(d)]
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    if "--check" in sys.argv:
        if not trees_equal(SRC, DST):
            print(".agents/skills が .claude/skills と違います。python scripts/sync_skills.py を実行してください。", file=sys.stderr)
            return 1
        return 0
    shutil.rmtree(DST, ignore_errors=True)
    shutil.copytree(SRC, DST)
    return 0


if __name__ == "__main__":
    sys.exit(main())
