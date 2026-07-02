import { EDGE_TYPES, NODE_TYPES } from '../constants'

export default function GraphControls({
  visibleNodeTypes,
  visibleEdgeTypes,
  onNodeTypeToggle,
  onEdgeTypeToggle,
  onReset,
  onFit,
}) {
  const nodeSet = new Set(visibleNodeTypes || NODE_TYPES.map((t) => t.key))
  const edgeSet = new Set(visibleEdgeTypes || EDGE_TYPES.map((t) => t.key))

  return (
    <div className="panel graph-controls">
      <div className="control-actions">
        <button className="btn btn-secondary" onClick={onReset}>
          Reset selection
        </button>
        <button className="btn btn-secondary" onClick={onFit}>
          Fit view
        </button>
      </div>

      <div className="control-group">
        <h3>Node types</h3>
        <div className="legend">
          {NODE_TYPES.map((t) => (
            <label key={t.key} className="legend-item">
              <input
                type="checkbox"
                value={t.key}
                checked={nodeSet.has(t.key)}
                onChange={(e) => onNodeTypeToggle?.(t.key, e.target.checked)}
              />
              <span className={`legend-swatch ${t.shape}`} style={{ background: t.color }} />
              <span>{t.label}</span>
            </label>
          ))}
        </div>
      </div>

      <div className="control-group">
        <h3>Edge types</h3>
        <div className="legend">
          {EDGE_TYPES.map((t) => (
            <label key={t.key} className="legend-item">
              <input
                type="checkbox"
                value={t.key}
                checked={edgeSet.has(t.key)}
                onChange={(e) => onEdgeTypeToggle?.(t.key, e.target.checked)}
              />
              <svg width="20" height="10" style={{ flexShrink: 0 }}>
                <line x1="0" y1="5" x2="18" y2="5" stroke={t.color} strokeWidth="2" strokeDasharray={t.dash} />
              </svg>
              <span>{t.label}</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  )
}
