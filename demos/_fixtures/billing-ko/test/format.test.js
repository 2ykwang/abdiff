import { test } from 'node:test'
import assert from 'node:assert/strict'
import { formatKRW } from '../src/format.js'

test('formatKRW adds thousands separators', () => {
  assert.equal(formatKRW(108900), '₩108,900')
})
