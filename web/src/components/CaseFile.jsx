import { TIER_LABELS, TIER_ORDER } from '../constants'
import { formatPKR, tierClass } from './chartUtils'
import AssetTimelineChart from './AssetTimelineChart'
import BenfordChart from './BenfordChart'
import EgoGraph from './EgoGraph'
import ScoreComponentsChart from './ScoreComponentsChart'
import SourceMixChart from './SourceMixChart'

function safe(value) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

export default function CaseFile({ profile, graphData, onInvestigateInGraph }) {
  if (!profile) {
    return (
      <div className="case-file-empty">
        <h2>Run the pipeline to open a case file</h2>
        <p>Use <strong>Run synthetic audit</strong> or upload CSVs to begin.</p>
      </div>
    )
  }

  const agg = profile.aggregate || {}
  const lliRatio = agg.lli_ratio || 0
  const lliClass = lliRatio > 3 ? 'danger' : lliRatio > 1.5 ? 'warning' : 'positive'
  const sourceRows = profile.source_rows || []
  const reasons = profile.direct_reasons || []

  return (
    <div className="case-file">
      <header className="case-header">
        <div className="case-header-row">
          <div>
            <p className="eyebrow">Case file</p>
            <h2 className="case-name">{profile.name || profile.canonical_name || profile.entity_id}</h2>
            <div className="case-meta">
              <span>ID: {profile.entity_id}</span>
              <span>Sources: {(profile.source_record_ids || []).length}</span>
              <span>Confidence: {(profile.scoring_confidence ?? profile.risk_score ?? 0).toFixed(1)}%</span>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
            <span className={`risk-chip ${tierClass(profile.risk_tier, TIER_ORDER)}`}>
              {TIER_LABELS[profile.risk_tier] || profile.risk_tier}
            </span>
            <button
              className="btn btn-secondary"
              onClick={() => onInvestigateInGraph?.(profile.entity_id)}
            >
              Investigate in graph
            </button>
          </div>
        </div>
        <div className="score-grid">
          <div className="score-item">
            <span className="score-label">Deviation score</span>
            <span className={`score-value ${tierClass(profile.risk_tier, TIER_ORDER)}`}>
              {(profile.deviation_score ?? 0).toFixed(1)}
            </span>
          </div>
          <div className="score-item">
            <span className="score-label">Direct risk</span>
            <span className="score-value">{(profile.direct_score ?? 0).toFixed(1)}</span>
          </div>
          <div className="score-item">
            <span className="score-label">LLI ratio</span>
            <span className={`score-value ${lliClass}`}>{lliRatio.toFixed(1)}x</span>
          </div>
          <div className="score-item">
            <span className="score-label">Asset events</span>
            <span className="score-value">{Math.round(agg.asset_event_count || 0)}</span>
          </div>
          <div className="score-item">
            <span className="score-label">Vehicle value</span>
            <span className="score-value">{formatPKR(agg.estimated_vehicle_value || 0)}</span>
          </div>
          <div className="score-item">
            <span className="score-label">Property value</span>
            <span className="score-value">{formatPKR(agg.estimated_property_value || 0)}</span>
          </div>
        </div>
      </header>

      <section className="case-section">
        <div className="case-section-header">
          <h3>Direct reasons</h3>
        </div>
        <div className="case-section-body">
          <ul className="reasons-list">
            {reasons.length ? reasons.map((r, i) => <li key={i}>{r}</li>) : <li>No direct reasons recorded.</li>}
          </ul>
        </div>
      </section>

      <section className="case-section">
        <div className="case-section-header">
          <h3>Score breakdown</h3>
        </div>
        <div className="case-section-body">
          <ScoreComponentsChart profile={profile} />
        </div>
      </section>

      <section className="case-section">
        <div className="case-section-header">
          <h3>Asset timeline</h3>
        </div>
        <div className="case-section-body">
          <AssetTimelineChart profile={profile} />
        </div>
      </section>

      <section className="case-section">
        <div className="case-section-header">
          <h3>Evidence signals</h3>
        </div>
        <div className="case-section-body">
          <div className="overview-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
            <div>
              <p className="eyebrow">Source mix</p>
              <SourceMixChart profile={profile} />
            </div>
            <div>
              <p className="eyebrow">Benford first digits</p>
              <BenfordChart profile={profile} />
            </div>
            <div>
              <p className="eyebrow">Geography</p>
              <GeoChips sourceRows={sourceRows} />
            </div>
          </div>
        </div>
      </section>

      <section className="case-section">
        <div className="case-section-header">
          <h3>Ego network</h3>
        </div>
        <div className="case-section-body">
          <EgoGraph profile={profile} graphData={graphData} />
        </div>
      </section>

      <section className="case-section">
        <div className="case-section-header">
          <h3>Source rows</h3>
        </div>
        <div className="case-section-body">
          <SourceRows rows={sourceRows} />
        </div>
      </section>
    </div>
  )
}

function GeoChips({ sourceRows }) {
  const provinces = new Set()
  const districts = new Set()
  ;(sourceRows || []).forEach((r) => {
    const raw = r.raw || {}
    if (raw.nic_province) provinces.add(raw.nic_province)
    if (raw.nic_district) districts.add(raw.nic_district)
  })

  if (!provinces.size && !districts.size) {
    return <p className="empty-state">No geocoded CNIC data.</p>
  }

  return (
    <div className="geo-chips">
      {Array.from(provinces).map((p) => (
        <span key={p} className="geo-chip">
          {p}
        </span>
      ))}
      {Array.from(districts).map((d) => (
        <span key={d} className="geo-chip">
          {d}
        </span>
      ))}
    </div>
  )
}

function SourceRows({ rows }) {
  if (!rows?.length) {
    return <p className="empty-state">No source rows.</p>
  }

  return (
    <div className="source-rows">
      {rows.map((row, idx) => {
        const raw = row.raw || {}
        return (
          <article key={idx} className="source-row">
            <header>
              <span>{row.dataset}</span>
              <span>{row.record_type}</span>
              <span>{row.row_id}</span>
            </header>
            <dl>
              {Object.entries(raw)
                .filter(([k]) => !k.startsWith('_'))
                .map(([k, v]) => (
                  <div key={k}>
                    <dt>{k}</dt>
                    <dd>{safe(v)}</dd>
                  </div>
                ))}
            </dl>
          </article>
        )
      })}
    </div>
  )
}
