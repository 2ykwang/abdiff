---
name: abdiff
description: Check whether one change to Claude Code's instructions or context (CLAUDE.md, .claude/rules, referenced docs, skills) actually changes behavior. Runs the same prompts against HEAD and HEAD + the uncommitted diff, N times each, and builds an HTML report for a person to compare the runs with condition labels hidden. Use it to test adding, deleting, rewording, or moving a rule, or to check whether an @import or a referenced doc is loaded and followed. Not for checking application code or anything automated tests already cover.
disable-model-invocation: true
argument-hint: "[what you want to test]"
---

# abdiff

Find out what one change to instructions or context does by running **the same prompt × two conditions × N times**. A person reads the report and decides. The agent running this skill (the orchestrator) defines the experiment, runs the runner, builds the report, and hands it to the user. That's the whole job.

Talk to the user in the user's language. Keep the field names below (`n`, `target`, `control`) as they are in files.

Terms:

- **baseline**: HEAD
- **variant**: HEAD plus the uncommitted changes in the working tree
- **test case**: one prompt. `kind` is `target` when the change should apply to the task, `control` when it should not (no effect expected)
- **run**: one execution
- **trace**: the sequence of tool calls in one run

## Procedure

### 0. Preconditions

Check all three. If any fails, stop and tell the user.

- The project is a git repository with a HEAD.
- `git diff HEAD --stat` is not empty. This diff is the variant. New files must be `git add`ed to show up.
- `claude`, `git`, and `python3` (3.9+) are on PATH.

### 1. Questionnaire

Read the diff and the repository layout, then send **one questionnaire with every field filled in**. The user answers only what they want to change; unanswered fields take the defaults. Use plain words with the user, not experiment jargon. Send it as nested markdown bullets, not a code block; space-aligned text breaks in chat.

> **abdiff questionnaire.** Answer only what you want to change. Blank fields take the values below.
>
> 1. Experiment name: `<short kebab-case name derived from the diff and $ARGUMENTS, if given>`
> 2. Model: `<current session model>`
> 3. Repeats: 3 (5 for rule deletion, dilution, or conflict experiments)
> 4. Hypothesis
>    - <one sentence from the diff: what changes and how>
> 5. Test cases
>    - **TC-01** (the change applies)
>      - Prompt: "<prompt>"
>      - Expected: <a countable statement about tool order, file changes, or the final answer>
>    - **TC-02** (the change applies)
>      - Prompt: "<prompt>"
>      - Expected: <same form>
>    - **TC-03** (the change should not apply)
>      - Prompt: "<a code task adjacent to the change but outside its scope>"
>      - Expected: No effect. <what would count as over-application if it shows up in the variant>
> 6. Variable check: `<git diff HEAD --stat summary>`. Is this one change the variable? (If several files: are they all part of the same change?)
> 7. Does the baseline already do this? (Answer "don't know" if unsure)
>
> <2 × repeats × cases> runs. Time and cost depend on the model and the task (for reference: haiku 10–90 s per run, opus 20–150 s). Runs execute in a temporary copy where Claude edits files and runs commands without permission prompts.
> Reply "go" to start.

The rules for filling it in are in [references/design.md](references/design.md). At minimum check these three:

- Expected effects must be countable. Write "Read test/x.test.js before the first Edit", "diff uses AppError", "answer states pass and fail counts". Don't write "does better".
- The control is a code task adjacent to the variable. A README typo fix or a file lookup can't reveal side effects.
- A case expected to show "no effect" is `kind: control`. A case the change applies to but where you expect "same" (deletion or dilution experiments) stays `target`, with "same" in the expected statement.

If the answer to 7 is "already does it", the experiment can't show an effect. Suggest changing the prompt or treating the rule as a deletion candidate. If "don't know", proceed, and tell the user to read the baseline runs first.

Save the answers to `.abdiff/<name>/experiment.json`. The format is in the "experiment.json" section of [references/protocol.md](references/protocol.md). Use the `permission` field if allowlist mode is needed.

### 2. Run

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/abdiff/scripts/run.py" .abdiff/<name>/experiment.json
```

The runner creates a temporary worktree per run, executes `claude -p`, and writes raw records to `.abdiff/<name>/runs/`. The fixed conditions and their rationale are in [references/protocol.md](references/protocol.md). It takes a while: run it in the background and watch stderr for progress. If any run fails, the runner prints a warning with the `stderr.txt` path and exits 1. Tell the user to exclude that run when judging.

### 3. Report

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/abdiff/scripts/report.py" .abdiff/<name>
```

This writes `.abdiff/<name>/report.html`. Give the user the path and have them open it in a browser (`open .abdiff/<name>/report.html` on macOS). The report layout and the record formats are in [references/trace.md](references/trace.md).

### 4. Judging

**A person judges.** The report opens with blind mode on. Verdicts are entered in the report and stored in the browser; to share, use "Save HTML" to download a copy with the verdicts. "No difference" and "Can't tell" are different answers: the first means the runs were comparable and showed no relevant difference; the second means variance or errors made a conclusion impossible.

### 5. Cleanup

The runner removes its worktrees. If some remain after a forced stop, suggest `git worktree prune`. The variant changes stay in the working tree. Adopt them (commit) when the expected change shows up repeatedly and the control's side effects are acceptable; otherwise revert. Don't confirm a deletion or a move on "saw no difference" alone.

## Don'ts

- **Don't edit or strengthen the prompts.** Don't paste document content into a prompt. That breaks the "no context" condition. Don't add hints like "follow the project rules".
- Don't run `claude -p` outside `run.py`. The conditions would differ.
- Don't summarize the results or say which side is better. If the user asks, count only facts from the traces, diffs, and answers (e.g. the number of runs with a test-file Read before the first Edit).
- Don't introduce any difference between baseline and variant other than the diff (flags, env vars, settings).
- Don't change the hypothesis or expected effects after seeing results. Start a new experiment instead.
- Don't touch the working tree while an experiment is running.
