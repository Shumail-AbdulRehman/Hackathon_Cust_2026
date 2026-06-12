import { KIND_FIELDS, FIELD_LABELS, KIND_OPTIONS } from '../constants'

export default function MappingReview({ profiles, mappings, onMappingChange, onKindChange }) {
  if (!profiles.length) return null

  return (
    <div className="mapping-review">
      {profiles.map((profile) => {
        const kind = mappings[profile.name]?.detected_kind || profile.detected_kind || 'generic'
        const fields = KIND_FIELDS[kind] || KIND_FIELDS.generic
        return (
          <div key={profile.name} className="mapping-dataset">
            <h3>
              {profile.name} <span className="kind-badge">{kind}</span>
            </h3>
            <div className="mapping-field" style={{ marginBottom: 'var(--space-md)' }}>
              <label>Detected kind</label>
              <select
                value={kind}
                onChange={(e) => onKindChange(profile.name, e.target.value)}
              >
                {KIND_OPTIONS.map((k) => (
                  <option key={k} value={k}>{k}</option>
                ))}
              </select>
            </div>
            <div className="mapping-fields">
              {fields.map((canonical) => {
                const current = mappings[profile.name]?.fields?.[canonical] || ''
                return (
                  <div key={canonical} className="mapping-field">
                    <label htmlFor={`map-${profile.name}-${canonical}`}>
                      {FIELD_LABELS[canonical] || canonical}
                    </label>
                    <select
                      id={`map-${profile.name}-${canonical}`}
                      value={current}
                      onChange={(e) => onMappingChange(profile.name, canonical, e.target.value)}
                    >
                      <option value="">— ignore —</option>
                      {profile.columns.map((col) => (
                        <option key={col} value={col}>{col}</option>
                      ))}
                    </select>
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}
