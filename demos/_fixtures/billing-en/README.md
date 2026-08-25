# workhub-billing

Subscription billing core for the Workhub SaaS. Handles plans, billing cycles, proration, invoices, coupons, and PG (payment gateway) calls.

## Run

```
npm test
```

## Layout

| File | Role |
|---|---|
| `src/plans.js` | Plan catalog and lookup |
| `src/dates.js` | `YYYY-MM-DD` calendar date arithmetic |
| `src/proration.js` | Billing cycle and proration math |
| `src/invoice.js` | Invoice creation, numbering, VAT |
| `src/coupons.js` | Coupon application |
| `src/payment.js` | PG (PayKo) payment request |
| `src/format.js` | Amount formatting |
