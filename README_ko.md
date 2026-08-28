# abdiff

CLAUDE.md를 고쳤을 때 Claude의 행동이 정말 달라지는지 확인하는 도구입니다.

CLAUDE.md에 규칙을 넣어도 Claude가 그 규칙을 따르는지는 몇 번 써 보고 감으로 판단하게 됩니다. 
이 도구는 규칙을 넣기 전과 넣은 후에 같은 작업을 각각 시키고, 두 결과를 나란히 비교해서 보여줍니다.

## 알 수 있는 것

- 새로 넣은 규칙이 Claude의 작업 방식이나 결과물을 실제로 바꾸는지
- 지우려는 규칙이 정말 필요했던 규칙인지
- 참고하라고 둔 문서를 Claude가 실제로 읽고 따르는지, 아니면 그 문서가 있기만 한 상태인지
- 같은 규칙을 두 가지 문구로 적었을 때 어느 문구를 Claude가 더 일관되게 따르는지

## 사용

```
/plugin marketplace add 2ykwang/abdiff
/plugin install abdiff@2ykwang
```

1. 규칙을 고칩니다. 고친 내용은 커밋하지 않은 상태로 둡니다.
2. `/abdiff:abdiff <실험 내용>`을 실행합니다. 질문지를 확인한 뒤 "진행"이라고 답합니다.
3. `.abdiff/<실험 이름>/report.html`을 열어 봅니다. Claude Code 안에서는 `!open <경로>`로 열 수 있습니다.

설문 8번을 켜면 격리된 Claude 호출이 각 run을 읽고, 기대 효과의 각 문장을 `yes` / `no` / `unclear`로 근거와 함께 표시합니다. 두 조건을 비교하거나 판정을 내리지는 않습니다. 판정은 직접 합니다.

## 데모

이 도구를 어디에 쓰는지 보여주는 실험 4개입니다. 링크를 열면 리포트가 나옵니다. 실행 스크립트와 바꾼 내용은 [demos/](demos/)에 있습니다.

- [fluent-korean](https://2ykwang.github.io/abdiff/demos/fluent-korean/report.html): 한국어 output style을 켜면 코드 분석 글이 달라지는지
- [payment-docs](https://2ykwang.github.io/abdiff/demos/payment-docs/report.html): 정책 문서를 넣으면 Claude가 읽고 따르는지
- [fastapi-architecture](https://2ykwang.github.io/abdiff/demos/fastapi-architecture/report.html): 아키텍처 문서를 주면 새 코드의 위치가 달라지는지
- [doc-sentence](https://2ykwang.github.io/abdiff/demos/doc-sentence/report.html): 스펙의 숫자 하나를 바꾸면 코드에 반영되는지

## 알아둘 것

- 실행 횟수는 `2 × 반복 횟수 × 테스트 케이스 수`입니다. 시간과 비용은 모델과 작업에 따라 다릅니다.
- 실험은 임시 복사본에서 권한 확인 없이 실행됩니다. 이 복사본은 샌드박스가 아니라서 Bash 명령은 복사본 밖의 파일에도 영향을 줄 수 있습니다. 신뢰할 수 없는 프로젝트라면 허용 도구 목록 모드를 씁니다. 설정 방법은 `skills/abdiff/references/protocol.md`에 있습니다.
- 사용자 전역 설정은 적용하지 않습니다. 프로젝트 안의 파일만 실험 대상으로 삼을 수 있습니다.
- 필요한 것: Claude Code CLI, git, python3 3.9+.

## 라이선스

MIT
