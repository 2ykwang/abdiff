// Dates are handled only as 'YYYY-MM-DD' strings. Time of day and time zones are outside this module.

export function parseDate(s) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s)
  if (!m) throw new TypeError(`invalid date: ${s}`)
  return new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]))
}

export function formatDate(d) {
  return d.toISOString().slice(0, 10)
}

export function addDays(s, n) {
  const d = parseDate(s)
  d.setUTCDate(d.getUTCDate() + n)
  return formatDate(d)
}

export function addMonths(s, n) {
  const d = parseDate(s)
  const day = d.getUTCDate()
  d.setUTCDate(1)
  d.setUTCMonth(d.getUTCMonth() + n)
  const last = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0)).getUTCDate()
  d.setUTCDate(Math.min(day, last))
  return formatDate(d)
}

export function daysBetween(a, b) {
  return Math.round((parseDate(b) - parseDate(a)) / 86400000)
}
