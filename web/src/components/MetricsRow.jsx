export default function MetricsRow({ metrics }) {
  return (
    <div className="metrics-row">
      {metrics.map((metric) => (
        <div
          key={metric.label}
          className={`metric-card${metric.loading ? ' loading' : ''}`}
        >
          <span className="metric-label">{metric.label}</span>
          <span className="metric-value">{metric.value}</span>
        </div>
      ))}
    </div>
  )
}
