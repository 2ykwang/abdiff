#!/usr/bin/env bash
# Shared helpers for demos/*/run.sh.
# A demo copies a fixture into a temporary git repo, commits the baseline, leaves the
# variant uncommitted, runs abdiff, and copies the report back into the demo folder.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXTURES="$ROOT/demos/_fixtures"
MODEL="${ABDIFF_DEMO_MODEL:-claude-sonnet-5}"
N="${ABDIFF_DEMO_N:-2}"

demo_setup() { # <fixture-dir-name>
  TMP="$(mktemp -d "${TMPDIR:-/tmp}/abdiff-demo.XXXXXX")"
  trap 'rm -rf "$TMP"' EXIT
  cp -R "$FIXTURES/$1/." "$TMP/"
  cd "$TMP"
  git init -q . && git config user.email demo@example.com && git config user.name demo
}

commit_head() { git add -A "$@" && git commit -qm "baseline"; }

tc() { # <id> <target|control> <title> <prompt> <expect>
  python3 -c 'import json,sys;print(json.dumps({"id":sys.argv[1],"kind":sys.argv[2],"title":sys.argv[3],"prompt":sys.argv[4],"expect":sys.argv[5]}))' "$@"
}

normalize() { # strip temp paths and user names from a text file, in place
  sed -E -i '' \
    -e 's#/private/var/folders/[^"/ ]+/[^"/ ]+/T/abdiff-[A-Za-z0-9.-]+/run-[0-9a-f]{8}#<worktree>#g' \
    -e 's#/var/folders/[^"/ ]+/[^"/ ]+/T/abdiff-[A-Za-z0-9.-]+/run-[0-9a-f]{8}#<worktree>#g' \
    -e 's#/private/var/folders/[^"/ ]+/[^"/ ]+/T/abdiff-[A-Za-z0-9.-]+#<tmp>#g' \
    -e "s#$HOME#~#g" -e "s#$(id -un)#user#g" "$1"
}

run_demo() { # <demo-name> <hypothesis> <json-test-cases-comma-separated>
  local name="$1" hyp="$2" tcs="$3" dest="$ROOT/demos/$1"
  mkdir -p ".abdiff/$name"
  python3 - "$name" "$hyp" "$N" "$MODEL" "$tcs" <<'EOF'
import json, sys
name, hyp, n, model, tcs = sys.argv[1:]
exp = {"name": name, "hypothesis": hyp, "n": int(n), "model": model, "permission": "bypass",
       "timeout_sec": 600, "budget_usd": 1.5, "test_cases": json.loads("[" + tcs + "]")}
json.dump(exp, open(f".abdiff/{name}/experiment.json", "w"), indent=2)
EOF
  echo "--- variant diff:"; git diff HEAD --stat
  python3 "$ROOT/skills/abdiff/scripts/run.py" ".abdiff/$name/experiment.json" || echo "warning: some runs failed; exclude them when judging"
  python3 "$ROOT/skills/abdiff/scripts/report.py" ".abdiff/$name"
  for f in report.html experiment.json variant.patch manifest.json; do cp ".abdiff/$name/$f" "$dest/$f"; normalize "$dest/$f"; done
  if [ -n "${ABDIFF_DEMO_KEEP_RUNS:-}" ]; then rm -rf "$dest/runs"; cp -R ".abdiff/$name/runs" "$dest/runs"; fi
  echo "--- report: $dest/report.html"
}
