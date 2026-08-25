import { addMonths, daysBetween, parseDate, formatDate } from './dates.js'

// 청구 주기. anchorDay(1~28)가 매달 주기 시작일이다.
// at이 속한 주기의 [start, end)를 돌려준다. end는 다음 주기 시작일이다.
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

// 주기 안에서 at부터 주기 끝까지 남은 일수 비율로 amount를 나눈다. at 당일을 포함한다.
export function prorate(amount, cycle, at) {
  const total = daysBetween(cycle.start, cycle.end)
  const remaining = daysBetween(at, cycle.end)
  if (remaining < 0 || remaining > total) throw new RangeError(`${at} is outside the cycle`)
  return Math.floor((amount * remaining) / total)
}
