const LABELS = {
  overview: 'Overview',
  profiles: 'Profiles',
  graph: 'Graph Investigation',
}

export default function TabNav({ tabs, activeTab, onChange }) {
  return (
    <nav className="tab-nav" role="tablist" aria-label="Primary views" style={{ marginBottom: 'var(--space-lg)' }}>
      {tabs.map((tab) => (
        <button
          key={tab}
          className={`tab-btn ${activeTab === tab ? 'active' : ''}`}
          role="tab"
          aria-selected={activeTab === tab}
          aria-controls={`panel-${tab}`}
          id={`tab-${tab}`}
          tabIndex={activeTab === tab ? 0 : -1}
          onClick={() => onChange(tab)}
        >
          {LABELS[tab]}
        </button>
      ))}
    </nav>
  )
}
