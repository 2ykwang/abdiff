# Fixed conditions (protocol) and experiment.json

Every run in an experiment gets the same conditions below. The only difference between baseline and variant is `variant.patch`. For each item, the "Verified by" column says whether it was confirmed by actually running Claude Code 2.1.243 or by the official docs.

## The command the runner executes

```
CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 claude -p "<prompt>" \
  --output-format stream-json --verbose \
  --setting-sources project \
  --strict-mcp-config \
  --no-session-persistence \
  --max-budget-usd <budget_usd> \
  --settings '{"hooks":{"InstructionsLoaded":[{"hooks":[{"type":"command","command":"cat >> <run>/instructions.jsonl; echo >> <run>/instructions.jsonl"}]}]}}' \
  [--model <model>] \
  --dangerously-skip-permissions | --permission-mode <mode> --allowedTools <list>
  < /dev/null > <run>/stream.jsonl 2> <run>/stderr.txt
```

The working directory is a worktree dedicated to the run. Before the run, the runner creates it with `git worktree add --detach <temp dir> HEAD`, applies `variant.patch` with `git apply` if this is the variant arm, runs `setup` if present, then freezes that state in a temporary commit. After the run it extracts `changes.patch` with `git add -A && git diff --cached <temp commit> --binary` and removes the worktree. So the variant patch and setup output never appear in `changes.patch`; only what the run itself changed does.

## Rationale per item

| Item | Value | Why | Verified by |
|---|---|---|---|
| `--setting-sources project` | Load project settings only | Drops `~/.claude/CLAUDE.md`, user plugins, hooks, and skills, which shrinks the noise surface. The variable is limited to files inside the project directory | Run: with `project` only, the project CLAUDE.md canary string showed up, 0 plugins, 0 SessionStart hooks. With `user` only, no canary, 17 plugins, 5 hook firings |
| `--strict-mcp-config` (no `--mcp-config`) | 0 MCP servers | MCP presence is a separate variable | Run: the init event shows `mcp_servers: []` |
| `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` | Auto memory off | Per the docs, auto memory is shared by every worktree of the same repo. Left on, it leaks between runs | Docs (memory) |
| `--no-session-persistence` | Don't save the session | Blocks conversation history sharing between runs and leaves nothing on disk | Docs (cli-reference) |
| `InstructionsLoaded` hook | Record which instruction files loaded | "Which instruction files actually entered context" comes from the harness, not from the model's self-report. Covers `.claude/rules`, `@import`, nested CLAUDE.md, and MEMORY.md | Run: injected via `--settings` JSON, it wrote `{"file_path":…,"memory_type":"Project","load_reason":"session_start"}` |
| `--max-budget-usd` | Per-run cost cap | Stops runaway runs | `claude --help` |
| Timeout | `timeout_sec` per run (default 600) | The runner kills the process group. A timed-out run is flagged in `run.json` | Run: exit 143, `timed_out: true` |
| Worktree created outside the repo | Temp directory | Claude Code loads every CLAUDE.md in parent directories. A worktree inside the repo would pick up the original's CLAUDE.md | Docs (memory: "How CLAUDE.md files load") |
| Fresh worktree per run | Isolation | Keeps one run's file changes invisible to the next | Runner implementation |
| No condition name in the worktree path or temp commit message | `run-<8 random chars>`, `abdiff: base` | The working directory path and recent commits enter the model's context (environment info). If the word `variant` is visible, there's a difference beyond the diff. The mapping lives only in `run.json` | Docs (context-window: "Environment info … Git branch, status, and recent commits load as a separate block at the very end of the system prompt") |
| `< /dev/null` | Close stdin | `-p` waits 3 seconds for stdin | Run: stderr warning |
| Execution order | Per test case, per run k: baseline then variant, sequential | Keeps time-of-day drift from landing on one arm | Runner implementation |

## Permission mode

`claude -p` is non-interactive, so nobody can answer a permission prompt. The default permission mode for `-p` is Manual, so file edits and commands get denied, and the result shows "blocked by permissions" instead of "effect of the instruction".

| `permission` value | Flags | Notes |
|---|---|---|
| `"bypass"` (default) | `--dangerously-skip-permissions` | Zero denials. The repo is safe because the worktree is disposable, but **Bash can touch the whole machine** |
| `{"mode": "acceptEdits", "allowed_tools": ["Bash(npm test *)", …]}` | `--permission-mode acceptEdits --allowedTools …` | Safe, but any command you didn't anticipate gets denied. Denials show up in the report's run metadata as "permission denials N" |

## experiment.json

Internal file the orchestrator writes from the questionnaire answers. Users don't create it by hand.

```json
{
  "name": "test-first-read",
  "hypothesis": "Adding the rule makes more runs Read the test file before editing code",
  "n": 3,
  "model": "claude-sonnet-5",
  "test_cases": [
    {"id": "TC-01", "kind": "target", "title": "formatDate timezone bug",
     "prompt": "Fix the bug where formatDate in src/utils/date.ts ignores the timezone",
     "expect": "In the variant, Read date.test.ts appears before the first Edit"},
    {"id": "TC-03", "kind": "control", "title": "README typo",
     "prompt": "Fix the typo in the README install section",
     "expect": "No effect. If the variant explores test files, that's over-application"}
  ]
}
```

| Field | Required | Description |
|---|---|---|
| `name` | yes | Experiment name. Must match the `.abdiff/<name>/` directory name |
| `hypothesis` | yes | One-sentence hypothesis |
| `test_cases[]` | yes | `id` (used as the directory name), `prompt` (run verbatim), `expect` (pre-run expectation, countable), `kind` (`target`: the variable applies to this task, `control`: it must not), `title` (optional, shown in the table of contents) |
| `n` | no | Repeats per arm. Default 3 |
| `model` | no | Value for `--model`. If omitted, `claude -p` uses its default model |
| `permission` | no | See "Permission mode" above. Default `"bypass"` |
| `timeout_sec` | no | Time limit per run in seconds. Default 600 |
| `budget_usd` | no | `--max-budget-usd` per run. Default 2.0 |
| `reading` | no | Settings for the optional `reading.py` step: `{"model": "<model for the reading>", "budget_usd": 0.5, "timeout_sec": 180}`. Every key is optional. Use a model other than the one under test when possible. What the reader sees: [reading.md](reading.md) |
| `setup` | no | Shell command run in every worktree. The worktree has no untracked files (`node_modules` etc.), so prompts that run tests need this. The env var `ABDIFF_PROJECT` (path to the original project) is available. The same command applies to both arms |
