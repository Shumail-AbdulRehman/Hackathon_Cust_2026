import { useState, useMemo } from 'react'
import { TIER_LABELS, DISPLAY_TIER_ORDER } from '../constants'

export default function ProfileQueue({ flagged, selectedId, onSelect }) {
  const [search, setSearch] = useState('')
  const [activeTier, setActiveTier] = useState('all')

  const filtered = useMemo(() => {
    const term = search.toLowerCase()
    return flagged.filter((p) => {
      const matchesSearch =
        !term ||
        (p.name || '').toLowerCase().includes(term) ||
        (p.entity_id || '').toLowerCase().includes(term)
      const matchesTier = activeTier === 'all' || p.risk_tier === activeTier
      return matchesSearch && matchesTier
    })
  }, [flagged, search, activeTier])

  return (
    <aside className="panel profile-queue">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Audit queue</p>
          <h2>Flagged profiles</h2>
        </div>
        <span className="count">{filtered.length}</span>
      </div>
      <div className="queue-controls">
        <input
          className="input"
          type="search"
          placeholder="Search entity or ID"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="filter-chips">
          <button className={`chip ${activeTier === 'all' ? 'active' : ''}`} onClick={() => setActiveTier('all')}>
            All
          </button>
          {DISPLAY_TIER_ORDER.map((tier) => (
            <button
              key={tier}
              className={`chip ${activeTier === tier ? 'active' : ''}`}
              onClick={() => setActiveTier(tier)}
            >
              {TIER_LABELS[tier]}
            </button>
          ))}
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Entity</th>
              <th>Tier</th>
              <th className="numeric">Score</th>
              <th className="numeric">LLI</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((p) => (
              <tr
                key={p.entity_id}
                className={p.entity_id === selectedId ? 'selected' : ''}
                onClick={() => onSelect(p.entity_id)}
              >
                <td>
                  <div style={{ fontWeight: 600 }}>{p.name || p.entity_id}</div>
                  <div style={{ color: 'var(--ink-muted)', fontSize: '0.75rem' }}>{p.entity_id}</div>
                </td>
                <td>
                  <span className={`risk-chip ${p.risk_tier}`}>{TIER_LABELS[p.risk_tier] || p.risk_tier}</span>
                </td>
                <td className="numeric">{(p.deviation_score ?? 0).toFixed(1)}</td>
                <td className="numeric">{(p.aggregate?.lli_ratio || 0).toFixed(1)}x</td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={4} className="empty-state" style={{ padding: 'var(--space-lg)' }}>
                  No flagged profiles match your filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </aside>
  )
}
