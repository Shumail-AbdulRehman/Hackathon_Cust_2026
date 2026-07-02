export default function Header({ children }) {
  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-mark">T</div>
        <div>
          <p className="eyebrow">Explainable AI</p>
          <h1 className="brand-title">TaxNet XAI</h1>
        </div>
      </div>
      <div className="top-actions">{children}</div>
    </header>
  )
}
