# abdiff

A tool that checks whether editing CLAUDE.md actually changes how Claude behaves.

You add a rule to CLAUDE.md, use it a few times, and end up guessing whether Claude follows it. This tool runs the same tasks before and after the change and puts the two results side by side.

[한국어](README_ko.md)

## What you learn

- Whether a new rule actually changes how Claude works or what it produces
- Whether a rule you want to delete was doing anything
- Whether a reference doc gets read and followed, or just sits there
- Which of two wordings of the same rule Claude follows more consistently

## Usage

```
/plugin marketplace add 2ykwang/abdiff
/plugin install abdiff@2ykwang
```

1. Edit the rule. Leave the change uncommitted.
2. Run `/abdiff:abdiff <what you want to test>`. Check the questionnaire and answer "go".
3. Open `.abdiff/<experiment>/report.html`. Inside Claude Code: `!open <path>`.

Questionnaire item 8 can add an isolated Claude reading of each run: it marks each expected-effect statement `yes`, `no`, or `unclear` with a citation. It doesn't compare the two sides or make the verdict; you do.

## Demos

Four experiments that show what this tool is for. Each link opens the report. The setup and the exact change for each are in [demos/](demos/).

- [fluent-korean](https://2ykwang.github.io/abdiff/demos/fluent-korean/report.html): whether turning on a Korean output style changes a code-analysis write-up
- [payment-docs](https://2ykwang.github.io/abdiff/demos/payment-docs/report.html): whether Claude reads and follows policy docs once they exist
- [fastapi-architecture](https://2ykwang.github.io/abdiff/demos/fastapi-architecture/report.html): whether an architecture doc changes where new endpoint code lands
- [doc-sentence](https://2ykwang.github.io/abdiff/demos/doc-sentence/report.html): whether changing one number in an imported spec reaches the code

## Good to know

- Total runs = `2 × repeats × test cases`. Time and cost depend on the model and the task.
- Runs execute in a throwaway copy of the project with permission prompts skipped. The copy is not a sandbox: Bash can still touch files outside it. For projects you don't trust, use allowlist mode. Setup is in `skills/abdiff/references/protocol.md`.
- User-level settings are not applied. Only files inside the project can be the variable.
- Requires Claude Code CLI, git, and python3 3.9+.

## License

MIT
