import { addMonths, daysBetween, parseDate, formatDate } from './dates.js'

// Billing cycle. anchorDay (1..28) is the day each monthly cycle starts.
// Returns the [start, end) of the cycle containing `at`. `end` is the next cycle's start date.
export function cycleBounds(anchorDay, at) {
  if (!Number.isInteger(anchorDay) || anchorDay < 1 || anchorDay > 28) {
    throw new RangeError(`anchorDay must be 1..28: ${anchorDay}`)
  }
  const d = parseDate(at)
  let start = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), anchorDay))
  if (start > d) start = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() - 1, anchorDay))
  const startStr = formatDate(start)
  return { start: startStr, end: addMonths(startStr, 1) }
}

// Prorates `amount` by the days remaining from `at` to the end of the cycle. The day of `at` counts.
export function prorate(amount, cycle, at) {
  const total = daysBetween(cycle.start, cycle.end)
  const remaining = daysBetween(at, cycle.end)
  if (remaining < 0 || remaining > total) throw new RangeError(`${at} is outside the cycle`)
  return Math.floor((amount * remaining) / total)
}
