// web/src/components/Header.jsx
export default function Header({ children, onRunDemo }) {
  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-mark">T</div>
        <div>
          <p className="eyebrow">Explainable AI</p>
          <h1 className="brand-title">TaxNet XAI</h1>
        </div>
      </div>
      <div className="top-actions">
        {onRunDemo && (
          <button className="btn btn-primary btn-small" onClick={onRunDemo}>
            Run demo
          </button>
        )}
        {children}
      </div>
    </header>
  )
}
