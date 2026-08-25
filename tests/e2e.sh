#!/usr/bin/env bash
# abdiff end-to-end test.
# Creates a small project in a temporary git repo, adds one conditional canary rule to CLAUDE.md
# (uncommitted = variant), runs a real N=1 experiment, then checks the runner's guarantees:
# records exist, instruction loads are recorded, worktrees are isolated and cleaned up, the variant
# diff doesn't leak into changes.patch, the baseline never sees the canary.
#
# Cases: TC-01 is a control where the rule must not fire (read a file only), TC-02 is a target where
# it must fire (modify src/).
# Whether the model actually appends the canary is model behavior, so it's reported as a warning,
# not a failure. Every other check is deterministic and fails the script.
#
# Cost: 4 claude-haiku-4-5 runs (a few cents). Requires: logged-in claude CLI, git, python3
# Usage: bash tests/e2e.sh
#   ABDIFF_TEST_MODEL=claude-sonnet-5 bash tests/e2e.sh   # use another model
set -euo pipefail

PLUGIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${ABDIFF_E2E_OUT:-$PLUGIN_DIR/tests/.last}"
MODEL="${ABDIFF_TEST_MODEL:-claude-haiku-4-5-20251001}"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/abdiff-e2e.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

FAILED=0
check() { # <description> <command...>
  local desc="$1"; shift
  if "$@"; then echo "ok    $desc"; else echo "FAIL  $desc"; FAILED=1; fi
}
warn() { # <description> <command...>
  local desc="$1"; shift
  if "$@"; then echo "ok    $desc"; else echo "warn  $desc (model behavior, not a runner failure)"; fi
}

echo "temp repo: $TMP"
cd "$TMP"
git init -q .
git config user.email abdiff-test@example.com
git config user.name abdiff-test
printf '# Project rules\n\n- Answer in English.\n' > CLAUDE.md
printf 'hello\n' > hello.txt
mkdir -p src
printf 'export function add(a, b) { return a + b }\n' > src/add.js
git add -A
git commit -qm init

# Variant: add one conditional rule (not committed)
printf -- '- After modifying any file under src/, append the string [ABDIFF-CANARY] to the end of your answer.\n' >> CLAUDE.md

mkdir -p .abdiff/e2e
cat > .abdiff/e2e/experiment.json <<EOF
{
  "name": "e2e",
  "hypothesis": "Only the case that modifies src/ ends with [ABDIFF-CANARY]; the read-only case is unaffected",
  "n": 1,
  "model": "$MODEL",
  "permission": "bypass",
  "timeout_sec": 180,
  "budget_usd": 0.3,
  "test_cases": [
    {"id": "TC-01", "kind": "control", "title": "read a file",
     "prompt": "Tell me the contents of hello.txt in one line",
     "expect": "No effect. If the variant appends [ABDIFF-CANARY], the rule over-applied"},
    {"id": "TC-02", "kind": "target", "title": "add JSDoc",
     "prompt": "Add a JSDoc comment to the add function in src/add.js",
     "expect": "Only the variant appends [ABDIFF-CANARY]. Both conditions modify src/add.js"}
  ]
}
EOF

python3 "$PLUGIN_DIR/skills/abdiff/scripts/run.py" .abdiff/e2e/experiment.json --dry-run
RUN_RC=0
python3 "$PLUGIN_DIR/skills/abdiff/scripts/run.py" .abdiff/e2e/experiment.json || RUN_RC=$?
python3 "$PLUGIN_DIR/skills/abdiff/scripts/report.py" .abdiff/e2e

# Copy results before checking so a failed check still leaves something to inspect.
mkdir -p "$OUT_DIR"
rm -rf "$OUT_DIR/e2e"
cp -R .abdiff/e2e "$OUT_DIR/e2e"
echo "--- results copied to: $OUT_DIR/e2e (includes report.html) ---"

echo "--- checks ---"
check "runner exit code 0" test "$RUN_RC" -eq 0
check "variant.patch has the canary rule" grep -q 'ABDIFF-CANARY' .abdiff/e2e/variant.patch
check "manifest.json exists" test -s .abdiff/e2e/manifest.json
check "report.html exists" test -s .abdiff/e2e/report.html
for run in TC-01/baseline TC-01/variant TC-02/baseline TC-02/variant; do
  d=".abdiff/e2e/runs/$run/1"
  check "$run: stream.jsonl, run.json, instructions.jsonl exist" test -s "$d/stream.jsonl" -a -s "$d/run.json" -a -s "$d/instructions.jsonl"
done

# JSON-level checks on every run: hook record, isolation, no session persistence, no MCP, no user-level files.
check "hook records, worktree isolation, session/MCP/user settings excluded" python3 - "$TMP" <<'EOF'
import json, os, sys
root = sys.argv[1]; ok = True
def fail(msg):
    global ok; ok = False; print("      -", msg)
for run in ("TC-01/baseline", "TC-01/variant", "TC-02/baseline", "TC-02/variant"):
    d = f".abdiff/e2e/runs/{run}/1"
    recs = [json.loads(l) for l in open(f"{d}/instructions.jsonl") if l.strip()]
    if not any(r.get("file_path", "").endswith("/CLAUDE.md") and r.get("load_reason") == "session_start" for r in recs):
        fail(f"{run}: CLAUDE.md session_start load not recorded")
    for r in recs:
        cwd = r.get("cwd", "")
        if cwd.startswith(root): fail(f"{run}: worktree is inside the original repo: {cwd}")
        if "baseline" in cwd or "variant" in cwd: fail(f"{run}: condition name in worktree path: {cwd}")
        if os.path.expanduser("~/.claude") in r.get("file_path", ""): fail(f"{run}: user-level file loaded: {r['file_path']}")
        tp = r.get("transcript_path")
        if tp and os.path.exists(tp): fail(f"{run}: session transcript persisted: {tp}")
    init = next((json.loads(l) for l in open(f"{d}/stream.jsonl") if '"subtype":"init"' in l or '"subtype": "init"' in l), None)
    if init is None: fail(f"{run}: no init event in stream.jsonl")
    elif init.get("mcp_servers"): fail(f"{run}: MCP servers present: {init['mcp_servers']}")
    rj = json.load(open(f"{d}/run.json"))
    if rj.get("timed_out"): fail(f"{run}: timed out")
sys.exit(0 if ok else 1)
EOF

check "variant diff (CLAUDE.md) not leaked into changes.patch" bash -c '! grep -q "ABDIFF-CANARY" .abdiff/e2e/runs/TC-02/variant/1/changes.patch'
check "TC-02 variant changed src/add.js" grep -q 'src/add.js' .abdiff/e2e/runs/TC-02/variant/1/changes.patch
check "canary absent from baseline streams" bash -c '! grep -q "ABDIFF-CANARY" .abdiff/e2e/runs/TC-01/baseline/1/stream.jsonl .abdiff/e2e/runs/TC-02/baseline/1/stream.jsonl'
check "no worktree left behind" test "$(git worktree list | wc -l | tr -d ' ')" = "1"
check ".abdiff/ added to .git/info/exclude" grep -q '^\.abdiff/$' "$(git rev-parse --git-path info/exclude)"
check "report has both conditions and both cases" bash -c 'grep -q "data-arm=\"base\"" .abdiff/e2e/report.html && grep -q "data-arm=\"var\"" .abdiff/e2e/report.html && grep -q "data-case=\"TC-02\"" .abdiff/e2e/report.html'

# Model behavior: checked on the final answer only (the result event), not on the whole stream.
final() { python3 -c 'import json,sys
for l in open(sys.argv[1]):
    e=json.loads(l)
    if e.get("type")=="result": print(e.get("result","")); break' "$1"; }
warn "TC-02 variant final answer ends with the canary" bash -c "$(declare -f final); final .abdiff/e2e/runs/TC-02/variant/1/stream.jsonl | grep -q 'ABDIFF-CANARY'"
warn "TC-01 variant final answer has no canary (no over-application)" bash -c "$(declare -f final); ! final .abdiff/e2e/runs/TC-01/variant/1/stream.jsonl | grep -q 'ABDIFF-CANARY'"

if [ "$FAILED" -ne 0 ]; then echo "--- e2e FAILED ---"; exit 1; fi
echo "--- e2e passed ---"
