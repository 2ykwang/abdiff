# Demos

[한국어](README_ko.md)

Four experiments on `claude-sonnet-5`, 2 runs per side. Each folder has `run.sh`, `variant.patch`, and `report.html`.

| Demo | What it checks | What we saw |
|---|---|---|
| [fluent-korean](https://2ykwang.github.io/abdiff/demos/fluent-korean/report.html) | Whether turning on a Korean output style changes a code-analysis write-up. | Em dashes dropped from 26 to 1, and sentences ended in predicates. |
| [payment-docs](https://2ykwang.github.io/abdiff/demos/payment-docs/report.html) | Whether Claude reads and follows policy docs once they exist. | 2 of 4 runs read the docs, and only those runs followed the policy. |
| [fastapi-architecture](https://2ykwang.github.io/abdiff/demos/fastapi-architecture/report.html) | Whether an architecture doc changes where new endpoint code lands. | Layout was the same; runs that added tests went from 0/2 to 2/2. |
| [doc-sentence](https://2ykwang.github.io/abdiff/demos/doc-sentence/report.html) | Whether changing one number in an imported spec (3 → 2 attempts) reaches the code. | `MAX_ATTEMPTS` went from 3 to 2 in both runs. |
