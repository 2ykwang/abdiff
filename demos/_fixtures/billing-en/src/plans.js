export const PLANS = [
  { id: 'starter', name: 'Starter', monthlyPrice: 29000, seatLimit: 5, legacy: false },
  { id: 'team', name: 'Team', monthlyPrice: 99000, seatLimit: 20, legacy: false },
  { id: 'business', name: 'Business', monthlyPrice: 290000, seatLimit: 100, legacy: false },
  { id: 'L-startup-2019', name: 'Startup (2019)', monthlyPrice: 49000, seatLimit: 10, legacy: true },
  { id: 'L-growth-2019', name: 'Growth (2019)', monthlyPrice: 149000, seatLimit: 30, legacy: true },
]

export function findPlan(id) {
  const plan = PLANS.find((p) => p.id === id)
  if (!plan) throw new Error(`unknown plan: ${id}`)
  return plan
}
