#!/usr/bin/env python3
"""abdiff reader (optional).

For every run in a results directory, asks an isolated `claude -p` whether the run shows each
countable statement in the case's `expect`, with a citation. Writes reading.json next to the
run's raw records. The reader is never told the run's condition, the hypothesis, variant.patch, or
instructions.jsonl, and has no tools and no project or user instruction files.

This is reading help for the person judging. It does not pick a side.

Usage: python3 reading.py <results-dir>

Options come from experiment.json's `reading` field: references/protocol.md
Prompt: prompts/reading.md. What the reader sees and why: references/reading.md
"""
import datetime as dt
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from report import ARMS, parse_stream, read_json, read_jsonl, read_text, summarize_input  # noqa: E402

PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "reading.md"
DEFAULTS = {"budget_usd": 0.5, "timeout_sec": 180}
TOOL_RESULT_MAX = 2000  # chars per tool result shown to the reader
CALLS_MAX = 150000  # chars for the whole tool-call section
PATCH_MAX = 40000  # chars of changes.patch
SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"findings": {"type": "array", "minItems": 1, "items": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "statement": {"type": "string", "minLength": 1},
            "observed": {"type": "string", "enum": ["yes", "no", "unclear"]},
            "evidence": {"type": "string", "minLength": 1},
        },
        "required": ["statement", "observed", "evidence"],
    }}, "summary": {"type": "string", "minLength": 1}},
    "required": ["findings", "summary"],
}


def die(msg):
    print(f"abdiff: {msg}", file=sys.stderr)
    sys.exit(1)


def log(msg, end="\n"):
    print(msg, file=sys.stderr, end=end, flush=True)


def now():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def clip(s, limit):
    return s if len(s) <= limit else s[:limit] + f"\n... (truncated, {len(s) - limit:,} more chars)"


def run_record(tc, rd, rj):
    """The parts of one run the reader may see. No condition name, no instruction loads."""
    p = parse_stream(read_jsonl(rd / "stream.jsonl"))
    wt = rj.get("worktree") or ""
    calls = []
    for i, c in enumerate(p["trace"], 1):
        line = f"{i}. {c['tool']} {summarize_input(c['tool'], c['input'], wt)}"
        if c["result"] is not None:
            tag = "error" if c["result"]["is_error"] else "result"
            line += f"\n   {tag}: {clip(c['result']['text'], TOOL_RESULT_MAX)}"
        calls.append(line)
    status = [f"exit {rj.get('exit_code')}"]
    if rj.get("timed_out"):
        status.append("timed out")
    if p["is_error"]:
        status.append("ended with an error")
    if not p["has_result"]:
        status.append("no result event")
    return "\n\n".join([
        f"## Task prompt\n{tc['prompt']}",
        f"## Expected effect (written before the run)\n{tc['expect']}",
        "## Run status\n" + ", ".join(status),
        "## Final response\n" + (p["final"] or "(none)"),
        f"## Tool calls ({len(calls)})\n" + (clip("\n".join(calls), CALLS_MAX) or "(none)"),
        "## Files changed (diff)\n" + (clip(read_text(rd / "changes.patch"), PATCH_MAX) or "(none)"),
    ])


def build_command(cfg):
    # No user, project, or local settings, no CLAUDE.md, no tools, no MCP: the reader sees the record only.
    # --system-prompt-file isn't listed in `claude --help` (2.1.250) but works; --system-prompt is the documented form.
    cmd = [
        "claude", "-p", "--output-format", "json",
        "--system-prompt-file", str(PROMPT_FILE),
        "--json-schema", json.dumps(SCHEMA),
        "--tools", "", "--setting-sources", "", "--strict-mcp-config", "--no-session-persistence",
        "--max-budget-usd", str(cfg["budget_usd"]),
    ]
    if cfg.get("model"):
        cmd += ["--model", cfg["model"]]
    return cmd


def read_one(cfg, tc, rd, rj):
    # A fresh empty directory outside the repo per call: no CLAUDE.md is found by path, and
    # nothing carries over between calls.
    with tempfile.TemporaryDirectory(prefix="abdiff-reading-") as cwd:
        env = dict(os.environ, CLAUDE_CODE_DISABLE_AUTO_MEMORY="1")
        try:
            r = subprocess.run(build_command(cfg), input=run_record(tc, rd, rj), cwd=cwd, env=env, text=True,
                               encoding="utf-8", errors="replace", capture_output=True, timeout=float(cfg["timeout_sec"]))
        except subprocess.TimeoutExpired:
            return {"error": f"timed out after {cfg['timeout_sec']}s"}
    try:
        out = json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"error": f"exit {r.returncode}: {r.stderr.strip()[-500:] or 'no JSON output'}"}
    if r.returncode != 0 or out.get("is_error") or not isinstance(out.get("structured_output"), dict):
        return {"error": out.get("result") or f"exit {r.returncode}: {out.get('subtype') or 'no structured output'}"}
    model = out.get("model") or ",".join(out.get("modelUsage") or {}) or cfg.get("model")
    return {**out["structured_output"], "model": model, "cost_usd": out.get("total_cost_usd")}


def main():
    if len(sys.argv) != 2:
        die("usage: reading.py <results-dir>")
    results = Path(sys.argv[1]).resolve()
    exp = read_json(results / "experiment.json")
    if not exp or not exp.get("test_cases"):
        die(f"experiment.json is missing or has no test_cases: {results}")
    if not shutil.which("claude"):
        die("claude CLI is not on PATH")
    if not isinstance(exp.get("reading", {}), dict):
        die('reading must be an object, e.g. {"model": "..."} or {}')
    cfg = {**DEFAULTS, **exp.get("reading", {})}
    n = int((read_json(results / "manifest.json") or {}).get("n") or exp.get("n") or 3)
    runs = [(tc, arm, k) for tc in exp["test_cases"] for k in range(1, n + 1) for arm, _, _ in ARMS]
    log(f"{len(runs)} runs to read / model {cfg.get('model') or 'default'} / budget cap ${len(runs) * float(cfg['budget_usd']):g}")

    meta = {"model": cfg.get("model"), "started_at": now(), "finished_at": None, "interrupted": False,
            "runs": len(runs), "read": 0, "failed": 0,
            "command": "CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 " + " ".join(shlex.quote(c) for c in build_command(cfg)).replace(json.dumps(SCHEMA), "<schema>")}

    # Claude Code sends SIGTERM when it stops a background task. Route it through the same
    # path as Ctrl+C; subprocess.run kills the in-flight claude on the way out.
    def on_term(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, on_term)

    try:
        for i, (tc, arm, k) in enumerate(runs, 1):
            rd = results / "runs" / tc["id"] / arm / str(k)
            log(f"[{i}/{len(runs)}] {tc['id']} {arm} run {k} ...", end=" ")
            rj = read_json(rd / "run.json")
            if rj is None:
                log("not run, skipped")
                continue
            j = read_one(cfg, tc, rd, rj)
            (rd / "reading.json").write_text(json.dumps(j, ensure_ascii=False, indent=2), encoding="utf-8")
            if "error" in j:
                meta["failed"] += 1
                log(f"failed: {j['error']}")
            else:
                meta["read"] += 1
                log(f"{len(j['findings'])} findings")
    except KeyboardInterrupt:
        meta["interrupted"] = True
        log("\ninterrupted")
    finally:
        meta["finished_at"] = now()
        (results / "readings.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    log(f"done: {meta['read']}/{len(runs)} runs read, {meta['failed']} failed. Rebuild the report to include them.")
    sys.exit(130 if meta["interrupted"] else 1 if meta["failed"] else 0)


if __name__ == "__main__":
    main()
