import { useMemo } from 'react'
import { FIELD_LABELS, KIND_FIELDS } from '../constants'

function buildInitialMappings(profiles, existing = {}) {
  const mappings = {}
  profiles.forEach((profile) => {
    const mapping = existing[profile.name] || {}
    mappings[profile.name] = {
      detected_kind: mapping.detected_kind || profile.detected_kind || 'generic',
      fields: { ...(mapping.fields || {}), ...(profile.mapping || {}) },
    }
  })
  return mappings
}

export default function MappingReview({ profiles, mappings: controlledMappings, onChange }) {
  const mappings = useMemo(
    () => controlledMappings || buildInitialMappings(profiles || []),
    [controlledMappings, profiles],
  )

  if (!profiles?.length) return null

  const handleChange = (dataset, field, source) => {
    const next = {
      ...mappings,
      [dataset]: {
        ...mappings[dataset],
        fields: {
          ...mappings[dataset]?.fields,
          [field]: source,
        },
      },
    }
    onChange?.(dataset, field, source, next)
  }

  return (
    <div className="panel mapping-panel">
      <div className="mapping-review">
        {profiles.map((profile) => {
          const kind = mappings[profile.name]?.detected_kind || profile.detected_kind || 'generic'
          const fields = KIND_FIELDS[kind] || KIND_FIELDS.generic
          return (
            <div key={profile.name} className="mapping-dataset">
              <h3>
                {profile.name} <span className="kind-badge">{kind}</span>
              </h3>
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
                        onChange={(e) => handleChange(profile.name, canonical, e.target.value)}
                      >
                        <option value="">— ignore —</option>
                        {(profile.columns || []).map((col) => (
                          <option key={col} value={col}>
                            {col}
                          </option>
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
    </div>
  )
}
