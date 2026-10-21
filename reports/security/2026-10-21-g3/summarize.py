"""保存済みの診断結果を集計する。対象は本診断ディレクトリ内だけ。"""

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


print("ruff S:", len(read("sast/ruff-s.json")))
print("bandit:", len(read("sast/bandit.json")["results"]))
if (ROOT / "sast/semgrep.json").exists():
    result = read("sast/semgrep.json")
    print("semgrep results/errors:", len(result["results"]), len(result["errors"]))
else:
    print("semgrep: 未完了（結果ファイルなし）")
print("pip-audit:", sum(len(d["vulns"]) for d in read("sca/pip-audit.json")["dependencies"]))
print("npm audit:", read("sca/npm-audit.json")["metadata"]["vulnerabilities"])
for path in sorted((ROOT / "secrets").glob("*.json")):
    print(path.name, len(json.loads(path.read_text(encoding="utf-8-sig"))))
for path in sorted((ROOT / "container").glob("trivy-*.json")):
    rows = json.loads(path.read_text(encoding="utf-8-sig")).get("Results", [])
    print(path.name, {key: sum(len(r.get(key, [])) for r in rows)
                      for key in ("Vulnerabilities", "Misconfigurations", "Secrets")})
for path in sorted((ROOT / "dast").glob("zap-api*.json")):
    sites = json.loads(path.read_text(encoding="utf-8-sig")).get("site", [])
    print(path.name, "riskcode/count:", dict(Counter(alert["riskcode"] for site in sites
                                                   for alert in site.get("alerts", []))))
