export default function MetricsRow({ metrics, loading }) {
  const items = [
    { label: 'Records', value: metrics?.records ?? '—' },
    { label: 'Entities', value: metrics?.entities ?? '—' },
    { label: 'Flagged', value: metrics?.flagged ?? '—' },
    { label: 'Avg confidence', value: metrics?.confidence ?? '—' },
    { label: 'Top tier', value: metrics?.topTier ?? '—' },
  ]

  return (
    <div className="metrics-row">
      {items.map((item) => (
        <div key={item.label} className={`metric-card ${loading ? 'loading' : ''}`}>
          <span className="metric-label">{item.label}</span>
          <strong className="metric-value">{item.value}</strong>
        </div>
      ))}
    </div>
  )
}
