#!/usr/bin/env python3
"""abdiff report generator.

Reads the raw records in a results directory (.abdiff/<experiment>/) and writes one report.html.
Which files it reads and how the report is laid out: references/trace.md

Usage: python3 report.py <results-dir>
"""
import html
import json
import os
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "report.html"
ARMS = (("baseline", "base", "baseline"), ("variant", "var", "variant"))
KIND = {"target": "target", "control": "control (no effect expected)"}
DIFF_OPEN_MAX_LINES = 40  # one file at or under this many lines: show the diff expanded


def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def read_text(p):
    try:
        return Path(p).read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def read_json(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def read_jsonl(p):
    out = []
    for line in read_text(p).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def rel(path, wt):
    if not isinstance(path, str):
        return json.dumps(path, ensure_ascii=False)
    for prefix in {wt, os.path.realpath(wt)} if wt else ():
        if path.startswith(prefix):
            return path[len(prefix):].lstrip("/") or "."
    return path


# ---------- stream.jsonl ----------

def tool_result_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    return "" if content is None else json.dumps(content, ensure_ascii=False)


def parse_stream(events):
    r = {"model": None, "version": None, "trace": [], "last_text": None, "final": None, "has_result": False,
         "is_error": None, "num_turns": None, "cost": None, "denials": []}
    results = {}
    for ev in events:
        t = ev.get("type")
        if t == "system" and ev.get("subtype") == "init":
            r["model"] = ev.get("model")
            r["version"] = ev.get("claude_code_version")
        elif t == "assistant":
            parent = ev.get("parent_tool_use_id")
            for b in (ev.get("message") or {}).get("content") or []:
                if b.get("type") == "tool_use":
                    r["trace"].append({"id": b.get("id"), "tool": b.get("name") or "?", "input": b.get("input") or {}, "sub": bool(parent), "result": None})
                elif b.get("type") == "text" and not parent and b.get("text"):
                    r["last_text"] = b["text"]
        elif t == "user":
            # Tool results. Keep the full text so claims in the response ("N tests passed") can be checked.
            for b in (ev.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    results[b.get("tool_use_id")] = {"text": tool_result_text(b.get("content")), "is_error": bool(b.get("is_error"))}
        elif t == "result":
            r["has_result"] = True
            r["final"] = ev.get("result")
            r["is_error"] = ev.get("is_error")
            r["num_turns"] = ev.get("num_turns")
            r["cost"] = ev.get("total_cost_usd")
            r["denials"] = ev.get("permission_denials") or []
    if r["final"] is None:
        r["final"] = r["last_text"]
    for c in r["trace"]:
        c["result"] = results.get(c["id"])
    return r


def summarize_input(tool, inp, wt):
    inp = inp or {}
    if tool == "Read":
        s = rel(inp.get("file_path", ""), wt)
        extra = [f"{k}={inp[k]}" for k in ("offset", "limit") if k in inp]
        return s + (f"  ({', '.join(extra)})" if extra else "")
    if tool in ("Edit", "Write"):
        return rel(inp.get("file_path", ""), wt)
    if tool == "NotebookEdit":
        return rel(inp.get("notebook_path", ""), wt)
    if tool == "Bash":
        return inp.get("command", "")
    if tool == "Grep":
        s = f"/{inp.get('pattern', '')}/"
        if inp.get("path"):
            s += f"  {rel(inp['path'], wt)}"
        if inp.get("glob"):
            s += f"  glob={inp['glob']}"
        return s
    if tool == "Glob":
        s = inp.get("pattern", "")
        if inp.get("path"):
            s += f"  {rel(inp['path'], wt)}"
        return s
    if tool in ("Agent", "Task"):
        d, p = inp.get("description", ""), inp.get("prompt", "")
        return f"{d}\n{p}" if p else d
    if tool == "WebFetch":
        return inp.get("url", "")
    if tool == "WebSearch":
        return inp.get("query", "")
    if tool == "Skill":
        return f"{inp.get('skill', '')} {inp.get('args', '')}".strip()
    return json.dumps(inp, ensure_ascii=False)


# ---------- patch ----------

def split_patch(text):
    files, cur, in_hunk = [], None, False
    for line in text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split(" b/", 1)
            cur = {"path": parts[1] if len(parts) > 1 else line, "status": "modified", "binary": False,
                   "added": 0, "removed": 0, "lines": []}
            files.append(cur)
            in_hunk = False
            continue
        if cur is None:
            continue
        cur["lines"].append(line)
        if line.startswith("@@"):
            in_hunk = True
        elif not in_hunk:
            if line.startswith("new file mode"):
                cur["status"] = "new"
            elif line.startswith("deleted file mode"):
                cur["status"] = "deleted"
            elif line.startswith("rename from"):
                cur["status"] = "renamed"
            elif line.startswith("Binary files") or line.startswith("GIT binary patch"):
                cur["binary"] = True
        elif line.startswith("+"):
            cur["added"] += 1
        elif line.startswith("-"):
            cur["removed"] += 1
    return files


def render_diff_body(f):
    if f["binary"]:
        return '<p class="fine">Binary file. See the raw patch for its content.</p>'
    spans, in_hunk = [], False
    for line in f["lines"]:
        if line.startswith("@@"):
            in_hunk = True
            cls = "hunk"
        elif not in_hunk:
            cls = "meta"
        elif line.startswith("+"):
            cls = "add"
        elif line.startswith("-"):
            cls = "del"
        else:
            cls = "ctx"
        spans.append(f'<span class="dl {cls}">{esc(line)}</span>')
    return '<div class="diff">' + "".join(spans) + "</div>"


def render_files(files):
    if not files:
        return '<div class="lbl">Changed files: 0</div><p class="fine">No changes.</p>'
    total_a = sum(f["added"] for f in files)
    total_d = sum(f["removed"] for f in files)
    out = [f'<div class="lbl">Changed files: {len(files)} / <span class="stat"><span class="add">+{total_a}</span> <span class="del">-{total_d}</span></span></div>']
    small = len(files) == 1 and len(files[0]["lines"]) <= DIFF_OPEN_MAX_LINES
    for f in files:
        tag = f' <span class="tag">{esc(f["status"])}</span>' if f["status"] != "modified" else ""
        if f["binary"]:
            tag += ' <span class="tag">binary</span>'
        out.append(
            f'<details class="file"{" open" if small else ""}><summary><span class="path">{esc(f["path"])}</span>{tag}'
            f'<span class="stat"><span class="add">+{f["added"]}</span> <span class="del">-{f["removed"]}</span></span></summary>'
            f'{render_diff_body(f)}</details>'
        )
    return "".join(out)


# ---------- run ----------

def load_run(results, cid, arm, k):
    rd = results / "runs" / cid / arm / str(k)
    if not rd.exists():
        return None
    rj = read_json(rd / "run.json")
    wt = (rj or {}).get("worktree") or ""
    return {
        "run_json": rj, "wt": wt,
        "parsed": parse_stream(read_jsonl(rd / "stream.jsonl")),
        "instr": read_jsonl(rd / "instructions.jsonl"),
        "changes": split_patch(read_text(rd / "changes.patch")),
        "stderr": read_text(rd / "stderr.txt").strip(),
        "setup": read_text(rd / "setup.txt").strip(),
        "reading": read_json(rd / "reading.json"),
    }


def run_flags(run):
    p, rj = run["parsed"], run["run_json"]
    flags = []
    if rj is None:
        flags.append("interrupted")
    elif rj.get("timed_out"):
        flags.append("timeout")
    if p["is_error"]:
        flags.append("error")
    if rj is not None and not rj.get("timed_out") and not p["has_result"]:
        flags.append("no result event")
    if p["denials"]:
        flags.append(f"permission denials: {len(p['denials'])}")
    return flags


def run_summary(run):
    if run is None:
        return "not run"
    p, rj = run["parsed"], run["run_json"] or {}
    parts = []
    if p["num_turns"] is not None:
        parts.append(f"{p['num_turns']} turns")
    if rj.get("duration_sec") is not None:
        parts.append(f"{rj['duration_sec']:.0f}s")
    parts.append(f"{len(p['trace'])} tool calls")
    parts.append(f"{len(run['changes'])} files changed")
    parts += run_flags(run)
    return " / ".join(parts)


def render_trace(p, wt):
    if not p["trace"]:
        return '<p class="fine">No tool calls.</p>'
    items = []
    for c in p["trace"]:
        cls = ' class="sub"' if c["sub"] else ""
        res = c.get("result")
        if res is None:
            res_html = '<span class="tres-none">no result</span>'
        else:
            label = ("error / " if res["is_error"] else "result / ") + f"{len(res['text']):,} chars"
            res_html = f'<details class="tres"><summary>{label}</summary><pre class="tres-body">{esc(res["text"])}</pre></details>'
        items.append(f'<li{cls}><span class="tool">{esc(c["tool"])}</span><span class="arg">{esc(summarize_input(c["tool"], c["input"], wt))}</span>{res_html}</li>')
    return '<ol class="tr">' + "".join(items) + "</ol>"


def render_instructions(instr, wt):
    if not instr:
        return '<details class="instr"><summary>Instruction files loaded: 0</summary><p class="fine">The InstructionsLoaded hook recorded nothing.</p></details>'
    lis = "".join(
        f'<li><span class="path">{esc(rel(i.get("file_path", ""), wt))}</span>'
        f'<span class="fine">{esc(i.get("memory_type", ""))} / {esc(i.get("load_reason", ""))}</span></li>'
        for i in instr
    )
    return f'<details class="instr"><summary>Instruction files loaded: {len(instr)}</summary><ul class="files">{lis}</ul></details>'


def render_reading(j):
    # Collapsed, and the summary line carries no yes/no counts, so the person reads the raw record
    # before the LLM's reading of it.
    findings = j.get("findings") if isinstance(j, dict) else None
    if not isinstance(findings, list) or not all(isinstance(f, dict) for f in findings):
        err = j.get("error") if isinstance(j, dict) else None
        return f'<div class="run-section"><details class="instr"><summary>LLM reading: failed</summary><pre class="block">{esc(err or "malformed reading.json")}</pre></details></div>'
    lis = "".join(
        f'<li><span class="tag">{esc(f.get("observed"))}</span> {esc(f.get("statement"))}<span class="fine">{esc(f.get("evidence"))}</span></li>'
        for f in findings
    )
    return (f'<div class="run-section"><details class="instr"><summary>LLM reading: {len(findings)} findings</summary>'
            f'<p>{esc(j.get("summary"))}</p><ul class="reading">{lis}</ul><p class="fine">Read by {esc(j.get("model") or "?")} from the trace, diff and response only. Check each citation in the record above; not a verdict.</p></details></div>')


def render_meta(run):
    # Only what a judgment needs: anomalies and the exit code. Tokens, cost and model are left out
    # so length or cost isn't mistaken for quality.
    p, rj = run["parsed"], run["run_json"] or {}
    parts = []
    if rj.get("exit_code") is not None:
        parts.append(f"exit {rj['exit_code']}")
    flags = run_flags(run)
    out = '<p class="run-meta">' + esc(" / ".join(parts))
    if flags:
        out += (" / " if parts else "") + '<b class="warn">' + esc(" / ".join(flags)) + "</b>"
    out += "</p>"
    if p["denials"]:
        lis = "".join(f"<li><span class=\"tool\">{esc(d.get('tool_name'))}</span> {esc(summarize_input(d.get('tool_name'), d.get('tool_input'), run['wt']))}</li>" for d in p["denials"])
        out += f'<details class="instr"><summary>Permission denials: {len(p["denials"])}</summary><ul class="files">{lis}</ul></details>'
    if run["stderr"]:
        out += f'<details class="instr"><summary>stderr</summary><pre class="block">{esc(run["stderr"])}</pre></details>'
    if run["setup"]:
        out += f'<details class="instr"><summary>setup output</summary><pre class="block">{esc(run["setup"])}</pre></details>'
    return out


def render_run(arm_key, label, run):
    if run is None:
        return (f'<details class="run" data-arm="{arm_key}" open><summary><span class="arm-label">{label}</span>'
                f'<span class="run-sum">not run</span></summary></details>')
    p = run["parsed"]
    final_html = f'<pre class="resp">{esc(p["final"])}</pre>' if p["final"] is not None else '<p class="fine">No final response.</p>'
    return (
        f'<details class="run" data-arm="{arm_key}" open>'
        f'<summary><span class="arm-label">{label}</span><span class="run-sum">{esc(run_summary(run))}</span></summary>'
        f'<div class="run-section"><div class="lbl">Final response</div>{final_html}</div>'
        f'<div class="run-section"><details class="trace"><summary>Trace / {len(p["trace"])} tool calls</summary>{render_trace(p, run["wt"])}</details></div>'
        f'<div class="run-section">{render_instructions(run["instr"], run["wt"])}</div>'
        f'<div class="run-section">{render_files(run["changes"])}</div>'
        f'{render_reading(run["reading"]) if run["reading"] else ""}'
        f'{render_meta(run)}'
        f'</details>'
    )


def render_case(tc, n, results):
    cid = tc["id"]
    kind = KIND.get(tc.get("kind") or "target", esc(tc.get("kind")))
    title = f' {esc(tc["title"])}' if tc.get("title") else ""
    out = [
        f'<section class="sec case" id="case-{esc(cid)}" data-case="{esc(cid)}">',
        f'<h2><span class="cid">{esc(cid)}</span>{title}<span class="case-kind">{kind}</span></h2>',
        f'<div class="field"><div class="lbl">Prompt</div><pre class="block">{esc(tc["prompt"])}</pre></div>',
        f'<div class="field"><div class="lbl">Expected effect (written before the run)</div><p>{esc(tc["expect"])}</p></div>',
    ]
    for k in range(1, n + 1):
        runs = {arm: load_run(results, cid, arm, k) for arm, _, _ in ARMS}
        sums = "".join(
            f'<span class="pair-sum" data-arm="{key}"><span class="arm-label">{label}</span> {esc(run_summary(runs[arm]))}</span>'
            for arm, key, label in ARMS
        )
        # Only the first pair is expanded. The rest are compared by their summary line and opened as needed.
        out.append(f'<details class="pair"{" open" if k == 1 else ""}><summary><span class="pair-title">run {k}</span><span class="pair-sums">{sums}</span></summary><div class="pair-body">')
        for arm, key, label in ARMS:
            out.append(render_run(key, label, runs[arm]))
        out.append("</div></details>")
    out.append("</section>")
    return "".join(out)


# ---------- page ----------

def render_overview(exp, man, readings, all_runs, n):
    models = sorted({r["parsed"]["model"] for r in all_runs if r and r["parsed"]["model"]})
    versions = sorted({r["parsed"]["version"] for r in all_runs if r and r["parsed"]["version"]})
    done = sum(1 for r in all_runs if r)
    failed = sum(1 for r in all_runs if r and run_flags(r))
    cost = sum(r["parsed"]["cost"] or 0 for r in all_runs if r)
    total = 2 * n * len(exp["test_cases"])
    rows = [
        ("Hypothesis", esc(exp.get("hypothesis"))),
        ("Run time", f"{esc(man.get('started_at'))} -> {esc(man.get('finished_at') or 'in progress / interrupted')}"),
        ("Claude Code", esc(", ".join(versions) or man.get("claude_version") or "?")),
        ("Model (observed)", esc(", ".join(models) or "not recorded")),
        ("N", f"{n} per condition per test case"),
        ("Test cases", f"{len(exp['test_cases'])} ({sum(1 for t in exp['test_cases'] if t.get('kind') != 'control')} target, {sum(1 for t in exp['test_cases'] if t.get('kind') == 'control')} control)"),
        ("Runs", f"{done}/{total} completed / {failed} with timeout, error or permission denials" + (" / experiment interrupted" if man.get("interrupted") else "")),
        ("Run cost", f"${cost:.2f}" + (" (LLM reading excluded)" if readings else "")),
    ]
    if isinstance(readings, dict):
        reading_cost = sum(r["reading"].get("cost_usd") or 0 for r in all_runs if r and isinstance(r["reading"], dict))
        rows.append(("LLM reading", esc(f"{readings.get('read')}/{readings.get('runs')} runs read by {readings.get('model') or 'claude -p default'}, {readings.get('failed')} failed"
                                        + (", interrupted" if readings.get("interrupted") else "")
                                        + f", ${reading_cost:.2f}. Isolated claude -p: no tools, no project or user files, not told the condition, hypothesis or variant.patch. Collapsed under each run.")))
    if n < 3:
        rows.append(("Caution", f"<b class=\"warn\">N={n}.</b> Run-to-run variance can't be told apart from the difference between conditions. Rerun with N=3 or more before drawing a conclusion."))
    trs = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows)
    return (f'<section class="sec" id="overview"><h1>{esc(exp["name"])}</h1>'
            f'<p class="doc-meta">abdiff experiment report / baseline commit {esc((man.get("base_commit") or "")[:12])}</p>'
            f'<h2>Overview</h2><div class="scroll"><table class="kv"><tbody>{trs}</tbody></table></div></section>')


def render_change(variant_patch):
    return (f'<section class="sec" id="change"><h2>The change</h2>'
            f'<p>The variant condition is the baseline commit with the diff below applied. Everything else (files, settings, prompts) is identical in both conditions.</p>'
            f'{render_files(split_patch(variant_patch))}</section>')


def render_protocol(man):
    trs = "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in man.get("protocol") or [])
    return (f'<section class="sec" id="protocol"><h2>Fixed conditions</h2><p>Applied identically to every run.</p>'
            f'<div class="scroll"><table class="kv"><tbody>{trs}</tbody></table></div>'
            f'<div class="field"><div class="lbl">Command</div><pre class="block">{esc(man.get("command_template") or "")}</pre></div></section>')


def main():
    if len(sys.argv) != 2:
        print("usage: report.py <results-dir>", file=sys.stderr)
        sys.exit(1)
    results = Path(sys.argv[1]).resolve()
    exp = read_json(results / "experiment.json")
    if not exp or not isinstance(exp.get("test_cases"), list) or not exp["test_cases"]:
        print(f"experiment.json is missing or has no test_cases: {results}", file=sys.stderr)
        sys.exit(1)
    man = read_json(results / "manifest.json", {}) or {}
    n = int(man.get("n") or exp.get("n") or 3)  # the n the runner actually used is in manifest.json
    all_runs = [load_run(results, t["id"], arm, k) for t in exp["test_cases"] for k in range(1, n + 1) for arm, _, _ in ARMS]
    readings = read_json(results / "readings.json")

    # Order: overview -> the change -> per-case comparison -> fixed conditions.
    # The diff comes before the cases: knowing what changed is what makes the traces readable.
    content = "".join([
        render_overview(exp, man, readings, all_runs, n),
        render_change(read_text(results / "variant.patch")),
        "".join(render_case(t, n, results) for t in exp["test_cases"]),
        render_protocol(man),
    ])
    toc = "".join(
        f'<li><a href="#case-{esc(t["id"])}">{esc(t["id"])}{(" " + esc(t["title"])) if t.get("title") else ""}</a></li>'
        for t in exp["test_cases"]
    )
    page = (TEMPLATE.read_text(encoding="utf-8")
            .replace("{{TITLE}}", esc(f"abdiff / {exp['name']}"))
            .replace("{{EXPERIMENT}}", esc(exp["name"]))
            .replace("{{TOC_CASES}}", toc)
            .replace("{{CONTENT}}", content))
    out = results / "report.html"
    out.write_text(page, encoding="utf-8")
    print(f"{out} ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
