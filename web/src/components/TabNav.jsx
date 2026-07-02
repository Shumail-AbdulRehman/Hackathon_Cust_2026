export default function TabNav({ tabs, activeTab, onChange }) {
  return (
    <nav className="tab-nav" role="tablist" aria-label="Primary tabs">
      {tabs.map((tab) => {
        const id = typeof tab === 'string' ? tab : tab.id
        const label = typeof tab === 'string' ? tab : tab.label
        const isActive = id === activeTab
        return (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={isActive}
            tabIndex={isActive ? 0 : -1}
            className={`tab-btn${isActive ? ' active' : ''}`}
            onClick={() => onChange(id)}
          >
            {label}
          </button>
        )
      })}
    </nav>
  )
}
