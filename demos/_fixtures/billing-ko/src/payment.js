export class GatewayError extends Error {
  constructor(code, message) {
    super(message ?? code)
    this.name = 'GatewayError'
    this.code = code
  }
}

// PayKo 결제 요청.
// gateway.request({ path, headers, body })는 { status, paymentKey }를 돌려주거나 GatewayError를 던진다.
export async function charge(gateway, { orderId, amount, method = 'card' }) {
  if (!Number.isInteger(amount) || amount <= 0) {
    throw new RangeError('amount must be a positive integer (KRW)')
  }
  const res = await gateway.request({
    path: '/v1/payments',
    headers: {},
    body: { orderId, amount, currency: 'KRW', method },
  })
  return { status: res.status, paymentKey: res.paymentKey }
}
