# PG (PayKo) integration contract and operational notes

We use a single PG, PayKo. `charge` in `src/payment.js` is a thin function that calls PayKo `/v1/payments`.
How the PayKo API behaves, what the contract restricts, and what went wrong in the past are not in the code. This document records them.

## 1. Contract overview

- Contract signed March 2022. Three payment methods: card, virtual account, bank transfer.
- Fees: card 2.3%, virtual account 300 KRW per transaction, bank transfer 1.5%.
- Settlement: D+2 business days. Settlement files arrive daily at 06:00 over SFTP; the finance team reconciles them against invoices.
- The PayKo contact channel and incident phone numbers are on the internal wiki under "Payments/PayKo". They are not recorded here.

## 2. API behavior

### 2.1 Idempotency key (`Idempotency-Key` header)

- If a request carries an `Idempotency-Key` header, PayKo **returns the first response unchanged for any request with the same key for 24 hours.**
  It does not create a second payment.
- Without the header, every request creates a new payment. The same `orderId` does not prevent this (`DUPLICATE_ORDER` is raised only after a payment is
  `DONE`; while one is in progress, both can go through).
- Generate a new key per request, but **when retrying the same payment, always send the same key again.** A new key on every retry is the same as no key.
- This was the cause of the March 2024 double-charge incident (INC-2024-03). A retry after a timeout had no key, and 27 customers were charged
  twice. Refunds and the apology notice took two weeks.

### 2.2 Error codes and whether to retry

| Class | Code | Meaning | Retry |
|---|---|---|---|
| Transient | `NETWORK_ERROR` | Connection failed | Yes |
| Transient | `GATEWAY_TIMEOUT` | PayKo got no response from the card network. **The payment may have succeeded** | Only with the same idempotency key |
| Transient | `PROVIDER_UNAVAILABLE` | Card network maintenance | Yes |
| Limit | `RATE_LIMITED` | Requests per second exceeded | After 2 seconds |
| Declined | `DECLINED` | Declined by the card issuer | **Never** |
| Declined | `INSUFFICIENT_FUNDS` | Over limit or insufficient balance | **Never** |
| Declined | `INVALID_CARD` | Bad or expired card details | **Never** |
| Declined | `FRAUD_SUSPECTED` | Flagged by fraud detection | **Never**. Escalate to CS immediately |
| Duplicate | `DUPLICATE_ORDER` | Same `orderId` already `DONE` | Never. Look up the existing payment |

- Retrying a declined code trips the card network's fraud detection. PayKo tracks the "retry after decline" ratio per merchant, sends a warning when
  it passes a threshold, and suspends payments on the third warning. We received the first warning in May 2024 (INC-2024-05).
  That time the cause was a person clicking "charge again" repeatedly in the CS tool, but automatic retries count the same way.
- `GATEWAY_TIMEOUT` may mean the payment actually succeeded. Retrying with the same idempotency key returns the successful payment's response;
  retrying with a different key creates a double charge.

### 2.3 Retry count and interval

- PayKo integration guide: for transient errors, **at most 3 attempts, at least 2 seconds apart**. Beyond that you get `RATE_LIMITED`.
- If every attempt fails, record the payment as failed; the billing batch tries once more the next day at 09:00 (batch retry is a separate system).

### 2.4 Payment status

| Status | Meaning |
|---|---|
| `DONE` | Payment complete |
| `WAITING_FOR_DEPOSIT` | Virtual account issued, waiting for deposit. **Not a failure** |
| `CANCELED` | Canceled |
| `EXPIRED` | Virtual account deposit window (3 days) passed |

- For virtual accounts the request response is `WAITING_FOR_DEPOSIT`, and `DONE` arrives later by webhook when the deposit lands. Do not treat the
  request response alone as a failure.

## 3. Request rules

- `orderId`: at most 64 characters, alphanumeric plus `_` and `-`. Must be unique within the merchant. Use the invoice number as is.
- `amount`: integer KRW. Card payments under 100 KRW return `INVALID_AMOUNT`. Zero-amount invoices do not call PayKo.
- `currency`: always `KRW`. No other currency is in the contract.
- Card payments over 5,000,000 KRW may require extra authentication from PayKo. Enterprise does not pay by card, so this is rare in practice.

## 4. Test environment

- Sandbox keys start with `pk_test_`. In the sandbox, `amount` `1004` returns `DECLINED` and `5000` returns `GATEWAY_TIMEOUT`.
- Unit tests do not call PayKo; they inject a fake `gateway` object. Integration tests run against the sandbox once a week.

## 5. Settlement reconciliation

- Match the `paymentKey` in each daily settlement file against the invoice's payment record. Unmatched rows go to the finance team.
- Store `paymentKey` **exactly** as received in the payment response. Refunds, cancellations, and reconciliation all key on it.

## 6. Webhooks

- PayKo POSTs to `/webhooks/payko` when a payment status changes: virtual account deposit (`DONE`), expiry (`EXPIRED`), cancellation (`CANCELED`).
- Verify the request signature header (`PayKo-Signature`). On verification failure respond 400 and do not process.
- If PayKo does not receive a 2xx it resends the same webhook **up to 5 times**. Webhook handling must therefore produce the same result when the same
  `paymentKey` and status arrive twice.
- There have been cases where the webhook arrived before the payment request's response (rarely, on card payments). If no payment record exists for the
  `paymentKey`, reprocess after 30 seconds.

## 7. Cancellation and refunds

- The cancel API is `/v1/payments/{paymentKey}/cancel`. Partial cancellation uses `cancelAmount`. Cancellation also uses an idempotency key.
- Cancel only after finance approval. The billing system calls cancel automatically in exactly **one** case: an upgrade payment succeeded but saving the
  plan change failed.
- Refunding a virtual account payment is a transfer to the customer's bank account and requires `refundReceiveAccount`. CS collects it from the customer.
- Card cancellations are authorization reversals; after settlement (D+2 or later) they become capture cancellations and show up as refunds on the
  customer's card statement.

## 8. Common implementation mistakes

- Retrying every exception. Declined codes are never retried.
- Generating a new idempotency key on each retry. One set of attempts for one payment shares one key.
- Treating `GATEWAY_TIMEOUT` as a definite failure. Retry with the same key or confirm through the lookup API.
- Treating `WAITING_FOR_DEPOSIT` as a failure.
- Retrying with no delay. At least 2 seconds, at most 3 attempts.
- Transforming `paymentKey` before storing it. Store it as received.
- Calling PayKo for a zero-amount invoice. Record zero-amount invoices as `DONE` with no payment.
