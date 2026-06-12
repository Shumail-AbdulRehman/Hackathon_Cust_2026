import { FIELD_LABELS } from '../constants'

export default function DatasetProfiles({ profiles }) {
  if (!profiles.length) {
    return (
      <div className="dataset-profiles">
        <p className="empty-state">Run an audit or upload files to see dataset profiles.</p>
      </div>
    )
  }

  return (
    <div className="dataset-profiles">
      {profiles.map((profile) => {
        const cols = profile.columns?.length ?? 0
        const mapped = Object.entries(profile.mapping || {})
          .map(([k, v]) => `${FIELD_LABELS[k] || k}: ${v}`)
          .join(', ')
        return (
          <div key={profile.name} className="dataset-profile">
            <h3>{profile.name}</h3>
            <span className="hint">
              {profile.detected_kind} · {profile.row_count ?? '?'} rows · {cols} columns
            </span>
            <p className="hint">{mapped || 'Auto-detected mapping'}</p>
          </div>
        )
      })}
    </div>
  )
}
