import { useEffect, useState } from 'react'
import { getProfile, getProfiles } from '../api'

export default function NodeSummarySidebar({ entityId, onChangeEntity }) {
  const [profile, setProfile] = useState(null)
  const [search, setSearch] = useState('')
  const [suggestions, setSuggestions] = useState([])

  useEffect(() => {
    if (!entityId) return
    getProfile(entityId).then(setProfile).catch(() => setProfile(null))
  }, [entityId])

  useEffect(() => {
    const timer = setTimeout(() => {
      if (!search.trim()) {
        setSuggestions([])
        return
      }
      getProfiles(search).then(setSuggestions).catch(() => setSuggestions([]))
    }, 200)
    return () => clearTimeout(timer)
  }, [search])

  if (!profile) {
    return (
      <aside className="node-summary-sidebar panel">
        <div className="panel-head">
          <div>
            <p className="eyebrow">Node context</p>
            <h2>No node selected</h2>
          </div>
        </div>
        <div className="panel-body">
          <input
            className="input"
            type="search"
            placeholder="Search entity ID or name"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {suggestions.length > 0 && (
            <ul className="entity-suggestions">
              {suggestions.map((s) => (
                <li key={s.entity_id} onClick={() => onChangeEntity(s.entity_id)}>
                  {s.name || s.entity_id}
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>
    )
  }

  const features = profile.features || {}
  const topSignals = Object.entries(features)
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
    .slice(0, 5)

  return (
    <aside className="node-summary-sidebar panel">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Node context</p>
          <h2>{profile.canonical_name || profile.entity_id}</h2>
        </div>
        <span className={`risk-chip ${profile.risk_tier || 'green'}`}>{profile.risk_tier}</span>
      </div>
      <div className="panel-body">
        <input
          className="input"
          type="search"
          placeholder="Switch entity..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        {suggestions.length > 0 && (
          <ul className="entity-suggestions">
            {suggestions.map((s) => (
              <li key={s.entity_id} onClick={() => onChangeEntity(s.entity_id)}>
                {s.name || s.entity_id}
              </li>
            ))}
          </ul>
        )}

        <div className="score-grid" style={{ marginTop: '16px' }}>
          <div className="score-item">
            <span className="score-label">Risk score</span>
            <span className="score-value">{(profile.risk_score || 0).toFixed(1)}</span>
          </div>
          <div className="score-item">
            <span className="score-label">Proxy label</span>
            <span className="score-value">{(profile.proxy_label || 0).toFixed(1)}</span>
          </div>
          <div className="score-item">
            <span className="score-label">Records</span>
            <span className="score-value">{profile.record_count || 0}</span>
          </div>
        </div>

        <div className="signal-list">
          <p className="eyebrow">Top XGBoost signals</p>
          {topSignals.map(([k, v]) => (
            <div key={k} className="signal-row">
              <span>{k.replace(/_/g, ' ')}</span>
              <span className="signal-value">{Number(v).toFixed(3)}</span>
            </div>
          ))}
        </div>
      </div>
    </aside>
  )
}
