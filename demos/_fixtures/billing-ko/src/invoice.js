export const VAT_RATE = 0.1

let seq = 0

// 청구서 번호: INV-YYYYMM-NNNNN
export function nextInvoiceNumber(issuedOn) {
  seq += 1
  return `INV-${issuedOn.slice(0, 7).replace('-', '')}-${String(seq).padStart(5, '0')}`
}

export function resetInvoiceSequence() {
  seq = 0
}

export function createInvoice({ accountId, issuedOn, lines }) {
  if (!lines.length) throw new Error('invoice needs at least one line')
  const subtotal = lines.reduce((sum, l) => sum + l.amount, 0)
  const vat = Math.floor(subtotal * VAT_RATE)
  return {
    number: nextInvoiceNumber(issuedOn),
    accountId,
    issuedOn,
    lines,
    subtotal,
    vat,
    total: subtotal + vat,
  }
}
