import { useMemo, useState } from 'react'
import { TIER_LABELS, TIER_ORDER } from '../constants'
import { tierClass } from './chartUtils'

export default function ProfileQueue({ profiles, selectedId, onSelect }) {
  const [search, setSearch] = useState('')
  const [activeTier, setActiveTier] = useState('all')

  const filtered = useMemo(() => {
    const q = search.toLowerCase()
    return (profiles || []).filter((p) => {
      const matchesSearch =
        !q || (p.name || '').toLowerCase().includes(q) || (p.entity_id || '').toLowerCase().includes(q)
      const matchesTier = activeTier === 'all' || p.risk_tier === activeTier
      return matchesSearch && matchesTier
    })
  }, [profiles, search, activeTier])

  return (
    <div className="panel profile-queue">
      <div className="queue-controls">
        <input
          className="input"
          type="search"
          placeholder="Search profiles..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="filter-chips">
          <button
            className={`chip ${activeTier === 'all' ? 'active' : ''}`}
            onClick={() => setActiveTier('all')}
          >
            All
          </button>
          {TIER_ORDER.map((tier) => (
            <button
              key={tier}
              className={`chip ${activeTier === tier ? 'active' : ''}`}
              onClick={() => setActiveTier(tier)}
            >
              {TIER_LABELS[tier]}
            </button>
          ))}
        </div>
        <p className="eyebrow">Showing {filtered.length} flagged</p>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Entity</th>
              <th>Risk</th>
              <th className="numeric">Score</th>
              <th className="numeric">LLI</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((p) => (
              <tr
                key={p.entity_id}
                className={p.entity_id === selectedId ? 'selected' : ''}
                onClick={() => onSelect?.(p.entity_id)}
              >
                <td>
                  <div className="queue-name">{p.name || p.entity_id}</div>
                  <div className="queue-id">{p.entity_id}</div>
                </td>
                <td>
                  <span className={`risk-chip ${tierClass(p.risk_tier, TIER_ORDER)}`}>
                    {TIER_LABELS[p.risk_tier] || p.risk_tier}
                  </span>
                </td>
                <td className="numeric">{(p.deviation_score ?? 0).toFixed(1)}</td>
                <td className="numeric">{(p.aggregate?.lli_ratio || 0).toFixed(1)}x</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!filtered.length && <p className="empty-state" style={{ padding: '24px' }}>No matching profiles.</p>}
      </div>
    </div>
  )
}
