# Billing cycle and proration policy

This document covers the Workhub subscription billing cycle, how money is handled on plan changes, and the proration rules.
The code (`src/proration.js`) only provides calculation tools; which calculation applies in which situation is decided by the
policy here. The finance team owns this policy, and changes go through finance review (see "Change procedure" in `glossary-and-incident-log.md`).

## 1. Billing cycle

- Every account has an `anchorDay` (1..28). A new cycle starts on that day each month, and one month's fee is charged up front on the cycle start date.
- A cycle is `[start date, next start date)`. With an anchor of March 10, one cycle runs from March 10 through April 9.
- `anchorDay` is set from the date of the first paid conversion. The paid conversion date is the day the 14-day trial ends.
- Days 29, 30, and 31 are never used as anchors. In August 2023 we moved all 412 accounts with those anchors to day 28,
  because cycle lengths diverged per account in February and CS tickets piled up. The finance team keeps the list of moved accounts.
- The billing batch runs at 09:00 KST on the cycle start date. Plan changes made before that time are reflected in the cycle starting that day.

## 2. Date basis: Korea Standard Time (KST) calendar dates

- Every billing-related date is a **KST calendar date**. Servers and the database run in UTC, but any date entering billing logic must already be a
  `YYYY-MM-DD` string converted to KST.
- Reason: the "issue date" on the tax invoice must equal the cycle start date, and tax invoices are issued on Korean time.
  Using UTC dates would push charges between 00:00 and 09:00 KST to the previous day. This actually happened in June 2023 (INC-2023-06).
- So billing logic never uses the time component of a `Date` or the user's browser time zone. Overseas customers are on KST as well.

## 3. Money handling on plan changes

Plan changes fall into three kinds. The criterion is **the monthly fee**. Seat count and features are not considered.

| Change | Takes effect | Billing |
|---|---|---|
| Upgrade (monthly fee goes up) | Immediately | Prorate the difference over the remaining days and charge immediately |
| Downgrade (monthly fee goes down) | Next cycle start date | No charge and no refund this cycle. New fee from the next cycle |
| Lateral move (same monthly fee) | Immediately | 0 |

### 3.1 Upgrade

- The change date itself counts as a remaining day. Changing on March 25 with a cycle ending April 10 leaves 16 remaining days.
- Charge = (new plan monthly fee − old plan monthly fee) × remaining days ÷ cycle days. Truncate below 1 KRW.
- Cycle days are actual calendar days (28..31). Legacy plans follow section 4 instead.
- The upgrade invoice is issued and charged immediately. If the payment fails, the plan change is rolled back too.

### 3.2 Downgrade: no money moves this cycle

- A downgrade takes effect **from the next cycle start date**. The change request is stored only as a "scheduled" change.
- The difference for the rest of the current cycle is not refunded or returned as credit. The system must never produce a negative amount.
- Background: until November 2022, downgrades were also prorated immediately and the difference became a negative invoice. Every negative invoice
  then required a corrected tax invoice at month-end close, and the finance team closed November 8 days late (INC-2022-11).
  The December 2022 policy meeting fixed "downgrades are deferred, no refunds", and it is in section 7.3 of the terms of service.
- If CS requests an exception, the finance team handles it as a manual credit. The system has no exception path.
- Upgrading again while a downgrade is scheduled cancels the scheduled downgrade.

### 3.3 Lateral move

- Moving to a plan with the same monthly fee (none in the current catalog, but past regional plans had them). Immediate, charge 0.

## 4. Proration for legacy plans (`L-` prefix)

- 2019 contract, article 4: "For proration, one month is 30 days." So any proration involving a legacy plan uses **30 as the denominator**,
  regardless of the cycle's actual length. The numerator (remaining days) is the actual remaining days, capped at 30.
- This rule applies when the existing plan is legacy. Upgrading from a legacy plan to a current plan is still the last cycle under the old contract,
  so the 30-day basis applies.
- In a 31-day cycle a legacy customer who upgrades pays slightly more than a current customer. That is what the contract says, and customers know it.
  "Fixing" it to actual days would breach the contract.

## 5. Worked examples

| Situation | Calculation | Amount |
|---|---|---|
| Team (99,000) → Business (290,000), anchor 10, changed March 25 | (290,000 − 99,000) × 16 ÷ 31 | 98,580 KRW |
| Business → Team, changed March 25 | Team fee from the next cycle (April 10). This cycle charge 0 | 0 KRW |
| L-growth-2019 (149,000) → Business (290,000), anchor 10, changed March 25 | (290,000 − 149,000) × 16 ÷ 30 | 75,200 KRW |
| Starter → Team, changed on the cycle start date | Remaining days = cycle days, full difference | 70,000 KRW |

## 6. Out of scope

- Annual billing is not handled by this module. The 37 annual customers are invoiced manually by the finance team.
- Enterprise is invoiced per contract (net-30) and has no plan-change concept.

## 7. Cancellation

- Cancellation takes effect at the end of the cycle. The remaining period stays usable and there is no refund. Same principle as downgrades.
- Immediate cancellation with refund is finance-only (legal disputes, duplicate signups, and so on). The system has no immediate-cancel path.
- An account with a scheduled cancellation does not accept plan changes. The scheduled cancellation must be removed first.

## 8. Trial and anchor selection

- The trial is 14 days and needs no card. There are no invoices during the trial.
- If a card is on file when the trial ends, the account converts that day, and that day's date becomes `anchorDay`.
  If that day is the 29th, 30th, or 31st, `anchorDay` is set to 28 and only the first cycle runs a day or two longer. The first cycle is charged a full month.
- If no card is on file at trial end, the account becomes read-only, and the day a card is later added becomes the anchor.

## 9. Common implementation mistakes

- Excluding the change date from remaining days. It is included. A change on the cycle start date has the whole cycle remaining.
- Giving a "fair" credit on downgrade. Forbidden by policy, and the cause of INC-2022-11.
- Using a 30-day denominator for current plans, or actual days for legacy plans. Legacy status is decided by the **existing** plan.
- Truncating only once at the end. Truncate once in proration, once after coupons, once in VAT.
- Leaving the plan changed after an upgrade payment fails. On payment failure, roll back the plan change.
- Stacking a second scheduled downgrade on an account that already has one. Overwrite instead of stacking.
