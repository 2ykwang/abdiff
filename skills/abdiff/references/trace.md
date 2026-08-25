# Records and the report

The runner stores raw records only. The report generator reads them and builds the HTML.

## Result directory

```
.abdiff/<experiment name>/
├── experiment.json        # Experiment definition (orchestrator writes it from the questionnaire answers)
├── manifest.json          # Written by the runner: actual N, base commit, Claude Code version, start/end time, interrupted flag, fixed conditions, command
├── variant.patch          # git diff HEAD --binary (the variant condition)
├── report.html            # Output of report.py
└── runs/<case id>/<baseline|variant>/<k>/
    ├── stream.jsonl       # Raw claude -p --output-format stream-json
    ├── stderr.txt         # stderr of the claude process
    ├── instructions.jsonl # Instruction-file load events recorded by the InstructionsLoaded hook
    ├── changes.patch      # Files the run changed (git diff --cached <temp commit> --binary)
    ├── run.json           # Exit code, timeout flag, duration, worktree path, temp commit, command
    └── setup.txt          # Output of the setup command (only when setup is set)
```

The runner adds `.abdiff/` to `.git/info/exclude`. It doesn't touch `.gitignore`, because that edit would leak into the variant diff.

## What the report reads from stream.jsonl

| Event | Fields used |
|---|---|
| `system` / `init` | `model`, `claude_code_version` |
| `assistant` → `content[].tool_use` | Trace: tool name and input. If `parent_tool_use_id` is present, the call is marked as a subagent call |
| `assistant` → `content[].text` | When there's no `result` event, the last text is used as the final response |
| `user` → `content[].tool_result` | Tool result body and `is_error`. Attached to the trace line by `tool_use_id` |
| `result` | `result` (final response), `is_error`, `num_turns`, `total_cost_usd`, `permission_denials` |

Each trace line shows the tool name and input, with the full tool result collapsed underneath. That's so a response saying "7 tests passed" can be checked against the actual `node --test` output. Results are collapsed, never truncated. If the result is an error (`is_error`), the summary line says "error".

Per-tool input display:

| Tool | Shown |
|---|---|
| Read | Path (plus offset and limit if present) |
| Edit, Write, NotebookEdit | Path |
| Bash | Full command |
| Grep | `/pattern/`, path, glob |
| Glob | Pattern, path |
| Agent | Description and full prompt |
| WebFetch, WebSearch | url or query |
| Skill | Skill name and arguments |
| Anything else | Full input JSON |

Paths are shown relative to the worktree, with the worktree prefix stripped.

## instructions.jsonl

One event per line. Fields: `file_path`, `memory_type`, `load_reason` (`session_start`, `nested_traversal`, `path_glob_match`, `include`, `compact`), `session_id`, `cwd`. The report shows them per run as a collapsed "N instruction files loaded".

This record proves **that an input file entered context**. Whether the model followed it is judged from the response and the trace. A doc that's only pointed at with a "read this" line, rather than `@import`ed, doesn't appear here; it shows up only as a `Read` in the trace.

## changes.patch

After `git add -A`, this is the diff against the temporary commit made at run start (which already contains the variant patch and setup output). So files created by setup are excluded, and changes the agent made are included even if it committed them during the run. The report splits the patch per file: the list (path, status, +N −M) is always visible, the diff body is collapsed. If there's exactly one file with 40 lines or fewer, it's expanded. Binary patch bodies aren't shown.

## Report layout

Anything that reveals which arm is the variant (the diff, the fixed conditions) comes after the verdicts. Blind mode is on when the report opens.

| Order | Section | Contents |
|---|---|---|
| 1 | Overview | Hypothesis, run time, Claude Code version, observed model, N, number of cases, number of runs and abnormal runs, total cost. Warning if N is under 3 |
| 2 | Per-case comparison | Prompt, expected effect, and for each run k a baseline/variant pair (only the first pair expanded). Per run: final response (expanded), trace with tool results (collapsed), loaded instruction files (collapsed), changed files (list expanded, diff collapsed), exit code and anomaly flags |
| | Verdict | "Which side showed the behavior related to the expected effect more clearly?" Options: condition X / condition Y / no difference / can't tell, plus a note. Control cases show "no relevant difference is the expected value" |
| 3 | Summary | Case × verdict table, observed differences (free text) |
| 4 | Variant condition | `variant.patch` per file |
| 5 | Fixed conditions | Protocol table from `manifest.json` and the command |

The X/Y assignment and left/right order for blind mode are decided once on first open and stored in the browser. Toggling blind mode doesn't change them.

Verdicts and notes are saved in the browser's `localStorage` (keyed by experiment name and start time). They don't transfer to another browser or machine. To share, use "Save HTML" in the left menu to download a copy with the verdicts embedded.

## Limits

- Context injected by hook stdout isn't recorded.
- The model saying "I read X" isn't evidence. Only `instructions.jsonl` and `Read` calls in the trace count.
- N is small. When variance between runs is larger than the difference between arms, "can't tell" is the honest verdict.
