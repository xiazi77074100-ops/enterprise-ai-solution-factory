#!/bin/sh
# Copied into the repo for other sessions (docs/HANDOFF.md). Needs curl and python; the repository is public.
# Usage: wait_ci.sh <full-sha>. Polls the public GitHub API until every workflow run for the SHA completes.
# Prints the conclusions and failed steps; exit 0 only when all runs succeeded.
SHA="$1"
REPO=xiazi77074100-ops/enterprise-ai-solution-factory
for i in $(seq 1 60); do
  STATE=$(curl -s --max-time 20 "https://api.github.com/repos/$REPO/actions/runs?head_sha=$SHA" | python -c "
import sys,json
runs=json.load(sys.stdin).get('workflow_runs',[])
if not runs: print('none'); sys.exit()
print('done' if all(r['status']=='completed' for r in runs) else 'running')")
  [ "$STATE" = "done" ] && break
  sleep 15
done
curl -s --max-time 20 "https://api.github.com/repos/$REPO/actions/runs?head_sha=$SHA" | python -c "
import sys,json,urllib.request
runs=json.load(sys.stdin)['workflow_runs']
ok=True
for r in runs:
    print(r['event'], r['status'], r['conclusion'])
    if r['conclusion']!='success':
        ok=False
        jobs=json.load(urllib.request.urlopen(r['jobs_url'],timeout=20))['jobs']
        for j in jobs:
            for s in j['steps']:
                if s['conclusion']=='failure': print('  FAILED:', j['name'], '/', s['name'])
sys.exit(0 if ok and runs else 1)"
