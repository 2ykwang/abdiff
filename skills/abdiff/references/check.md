# LLM reading of runs (reading.py)

An optional step between the run and the report. A separate Claude call reads one run at a time and reports, for each countable statement in `expect`, whether that run shows it and where. A person still compares the arms and makes the verdict. Treat a `yes` as a pointer to a citation, not as a count.

## What the reader sees

| Given | Withheld | Why |
|---|---|---|
| Task prompt, `expect` | Hypothesis, condition name, `variant.patch` | The reader sees one run and isn't told which arm it is. `expect` is needed to know what to look for, so its direction can still be inferred; withholding the rest keeps the arm out |
| Final response | | What reached the user |
| Tool calls in order (summarized inputs), each result clipped to 2,000 chars, the whole section to 150,000 | `instructions.jsonl` | Instruction loads reveal the arm directly. Tool order is needed for "before / after" statements |
| `changes.patch`, clipped to 40,000 chars | | The artifact |
| Exit code, timeout, error, missing result event | Cost, tokens, duration, turn count | Length and cost aren't evidence |

No tools, no MCP, no user, project, or local settings, an empty temporary working directory per call, auto memory off. The command is in `readings.json`. The reading must not be done in the orchestrator's session or a subagent: both carry the project's CLAUDE.md hierarchy ([sub-agents docs](https://code.claude.com/docs/en/sub-agents)), which is the variable under test.

## Why this shape

- **One run against pre-written statements, not a pair.** Pairwise judging is where first-position preference lives (Zheng et al.), and the tool's question is whether the expected effect appeared, not which side is better (design.md §2, §9).
- **`yes` / `no` / `unclear` per statement plus a citation.** The citation is what lets the person check the reader instead of trusting it. `unclear` is allowed because LLM graders lean lenient (Judging the Judges).
- **Different model when possible.** Models favor their own generations as graders (Panickssery et al.); Anthropic's eval docs say to grade with a different model. `reading.model` is separate from the experiment's `model` for that reason.
- **Collapsed, no counts in the summary line.** So the person reads the record before the reading of it.

## Limits

- Blindness isn't complete. If the variant adds a doc and the run reads it, the trace reveals the arm.
- The record is untrusted text. A response, a file, or a tool result can contain instructions aimed at the reader. No tools limits what that can do, not what it can say; check every citation in the raw record.
- Verbosity still matters: a long run has more places for evidence to be, and more of it gets clipped. Clipped evidence shows up as `unclear` at best.
- `expect` written as prose the reader can't map to one-run facts produces vague or invented findings. The fix is a more countable `expect` (design.md §2), not a better reader.
- Agreement with human verdicts hasn't been measured here. The sources below that discuss model grading say to measure it before relying on it.

## References

- Zheng et al., "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena", NeurIPS 2023. https://arxiv.org/abs/2306.05685 — position, verbosity, self-enhancement bias in pairwise judging.
- Panickssery et al., "LLM Evaluators Recognize and Favor Their Own Generations", NeurIPS 2024. https://arxiv.org/abs/2404.13076 — self-preference.
- "Judging the Judges", 2024. https://arxiv.org/abs/2406.12624 — leniency, sensitivity to prompt length.
- Anthropic, "Develop test cases". https://platform.claude.com/docs/en/test-and-evaluate/develop-tests — use a different model to evaluate than the one that generated the output.
- Anthropic Engineering, "Demystifying evals for AI agents". https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents — transcript vs outcome grading; calibrate graders against humans.
- OpenAI, "Evaluation best practices". https://developers.openai.com/api/docs/guides/evaluation-best-practices — scale a model judge only once it agrees with human annotations.
