import { test } from 'node:test'
import assert from 'node:assert/strict'
import { applyCoupon } from '../src/coupons.js'

test('percent coupon', () => {
  assert.equal(applyCoupon(99000, { code: 'X', type: 'percent', value: 20 }), 79200)
})

test('fixed coupon never goes below zero', () => {
  assert.equal(applyCoupon(10000, { code: 'X', type: 'fixed', value: 30000 }), 0)
})
