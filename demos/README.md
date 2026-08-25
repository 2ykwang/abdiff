# Demos

[한국어](README_ko.md)

Four experiments on `claude-sonnet-5`, 2 runs per side. Each folder has `run.sh`, `variant.patch`, and `report.html`.

| Demo | What it checks | What we saw |
|---|---|---|
| [fluent-korean](fluent-korean/) | Whether turning on a Korean output style changes a code-analysis write-up. | Em dashes dropped from 26 to 1, and sentences ended in predicates. |
| [payment-docs](payment-docs/) | Whether Claude reads and follows policy docs once they exist. | 2 of 4 runs read the docs, and only those runs followed the policy. |
| [fastapi-architecture](fastapi-architecture/) | Whether an architecture doc changes where new endpoint code lands. | Layout was the same; runs that added tests went from 0/2 to 2/2. |
| [doc-sentence](doc-sentence/) | Whether changing one number in an imported spec (3 → 2 attempts) reaches the code. | `MAX_ATTEMPTS` went from 3 to 2 in both runs. |
