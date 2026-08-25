// coupon: { code, type: 'percent' | 'fixed', value }
export function applyCoupon(subtotal, coupon) {
  if (coupon.type === 'percent') {
    return subtotal - Math.floor((subtotal * coupon.value) / 100)
  }
  if (coupon.type === 'fixed') {
    return Math.max(0, subtotal - coupon.value)
  }
  throw new Error(`unknown coupon type: ${coupon.type}`)
}
