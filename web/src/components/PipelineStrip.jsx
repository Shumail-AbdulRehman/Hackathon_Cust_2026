const STEPS = [
  { key: 'ingest', label: 'Ingest', status: (step) => (step === 'ingest' ? 'Running' : step === 'resolve' || step === 'score' ? 'Done' : 'Waiting') },
  { key: 'resolve', label: 'Resolve', status: (step) => (step === 'resolve' ? 'Running' : step === 'score' ? 'Done' : 'Waiting') },
  { key: 'score', label: 'Score', status: (step) => (step === 'score' ? 'Done' : 'Waiting') },
]

export default function PipelineStrip({ step }) {
  const activeIndex = STEPS.findIndex((s) => s.key === step)
  return (
    <div className="pipeline-strip panel">
      {STEPS.map((s, idx) => {
        const state = idx < activeIndex ? 'done' : idx === activeIndex ? 'active' : ''
        return (
          <div key={s.key} className={`pipeline-step ${state}`} data-step={s.key}>
            <span className="step-number">{String(idx + 1).padStart(2, '0')}</span>
            <strong>{s.label}</strong>
            <small>{s.status(step)}</small>
          </div>
        )
      })}
    </div>
  )
}
