import ScoreComponentsChart from './ScoreComponentsChart'
import AssetTimelineChart from './AssetTimelineChart'
import SourceMixChart from './SourceMixChart'
import BenfordChart from './BenfordChart'
import EgoGraph from './EgoGraph'

function formatNumber(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return '—'
  if (Math.abs(num) >= 1_000_000) return `₨ ${(num / 1_000_000).toFixed(2)}M`
  if (Math.abs(num) >= 1_000) return `₨ ${(num / 1_000).toFixed(1)}K`
  return `₨ ${num.toLocaleString()}`
}

export default function CaseFile({ profile, graph, onInvestigateInGraph, formatPKR, tierClass, safe }) {
  if (!profile) {
    return (
      <section className="case-file-empty">
        <h2>Run the pipeline to open a case file</h2>
        <p>Use <strong>Run synthetic audit</strong> or upload CSVs to begin.</p>
      </section>
    )
  }

  const agg = profile.aggregate || {}
  const lliRatio = agg.lli_ratio || 0
  const lliClass = lliRatio > 3 ? 'danger' : lliRatio > 1.5 ? 'warning' : 'positive'

  return (
    <section className="case-file">
      <header className="case-header">
        <div className="case-header-row">
          <div>
            <p className="eyebrow">Case file</p>
            <h2 className="case-name">{profile.name || profile.entity_id}</h2>
            <div className="case-meta">
              <span>ID: {profile.entity_id}</span>
              <span>Sources: {(profile.source_record_ids || []).length}</span>
              <span>Confidence: {(profile.scoring_confidence ?? 0).toFixed(1)}%</span>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
            <span className={`risk-chip ${tierClass(profile.risk_tier)}`}>
              {profile.risk_tier}
            </span>
            <button
              className="btn btn-secondary"
              onClick={() => onInvestigateInGraph(profile.entity_id)}
            >
              Investigate in graph
            </button>
          </div>
        </div>
        <div className="score-grid">
          <div className="score-item">
            <span className="score-label">Deviation score</span>
            <span className={`score-value ${tierClass(profile.risk_tier)}`}>
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
        <div className="case-section-header"><h3>Direct reasons</h3></div>
        <div className="case-section-body">
          <ul className="reasons-list">
            {(profile.direct_reasons || []).length > 0 ? (
              profile.direct_reasons.map((reason, idx) => <li key={idx}>{reason}</li>)
            ) : (
              <li>No direct reasons recorded.</li>
            )}
          </ul>
        </div>
      </section>

      <section className="case-section">
        <div className="case-section-header"><h3>Score breakdown</h3></div>
        <div className="case-section-body chart-container">
          <ScoreComponentsChart components={profile.score_components} />
        </div>
      </section>

      <section className="case-section">
        <div className="case-section-header"><h3>Asset timeline</h3></div>
        <div className="case-section-body chart-container">
          <AssetTimelineChart rows={profile.source_rows} formatNumber={formatNumber} />
        </div>
      </section>

      <section className="case-section">
        <div className="case-section-header"><h3>Evidence signals</h3></div>
        <div className="case-section-body">
          <div className="overview-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
            <div>
              <p className="eyebrow">Source mix</p>
              <div className="chart-container small">
                <SourceMixChart rows={profile.source_rows} />
              </div>
            </div>
            <div>
              <p className="eyebrow">Benford first digits</p>
              <div className="chart-container small">
                <BenfordChart rows={profile.source_rows} />
              </div>
            </div>
            <div>
              <p className="eyebrow">Geography</p>
              <div className="geo-chips">
                {(() => {
                  const provinces = new Set()
                  const districts = new Set()
                  ;(profile.source_rows || []).forEach((r) => {
                    const raw = r.raw || {}
                    if (raw.nic_province) provinces.add(raw.nic_province)
                    if (raw.nic_district) districts.add(raw.nic_district)
                  })
                  const chips = [
                    ...Array.from(provinces).map((p) => <span key={p} className="geo-chip">{p}</span>),
                    ...Array.from(districts).map((d) => <span key={d} className="geo-chip">{d}</span>),
                  ]
                  return chips.length > 0 ? chips : <p className="empty-state">No geocoded CNIC data.</p>
                })()}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="case-section">
        <div className="case-section-header"><h3>Ego network</h3></div>
        <div className="case-section-body chart-container">
          <EgoGraph graph={graph} entityId={profile.entity_id} />
        </div>
      </section>

      <section className="case-section">
        <div className="case-section-header"><h3>Source rows</h3></div>
        <div className="case-section-body">
          <div className="source-rows">
            {(profile.source_rows || []).map((row) => {
              const raw = row.raw || {}
              const fields = Object.entries(raw).filter(([k]) => !k.startsWith('_'))
              return (
                <article key={`${row.dataset}-${row.row_id}`} className="source-row">
                  <header>
                    <span>{row.dataset}</span>
                    <span>{row.record_type}</span>
                    <span>{row.row_id}</span>
                  </header>
                  <dl>
                    {fields.map(([k, v]) => (
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
        </div>
      </section>
    </section>
  )
}
