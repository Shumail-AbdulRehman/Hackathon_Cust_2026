function safe(value) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function getNodeId(e) {
  return typeof e === 'object' ? e.id : e
}

export default function GraphDetail({ node, graphData, profiles, onOpenCaseFile }) {
  if (!node) {
    return (
      <div className="panel graph-detail">
        <div className="case-file-empty">
          <h2>Select a node</h2>
          <p>Click any node in the graph to inspect its evidence and relationships.</p>
        </div>
      </div>
    )
  }

  const graph = graphData || { nodes: [], edges: [] }

  const edges = graph.edges.filter((e) => {
    const s = getNodeId(e.source)
    const t = getNodeId(e.target)
    return s === node.id || t === node.id
  })

  const neighborIds = new Set()
  edges.forEach((e) => {
    const s = getNodeId(e.source)
    const t = getNodeId(e.target)
    neighborIds.add(s === node.id ? t : s)
  })

  const neighbors = graph.nodes.filter((n) => neighborIds.has(n.id))
  const profile = (profiles || []).find((p) => p.entity_id === node.id)

  return (
    <div className="panel graph-detail">
      <div className="panel-head">
        <div>
          <p className="eyebrow">{node.type || 'Node'}</p>
          <h2>{node.label || node.id}</h2>
        </div>
      </div>
      <div style={{ padding: '16px 24px', display: 'grid', gap: '16px' }}>
        {profile && (
          <div className="score-grid" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
            <div className="score-item">
              <span className="score-label">Score</span>
              <span className="score-value">{(profile.deviation_score || 0).toFixed(1)}</span>
            </div>
            <div className="score-item">
              <span className="score-label">LLI</span>
              <span className="score-value">{(profile.aggregate?.lli_ratio || 0).toFixed(1)}x</span>
            </div>
          </div>
        )}
        <div>
          <p className="eyebrow">Properties</p>
          <dl className="source-row">
            {Object.entries(node.meta || {}).map(([k, v]) => (
              <div key={k}>
                <dt>{safe(k)}</dt>
                <dd>{safe(v)}</dd>
              </div>
            ))}
          </dl>
        </div>
        <div>
          <p className="eyebrow">Connections ({neighbors.length})</p>
          <ul className="reasons-list">
            {neighbors.map((n) => (
              <li key={n.id}>
                {n.label || n.id}{' '}
                <span style={{ color: 'var(--ink-muted)' }}>({n.type || 'unknown'})</span>
              </li>
            ))}
          </ul>
        </div>
        {profile && (
          <button className="btn btn-secondary" onClick={() => onOpenCaseFile?.(node.id)}>
            Open case file
          </button>
        )}
      </div>
    </div>
  )
}
