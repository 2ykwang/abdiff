#!/usr/bin/env python3
"""abdiff runner.

Runs the same test prompts under two conditions, baseline (HEAD) and variant
(HEAD + uncommitted working-tree changes), N times each with `claude -p`, and
keeps the raw record of every run. It does not judge anything.

Usage:
  python3 run.py <experiment.json>            run
  python3 run.py <experiment.json> --dry-run  print the plan only

experiment.json format and the rationale for the fixed conditions: references/protocol.md
Result directory layout: references/trace.md
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
import time
import uuid
from pathlib import Path
from typing import NoReturn

ARMS = ("baseline", "variant")
DEFAULTS = {"n": 3, "permission": "bypass", "timeout_sec": 600, "budget_usd": 2.0}


def die(msg) -> NoReturn:
    print(f"abdiff: {msg}", file=sys.stderr)
    sys.exit(1)


def log(msg, end="\n"):
    print(msg, file=sys.stderr, end=end, flush=True)


def now():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def git(cwd, *args, check=True):
    r = subprocess.run(["git", "-C", str(cwd), *args], text=True, errors="replace", capture_output=True)
    if check and r.returncode != 0:
        die(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def load_experiment(path):
    try:
        exp = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 - show the user whatever went wrong
        die(f"can't read experiment.json: {e}")
    for field in ("name", "hypothesis", "test_cases"):
        if not exp.get(field):
            die(f"experiment.json is missing '{field}'")
    if exp["name"] != path.parent.name:
        die(f"name ('{exp['name']}') doesn't match the directory name ('{path.parent.name}')")
    if not isinstance(exp["test_cases"], list):
        die("test_cases must be an array")
    seen = set()
    for tc in exp["test_cases"]:
        for field in ("id", "prompt", "expect"):
            if not tc.get(field):
                die(f"test case is missing '{field}': {json.dumps(tc, ensure_ascii=False)}")
        if "/" in tc["id"] or tc["id"] in (".", ".."):
            die(f"test case id can't contain '/': {tc['id']}")
        if tc["id"] in seen:
            die(f"duplicate test case id: {tc['id']}")
        seen.add(tc["id"])
        tc.setdefault("kind", "target")
        if tc["kind"] not in ("target", "control"):
            die(f"kind must be target or control: {tc['id']}")
    for key, value in DEFAULTS.items():
        exp.setdefault(key, value)
    exp["n"] = int(exp["n"])
    if exp["n"] < 1:
        die("n must be at least 1")
    if not any(tc["kind"] == "control" for tc in exp["test_cases"]):
        log("warning: no test case has kind=control. Nothing will show side effects of the variant.")
    return exp


def permission_flags(p):
    if p == "bypass":
        return ["--dangerously-skip-permissions"]
    if isinstance(p, dict):
        flags = ["--permission-mode", p.get("mode", "acceptEdits")]
        tools = p.get("allowed_tools") or []
        if tools:
            flags += ["--allowedTools", ",".join(tools)]
        return flags
    die('permission must be "bypass" or {"mode": ..., "allowed_tools": [...]}')


def build_command(exp, prompt, instr_path):
    # InstructionsLoaded hook: Claude Code emits an event JSON on stdin every time it loads an
    # instruction file (CLAUDE.md, .claude/rules, ...) into context. Save each event as one line.
    q = shlex.quote(str(instr_path))
    hook = json.dumps({"hooks": {"InstructionsLoaded": [{"hooks": [{"type": "command", "command": f"cat >> {q}; echo >> {q}"}]}]}})
    cmd = [
        "claude", "-p", prompt,
        "--output-format", "stream-json", "--verbose",
        "--setting-sources", "project",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--max-budget-usd", str(exp["budget_usd"]),
        "--settings", hook,
    ]
    if exp.get("model"):
        cmd += ["--model", exp["model"]]
    return cmd + permission_flags(exp["permission"])


def kill_group(proc):
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait(timeout=5)
    except (ProcessLookupError, PermissionError):
        return
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def run_one(exp, root, head, patch, base_dir, results, tc, arm, k):
    # The working directory path ends up in the model's context (environment info), so the
    # condition name must not appear in it. The mapping is recorded in run.json only.
    wt = base_dir / f"run-{uuid.uuid4().hex[:8]}"
    rd = results / "runs" / tc["id"] / arm / str(k)
    rd.mkdir(parents=True, exist_ok=True)
    (rd / "reading.json").unlink(missing_ok=True)  # a reading of a previous run with this name
    git(root, "worktree", "add", "--detach", "-q", str(wt), head)
    try:
        if arm == "variant":
            r = subprocess.run(["git", "-C", str(wt), "apply", "--binary", str(patch)], text=True, errors="replace", capture_output=True)
            if r.returncode != 0:
                die(f"failed to apply variant patch: {r.stderr.strip()}")
        if exp.get("setup"):
            env = dict(os.environ, ABDIFF_PROJECT=str(root))
            r = subprocess.run(exp["setup"], shell=True, cwd=str(wt), env=env, text=True, errors="replace", capture_output=True)
            (rd / "setup.txt").write_text(f"exit {r.returncode}\n--- stdout ---\n{r.stdout}\n--- stderr ---\n{r.stderr}", encoding="utf-8")
            if r.returncode != 0:
                die(f"setup failed ({tc['id']} {arm} run {k}): {r.stderr.strip()}\n  output: {rd / 'setup.txt'}")
        # Pin the variant patch and setup output in a temporary commit so changes.patch only
        # contains what the run itself changed. The latest commit is visible in the model's
        # context too, so both conditions use the same message.
        git(wt, "add", "-A")
        git(wt, "-c", "user.name=abdiff", "-c", "user.email=abdiff@localhost", "-c", "commit.gpgsign=false",
            "commit", "-q", "--no-verify", "--allow-empty", "-m", "abdiff: base")
        base = git(wt, "rev-parse", "HEAD").strip()
        cmd = build_command(exp, tc["prompt"], rd / "instructions.jsonl")
        env = dict(os.environ, CLAUDE_CODE_DISABLE_AUTO_MEMORY="1")
        t0 = time.monotonic()
        timed_out = False
        with open(rd / "stream.jsonl", "w", encoding="utf-8") as out, open(rd / "stderr.txt", "w", encoding="utf-8") as err:
            proc = subprocess.Popen(cmd, cwd=str(wt), env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
            try:
                code = proc.wait(timeout=float(exp["timeout_sec"]))
            except subprocess.TimeoutExpired:
                timed_out = True
                kill_group(proc)
                code = proc.wait()
            except KeyboardInterrupt:
                kill_group(proc)
                raise
        duration = time.monotonic() - t0
        git(wt, "add", "-A")
        (rd / "changes.patch").write_text(git(wt, "diff", "--cached", "--binary", base), encoding="utf-8")
        (rd / "run.json").write_text(json.dumps({
            "exit_code": code, "timed_out": timed_out, "duration_sec": round(duration, 1),
            "worktree": str(wt), "base_commit": base, "command": cmd,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        return code, duration, timed_out, rd
    finally:
        git(root, "worktree", "remove", "--force", str(wt), check=False)


def cleanup(root, base_dir):
    if base_dir.exists():
        for wt in base_dir.iterdir():
            git(root, "worktree", "remove", "--force", str(wt), check=False)
        shutil.rmtree(base_dir, ignore_errors=True)
    git(root, "worktree", "prune", check=False)


def exclude_abdiff(root):
    # Writing to .gitignore would put that change into the variant diff, so use the
    # repo-local exclude file instead.
    p = Path(git(root, "rev-parse", "--git-path", "info/exclude").strip())
    if not p.is_absolute():
        p = root / p
    try:
        existing = p.read_text(encoding="utf-8") if p.exists() else ""
        if ".abdiff/" not in existing.splitlines():
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(("" if not existing or existing.endswith("\n") else "\n") + ".abdiff/\n")
    except OSError as e:
        log(f"warning: couldn't update {p}: {e}")


def permission_text(p):
    if p == "bypass":
        return "--dangerously-skip-permissions (allow everything)"
    text = f"--permission-mode {p.get('mode', 'acceptEdits')}"
    if p.get("allowed_tools"):
        text += f", --allowedTools {','.join(p['allowed_tools'])}"
    return text


def protocol_table(exp, head, claude_version):
    return [
        ["model", exp.get("model") or "claude -p default (recorded in each run's init event)"],
        ["permissions", permission_text(exp["permission"])],
        ["setting sources", "project - excludes ~/.claude CLAUDE.md, settings, plugins, hooks, skills"],
        ["MCP", "none (--strict-mcp-config, no --mcp-config)"],
        ["auto memory", "off (CLAUDE_CODE_DISABLE_AUTO_MEMORY=1)"],
        ["session persistence", "off (--no-session-persistence)"],
        ["instruction load record", "InstructionsLoaded hook -> instructions.jsonl"],
        ["budget cap", f"${exp['budget_usd']} per run (--max-budget-usd)"],
        ["timeout", f"{exp['timeout_sec']}s per run"],
        ["worktree", "one per run, created in a temp directory outside the repo and removed afterwards. Directory name and temp commit message never contain the condition name"],
        ["baseline commit", head],
        ["variant", "baseline commit + variant.patch"],
        ["setup", exp.get("setup") or "none"],
        ["run order", "per test case, for each run k: baseline then variant, alternating, sequential"],
        ["Claude Code", claude_version],
    ]


def main():
    argv = sys.argv[1:]
    dry = "--dry-run" in argv
    argv = [a for a in argv if a != "--dry-run"]
    if len(argv) != 1:
        die("usage: run.py <experiment.json> [--dry-run]")
    exp_path = Path(argv[0]).resolve()
    if not exp_path.is_file():
        die(f"file not found: {exp_path}")
    exp = load_experiment(exp_path)
    results = exp_path.parent
    if not shutil.which("claude"):
        die("claude CLI is not on PATH")

    root = Path(git(results, "rev-parse", "--show-toplevel").strip())
    head = git(root, "rev-parse", "HEAD").strip()
    stat = git(root, "diff", "HEAD", "--stat")
    patch = git(root, "diff", "HEAD", "--binary")
    if not patch.strip():
        die("no variant: the working tree has no uncommitted changes (new files need git add). Change an instruction and run again.")
    claude_version = subprocess.run(["claude", "--version"], text=True, capture_output=True).stdout.strip()

    n, tcs = exp["n"], exp["test_cases"]
    total = 2 * n * len(tcs)
    template = build_command(exp, "$PROMPT", "<run>/instructions.jsonl")
    template[template.index("--settings") + 1] = "<InstructionsLoaded hook settings JSON>"  # for display in the report; the real value is in run.json's command
    template_str = " ".join(shlex.quote(c) for c in template)

    log(f"{total} runs ({len(tcs)} test cases x N {n} x 2 conditions) / budget cap ${total * float(exp['budget_usd']):g}")
    log(f"variant diff:\n{stat.rstrip()}")
    log(f"model {exp.get('model') or 'default'} / permissions {permission_text(exp['permission'])} / timeout {exp['timeout_sec']}s per run")
    if dry:
        return

    exclude_abdiff(root)
    (results / "variant.patch").write_text(patch, encoding="utf-8")
    manifest = {
        "n": n, "base_commit": head, "claude_version": claude_version,
        "started_at": now(), "finished_at": None, "interrupted": False,
        "command_template": template_str, "protocol": protocol_table(exp, head, claude_version),
    }
    manifest_path = results / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # resolve(): follow symlinks such as macOS /var -> /private/var so paths match what Claude Code reports.
    base_dir = Path(tempfile.mkdtemp(prefix="abdiff-")).resolve()
    done = 0
    failed = []  # (description, stderr path)
    interrupted = False

    # Claude Code sends SIGTERM when it stops a background task. Route it through the same
    # cleanup path as Ctrl+C (SIGINT).
    def on_term(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, on_term)

    try:
        for tc in tcs:
            for k in range(1, n + 1):
                for arm in ARMS:
                    log(f"[{done + 1}/{total}] {tc['id']} {arm} run {k} ...", end=" ")
                    code, duration, timed_out, rd = run_one(exp, root, head, results / "variant.patch", base_dir, results, tc, arm, k)
                    done += 1
                    if timed_out or code != 0:
                        failed.append((f"{tc['id']} {arm} run {k}: {'timeout' if timed_out else f'exit {code}'}", rd / "stderr.txt"))
                    log(f"{duration:.0f}s {'timeout' if timed_out else f'exit {code}'}")
    except KeyboardInterrupt:
        interrupted = True
        log("\ninterrupted - cleaning up worktrees")
    finally:
        cleanup(root, base_dir)
        manifest.update(finished_at=now(), interrupted=interrupted)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    log(f"done: {done}/{total} runs. Results: {results}")
    print(str(results))
    if interrupted:
        sys.exit(130)
    if failed:
        log(f"warning: {len(failed)} run(s) failed. The report marks them as error/timeout. Leave them out of your judgment.")
        for desc, path in failed:
            log(f"  {desc}: {path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
