import { test } from 'node:test'
import assert from 'node:assert/strict'
import { PLANS, findPlan } from '../src/plans.js'

test('findPlan returns the plan by id', () => {
  assert.equal(findPlan('team').monthlyPrice, 99000)
})

test('findPlan throws on unknown id', () => {
  assert.throws(() => findPlan('nope'), /unknown plan/)
})

test('plan ids are unique', () => {
  assert.equal(new Set(PLANS.map((p) => p.id)).size, PLANS.length)
})
