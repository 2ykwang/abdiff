import { test, beforeEach } from 'node:test'
import assert from 'node:assert/strict'
import { createInvoice, resetInvoiceSequence } from '../src/invoice.js'

beforeEach(() => resetInvoiceSequence())

test('createInvoice sums lines and adds VAT', () => {
  const inv = createInvoice({
    accountId: 'acc_1',
    issuedOn: '2026-03-10',
    lines: [{ description: 'Team plan', amount: 99000 }],
  })
  assert.equal(inv.number, 'INV-202603-00001')
  assert.equal(inv.subtotal, 99000)
  assert.equal(inv.vat, 9900)
  assert.equal(inv.total, 108900)
})

test('createInvoice truncates VAT below 1 KRW', () => {
  const inv = createInvoice({ accountId: 'acc_1', issuedOn: '2026-03-10', lines: [{ description: 'x', amount: 12345 }] })
  assert.equal(inv.vat, 1234)
})
