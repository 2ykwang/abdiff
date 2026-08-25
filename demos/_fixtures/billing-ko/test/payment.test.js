import { test } from 'node:test'
import assert from 'node:assert/strict'
import { charge, GatewayError } from '../src/payment.js'

function fakeGateway(handler) {
  const calls = []
  return {
    calls,
    async request(req) {
      calls.push(req)
      return handler(req, calls.length)
    },
  }
}

test('charge sends KRW amount and returns status', async () => {
  const gw = fakeGateway(() => ({ status: 'DONE', paymentKey: 'pk_1' }))
  const res = await charge(gw, { orderId: 'ord_1', amount: 108900 })
  assert.equal(res.status, 'DONE')
  assert.equal(gw.calls[0].body.currency, 'KRW')
})

test('charge rejects non-integer amount', async () => {
  const gw = fakeGateway(() => ({ status: 'DONE' }))
  await assert.rejects(charge(gw, { orderId: 'ord_1', amount: 100.5 }), RangeError)
})

test('charge propagates gateway errors', async () => {
  const gw = fakeGateway(() => {
    throw new GatewayError('DECLINED', 'card declined')
  })
  await assert.rejects(charge(gw, { orderId: 'ord_1', amount: 1000 }), (e) => e.code === 'DECLINED')
})
