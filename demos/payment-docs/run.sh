#!/usr/bin/env bash
# Demo: domain docs absent (baseline) vs present (variant). CLAUDE.md never mentions docs/.
# Fixture: billing-en. The docs hold billing policy that the code doesn't encode.
source "$(dirname "$0")/../_lib.sh"
demo_setup billing-en
commit_head ':!docs'
git add docs
run_demo payment-docs \
  "With docs/ present, implementations follow policy that only the docs state: downgrades are deferred to the next cycle with no negative amount, legacy plans prorate over 30 days, retries reuse the same Idempotency-Key and never retry declined codes." \
  "$(tc TC-01 target 'changePlan' 'Implement changePlan(account, newPlanId, at) in src/proration.js. It returns what to charge this cycle when an account changes plan, and add tests. account looks like { planId, anchorDay }.' 'Variant: Read docs/billing-cycle-and-proration.md before the first edit; downgrade returns amount 0 and takes effect next cycle (no negative or refund amount); legacy plans use a 30-day denominator. Baseline expected: 0/2 on each.'),$(tc TC-02 target 'Retry in charge' 'Make charge in src/payment.js retry when the payment request fails. Add tests.' 'Variant: Read docs/payment-gateway-payko.md before the first edit; retries send the same Idempotency-Key; DECLINED-class errors are not retried. Count the same for the baseline; a ceiling here means the docs were not needed for this behavior.'),$(tc TC-03 control 'listPlansByPrice' 'Add listPlansByPrice() to src/plans.js that returns plans sorted by monthly price ascending, and add a test.' 'No effect. Excluding legacy plans or adding unrequested conditions in the variant would be over-application. Note whether the variant reads docs anyway and how much longer it takes.')"
