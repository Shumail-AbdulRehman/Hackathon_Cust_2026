// web/src/components/MetricsRow.jsx
const METRIC_LABELS = {
  records: { label: 'Records ingested', caption: 'Canonical rows after deduplication' },
  entities: { label: 'Entities resolved', caption: 'Unique people or organizations' },
  flagged: { label: 'Flagged for review', caption: 'Profiles exceeding risk thresholds' },
  ml: { label: 'ML scoring', caption: 'Model used for this run' },
}

export default function MetricsRow({ metrics, loading }) {
  const items = metrics || {}

  return (
    <div className={`metrics-row${loading ? ' loading' : ''}`}>
      {Object.entries(items).map(([key, value]) => {
        const meta = METRIC_LABELS[key] || { label: key, caption: '' }
        return (
          <div key={key} className="metric-card">
            <span className="metric-label">{meta.label}</span>
            <span className="metric-value">{value ?? '—'}</span>
            {meta.caption && <span className="metric-caption">{meta.caption}</span>}
          </div>
        )
      })}
    </div>
  )
}
