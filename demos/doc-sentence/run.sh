#!/usr/bin/env bash
# Demo: one number in an imported spec changes. Both conditions import docs/payment-gateway-payko.md;
# the variant changes "at most 3 attempts" to "at most 2 attempts".
# Fixture: billing-en.
source "$(dirname "$0")/../_lib.sh"
demo_setup billing-en
printf '@docs/payment-gateway-payko.md\n' >> CLAUDE.md
commit_head
sed -i '' 's/at most 3 attempts/at most 2 attempts/g' docs/payment-gateway-payko.md
[ "$(grep -c 'at most 2 attempts' docs/payment-gateway-payko.md)" = "2" ]
run_demo doc-sentence \
  "Changing the retry cap in the imported spec from 3 attempts to 2 changes the constant and the test assertions in the implementation from 3 to 2." \
  "$(tc TC-01 target 'Retry in charge' 'Make charge in src/payment.js retry when the payment request fails. Add tests.' 'Baseline: max 3 attempts (a constant = 3 or calls.length 3 in tests). Variant: max 2 attempts. Both: same Idempotency-Key reused across attempts, no retry on DECLINED-class errors.'),$(tc TC-02 control 'Zero-amount charge' 'Make charge in src/payment.js skip PayKo when amount is 0 and return { status: \"DONE\", paymentKey: null }. Add tests.' 'No effect. Both sides: no gateway.request call for amount 0. The retry cap is irrelevant to this task.')"
