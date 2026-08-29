# Experiment design guide

Most experiments fail because of design, not tooling. This doc lists what the orchestrator checks before filling in the questionnaire, and which prompts expose the effect for each kind of change. External sources are in the reference list at the end; points adapted to agent experiments are marked "adapted".

## 1. One variable

The difference between baseline and variant must be one change you can name in a sentence. Change two or more of content, location, size, and load mechanism at once and you can't say what caused a difference.

- Violation: an experiment that "splits" instructions across files but also adds new rules and a structure overview. You can't separate the effect of splitting from the effect of the new content.
- Violation: an experiment that links a doc with `@import` but also adds the doc itself. The doc's existence and the link mechanism change together. To compare link mechanisms, keep the doc in both arms and change only the link line.

When the diff spans several files, check that each file is part of the same change. A large diff, like adding one whole doc, is fine as long as it's one variable.

## 2. Write the expected effect before running, and make it countable

Don't revise `expect` after the run. Pick a plausible criterion after seeing the results and anything reads as success. Use this form:

> On [observation surface], the number of runs satisfying [condition] goes from a/N in baseline to b/N in variant: [up / down / same].

There are three observation surfaces. If order matters, count in the trace. If the artifact matters, count in `changes.patch`. If what reached the user matters, count in the final response. `instructions.jsonl` only proves a file entered context, so count compliance separately.

| Surface | Bad | Good |
|---|---|---|
| Trace | Checks tests properly first | More variant runs have `Read test/date.test.js` before the first `Edit` |
| Trace | Consults the docs | Count runs in the pointer arm with `Read docs/DOMAIN.md` before the first `Edit` |
| Trace | Definitely runs the tests | 3/3 variant runs have `Bash node --test` after the last `Edit` |
| Change diff | Error handling improves | Count runs whose diff contains `AppError(` and no new `Error(` |
| Change diff | Follows the coupon rules | Count runs whose diff has both the logic rejecting percent > 50 and its test |
| Response body | Reports results well | Count runs whose response has both the pass count and the fail count as numbers. "All passed" doesn't count |

When one sentence has several conditions, say AND or OR. Don't use time, turn count, or tokens as the expected effect.

## 3. Target cases and controls

`kind` only says whether the variable applies to the case. Whether you expect a difference is stated in `expect`.

- `target`: the variable applies to the task. A rule-add experiment expects "up"; a rule-delete or dilution experiment can expect "same".
- `control`: the variable must not apply. Expect no effect. A difference in the variant means the variable spread where it shouldn't. This is a negative control (adapted).

Pick a control in the same code area as the targets, with similar complexity and similar tool use, but without the trigger for the variable. A README typo fix or a `package.json` lookup finishes fast in both arms and can't reveal side effects like over-exploration or scope creep.

## 4. Check whether the baseline already does it

If the baseline already shows the target behavior (ceiling effect), adding the rule shows no difference. If the prompt never creates the situation that triggers the rule (floor effect), even a good rule looks useless.

- Violation: testing "read the test file before editing" when the baseline already read the tests before the first Edit in both cases.
- Violation: testing dilution of a rounding rule with a "refactor without behavior change" request. No rounding decision ever came up.

Questionnaire item 7 asks the user. If the baseline already does it, change the prompt or treat the rule as a deletion candidate. If unknown, run anyway and look at the baseline runs first in the report. If the baseline was already doing it, the experiment showed "the rule isn't needed", not the rule's effect.

## 5. Choose N by the kind of hypothesis

| Hypothesis | Default N | Why |
|---|---|---|
| There's an effect (rule add, more specific wording, doc link) | 3 | You only need to see a direction repeat on one side |
| There's no effect (rule delete, dilution, relocation), or priority under conflict | 5 | "No difference" has to survive more chances to show a difference |

These numbers are a practical rule balancing cost and human judging effort, not a power calculation. With N=1 you can't conclude "no difference".

## 6. Don't put search hints in the prompt

Phrases like "follow the project rules", "check the relevant docs", or "look at CLAUDE.md" make the model search for docs even without the variant. Then you're measuring the prompt's instruction, not the instruction file's effect (adapted). Write only what a real user would say.

## 7. Prompts by kind of change

| Change | Target example | Control example | What to count |
|---|---|---|---|
| Rule add | Fix the timeZone bug in `formatDate` / add env var override to `parseConfig` | An analysis request that edits no files | Runs showing the behavior the rule asks for |
| Rule delete (no-effect hypothesis, N=5) | Two tasks adding a new public function | Internal cleanup that doesn't change the public API | Runs where the behavior persists after deletion |
| More specific wording | Bug fix / refactor (if the rule says "after every change", a refactor triggers it too) | Analysis request with no edits | Runs satisfying the more specific condition (e.g. pass and fail counts) |
| Relocation (root ↔ `.claude/rules` ↔ nested CLAUDE.md) | A task editing a file under that path / a task creating a new file (a Write with no prior Read exposes the lazy-load timing) | A task outside that path | `load_reason`, whether it loaded before the first Edit, behavior |
| Reference doc link (`@import` vs pointer) | Two feature implementations that need the doc's rules | A feature of similar size unrelated to the doc | import: `include` load; pointer: `Read <doc>`; both: rule compliance |
| Dilution (key rule + unrelated rules added) | An implementation whose input actually triggers the key rule | A complex task unrelated to the key rule | Runs complying with the key rule. Increase in unrelated exploration |
| Conflict (N=5) | Two fixes that must create a new error message | A task editing the same file that needs no new message | Which rule was followed. Changing existing messages unnecessarily is a side effect |

When moving the same text between locations, compare one pair of locations at a time. In doc-link experiments, keep the doc in both arms and change only the link line.

## 8. Reading results

- Separate "no difference" from "can't tell". The first means you could compare and found no relevant difference. The second means errors, timeouts, contradictory runs, or too little evidence to conclude.
- The conclusion of a deletion experiment isn't "no difference seen, so delete". It's "across several situations, we didn't observe a failure caused by removing it".
- If you want to change the hypothesis or expectation after seeing results, close that experiment as exploration and start a new one.

## 9. What this tool doesn't do

| Not done | Why | Minimum allowed instead |
|---|---|---|
| Statistical tests | N is small and each case is a different task, so samples aren't independent or homogeneous | a/N vs b/N per case |
| Pairwise or aggregate LLM verdicts | They add position, length, and self-preference bias, and answer "which is better", which isn't the question | Optional check of one run at a time against the pre-written `expect`, with citations, not told the condition. A person still compares the arms. See [check.md](check.md) |
| Automatic prompt generation | Generators leak the target rule into the prompt or produce easy tasks with no trigger | A blank form and a checklist |
| Aggregate score, automatic winner | Opposite effects across cases cancel out in an average | Per-case human verdicts with raw evidence |

## References

Sources for the principles above. Points applied to agent experiments are adaptations. These are from training knowledge, not re-checked on the web, so verify before citing.

- Preregistration: Nosek et al., "The preregistration revolution", PNAS 2018.
- Interpreting null results: Altman & Bland, "Absence of evidence is not evidence of absence", BMJ 1995.
- Negative controls: Lipsitch, Tchetgen Tchetgen & Cohen, "Negative Controls: A Tool for Detecting Confounding and Bias in Observational Studies", Epidemiology 2010.
- Ceiling and floor effects: Terwee et al., Journal of Clinical Epidemiology 2007.
- Demand characteristics: Orne, American Psychologist 1962.
- Single variable: Montgomery, Design and Analysis of Experiments. Single-variable designs miss interactions, but this tool attributes one change, so it fits.
- Human pairwise judgment and bias: Zheng et al., "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena", NeurIPS 2023; MacCoun & Perlmutter, "Blind analysis", Nature 2015.
