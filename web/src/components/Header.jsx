export default function Header({
  onRunDemo,
  onRunBenchmark,
  onRunUploaded,
  onExport,
  onFilesSelected,
  benchmarkCitizens,
  onBenchmarkCitizensChange,
  canExport,
  loading,
}) {
  return (
    <header className="topbar">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true">⊕</span>
        <div>
          <p className="eyebrow">CUST Hackathon 2026</p>
          <h1 className="brand-title">TaxNet XAI</h1>
        </div>
      </div>

      <div className="top-actions">
        <label className="btn btn-secondary file-button">
          <input
            id="fileInput"
            type="file"
            accept=".csv"
            multiple
            hidden
            onChange={(e) => {
              onFilesSelected(e.target.files)
              e.target.value = ''
            }}
          />
          Upload CSVs
        </label>
        <button className="btn btn-secondary" onClick={onRunUploaded} disabled={loading}>
          Run uploaded
        </button>
        <button className="btn btn-primary" onClick={onRunDemo} disabled={loading}>
          Run synthetic audit
        </button>
        <label className="benchmark-control">
          <span>Citizens</span>
          <input
            className="input"
            type="number"
            min={1}
            max={5000}
            value={benchmarkCitizens}
            onChange={(e) => onBenchmarkCitizensChange(e.target.value)}
          />
        </label>
        <button className="btn btn-ghost" onClick={onRunBenchmark} disabled={loading}>
          Benchmark
        </button>
        <button className="btn btn-ghost" onClick={onExport} disabled={!canExport}>
          Export
        </button>
      </div>
    </header>
  )
}
