# 데모

`claude-sonnet-5`로 조건당 2회씩 실행한 실험 4개입니다. 폴더마다 `run.sh`, `variant.patch`, `report.html`이 있습니다.

| 데모 | 무엇을 확인하나 | 무엇이 보였나 |
|---|---|---|
| [fluent-korean](fluent-korean/) | 한국어 output style을 켜면 분석 글이 달라지는지 확인합니다. | 엠대시가 26개에서 1개로 줄었고, 문장이 서술어로 끝났습니다. |
| [payment-docs](payment-docs/) | 정책 문서를 넣으면 Claude가 읽고 따르는지 확인합니다. | run 4개 중 2개가 문서를 읽었고, 그 run만 정책을 따랐습니다. |
| [fastapi-architecture](fastapi-architecture/) | 아키텍처 문서를 주면 새 코드의 위치가 달라지는지 확인합니다. | 위치는 같았고, 테스트를 붙인 run이 0/2에서 2/2로 늘었습니다. |
| [doc-sentence](doc-sentence/) | 스펙의 숫자 하나(3회 → 2회)를 바꾸면 코드에 반영되는지 확인합니다. | 두 run 모두 `MAX_ATTEMPTS`가 3에서 2로 바뀌었습니다. |
