import { FIELD_LABELS } from '../constants'

function formatMapped(mapping) {
  return Object.entries(mapping || {})
    .map(([key, value]) => `${FIELD_LABELS[key] || key}: ${value}`)
    .join(', ')
}

export default function DatasetProfiles({
  profiles,
  emptyMessage = 'Run an audit or upload files to see dataset profiles.',
}) {
  return (
    <div className="panel dataset-profiles">
      {!profiles?.length ? (
        <p className="empty-state">{emptyMessage}</p>
      ) : (
        profiles.map((profile) => (
          <div key={profile.name} className="dataset-profile">
            <h3>{profile.name}</h3>
            <span className="hint">
              {profile.detected_kind} · {profile.row_count ?? '?'} rows · {profile.columns?.length ?? 0} columns
            </span>
            <p className="hint">{formatMapped(profile.mapping) || 'Auto-detected mapping'}</p>
          </div>
        ))
      )}
    </div>
  )
}
