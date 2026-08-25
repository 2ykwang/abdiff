import { test } from 'node:test'
import assert from 'node:assert/strict'
import { cycleBounds, prorate } from '../src/proration.js'

test('cycleBounds: anchor before the date', () => {
  assert.deepEqual(cycleBounds(10, '2026-03-15'), { start: '2026-03-10', end: '2026-04-10' })
})

test('cycleBounds: anchor after the date goes to previous month', () => {
  assert.deepEqual(cycleBounds(20, '2026-03-05'), { start: '2026-02-20', end: '2026-03-20' })
})

test('cycleBounds rejects anchor outside 1..28', () => {
  assert.throws(() => cycleBounds(31, '2026-03-05'), RangeError)
})

test('prorate: remaining days over cycle days, truncated', () => {
  const cycle = { start: '2026-03-10', end: '2026-04-10' } // 31 days
  assert.equal(prorate(99000, cycle, '2026-03-25'), Math.floor((99000 * 16) / 31))
})
