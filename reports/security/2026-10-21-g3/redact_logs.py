"""ログの接続URIを秘匿化し、行末空白と改行を正規化する。値は表示しない。"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PATTERN = re.compile(r"(postgresql(?:\+psycopg)?://[^:\s'\"]+:)[^@\s'\"]+(@)")

if __name__ == "__main__":
    changed = 0
    for path in ROOT.rglob("*"):
        if path.suffix not in {".txt", ".json"}:
            continue
        text = path.read_text(encoding="utf-8-sig")
        redacted = PATTERN.sub(r"\1[REDACTED]\2", text)
        normalized = "\n".join(line.rstrip() for line in redacted.splitlines()).rstrip()
        normalized = normalized + "\n" if normalized else ""
        if normalized != text:
            path.write_text(normalized, encoding="utf-8", newline="\n")
        if redacted != text:
            changed += 1
    print(f"接続URIを秘匿化したファイル: {changed}")
