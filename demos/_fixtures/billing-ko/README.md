# workhub-billing

Workhub SaaS의 구독 청구 코어 모듈. 플랜, 청구 주기, 일할 계산, 청구서, 쿠폰, PG 결제 호출을 담당한다.

## 실행

```
npm test
```

## 구조

| 파일 | 역할 |
|---|---|
| `src/plans.js` | 플랜 목록과 조회 |
| `src/dates.js` | `YYYY-MM-DD` 달력 날짜 연산 |
| `src/proration.js` | 청구 주기 계산과 일할 계산 |
| `src/invoice.js` | 청구서 생성, 번호 채번, 부가세 |
| `src/coupons.js` | 쿠폰 적용 |
| `src/payment.js` | PG(PayKo) 결제 요청 |
| `src/format.js` | 금액 표시 |
