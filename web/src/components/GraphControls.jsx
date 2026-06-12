import { NODE_TYPES, EDGE_TYPES } from '../constants'

export default function GraphControls({
  visibleNodeTypes,
  visibleEdgeTypes,
  onNodeTypesChange,
  onEdgeTypesChange,
  onReset,
}) {
  const toggleNodeType = (key) => {
    const next = new Set(visibleNodeTypes)
    if (next.has(key)) next.delete(key)
    else next.add(key)
    onNodeTypesChange(next)
  }

  const toggleEdgeType = (key) => {
    const next = new Set(visibleEdgeTypes)
    if (next.has(key)) next.delete(key)
    else next.add(key)
    onEdgeTypesChange(next)
  }

  return (
    <aside className="panel graph-controls">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Network</p>
          <h2>Graph filters</h2>
        </div>
      </div>
      <div className="control-group">
        <h3>Node types</h3>
        <div className="legend">
          {NODE_TYPES.map((type) => (
            <label key={type.key} className="legend-item">
              <input
                type="checkbox"
                checked={visibleNodeTypes.has(type.key)}
                onChange={() => toggleNodeType(type.key)}
              />
              <span
                className={`legend-swatch ${type.shape}`}
                style={{ background: type.color }}
              />
              <span>{type.label}</span>
            </label>
          ))}
        </div>
      </div>
      <div className="control-group">
        <h3>Relationships</h3>
        <div className="legend">
          {EDGE_TYPES.map((type) => (
            <label key={type.key} className="legend-item">
              <input
                type="checkbox"
                checked={visibleEdgeTypes.has(type.key)}
                onChange={() => toggleEdgeType(type.key)}
              />
              <svg width="20" height="10" style={{ flexShrink: 0 }}>
                <line
                  x1="0"
                  y1="5"
                  x2="18"
                  y2="5"
                  stroke={type.color}
                  strokeWidth="2"
                  strokeDasharray={type.dash}
                />
              </svg>
              <span>{type.label}</span>
            </label>
          ))}
        </div>
      </div>
      <div className="control-actions">
        <button className="btn btn-secondary" onClick={onReset}>
          Reset view
        </button>
      </div>
    </aside>
  )
}
