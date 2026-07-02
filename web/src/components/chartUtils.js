export function formatNumber(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return '—'
  if (Math.abs(num) >= 1_000_000) return `₨ ${(num / 1_000_000).toFixed(2)}M`
  if (Math.abs(num) >= 1_000) return `₨ ${(num / 1_000).toFixed(1)}K`
  return `₨ ${num.toLocaleString()}`
}

export function formatPKR(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return '—'
  return `PKR ${num.toLocaleString()}`
}

export function getChartSize(container) {
  const width = container.clientWidth || 400
  return { width, height: container.clientHeight || 240 }
}

export function tierClass(tier, order) {
  return order.includes(tier) ? tier : 'low'
}
