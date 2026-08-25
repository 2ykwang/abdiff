#!/usr/bin/env bash
# Demo: fluent-korean output style off (baseline) vs on (variant).
# Fixture: billing-ko (a Korean subscription-billing module). Prompts ask for Korean write-ups.
source "$(dirname "$0")/../_lib.sh"
demo_setup billing-ko
commit_head
mkdir -p .claude/output-styles
cp "$ROOT/demos/fluent-korean/fluent-korean.md" .claude/output-styles/fluent-korean.md
printf '{"outputStyle": "fluent-korean"}\n' > .claude/settings.json
git add .claude
run_demo fluent-korean \
  "With the fluent-korean output style applied, Korean write-ups end sentences with full predicates instead of noun fragments, drop fewer particles, and avoid em dashes; the content stays the same." \
  "$(tc TC-01 target 'Gap analysis of charge()' 'src/payment.js의 charge를 읽고, docs/payment-gateway-payko.md 기준으로 빠진 처리를 정리해서 보고해줘. 코드는 고치지 마.' 'Variant: fewer lines ending in noun fragments (e.g. "판단 불가", "전파만 함"), more sentences ending in -다/-니다, no em dashes. Same list of missing behaviors on both sides.'),$(tc TC-02 target 'Wiki article on billing cycles' 'src/proration.js와 docs/billing-cycle-and-proration.md를 읽고, 청구 주기와 일할 계산이 코드에서 어떻게 구현돼 있고 정책과 어디가 다른지 팀 위키에 올릴 기술 글로 정리해줘. 코드는 고치지 마.' 'Variant: complete sentences with predicates and particles throughout; baseline: telegraphic bullet fragments. Facts (cycle bounds, proration, legacy 30-day denominator, downgrade deferral) appear on both sides.'),$(tc TC-03 control 'Code only' 'src/plans.js에 플랜을 월 요금 오름차순으로 돌려주는 listPlansByPrice() 함수를 추가해줘. 설명은 하지 말고 코드만 고쳐.' 'No effect. Same kind of diff on both sides and a one-line answer. A long Korean explanation in the variant would be over-application.')"
