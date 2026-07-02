export default function PipelineStrip({ steps }) {
  return (
    <div className="panel">
      <div className="pipeline-strip" role="list">
        {steps.map((step, index) => {
          const classes = ['pipeline-step']
          if (step.status === 'active') classes.push('active')
          if (step.status === 'done') classes.push('done')
          return (
            <div key={step.id} className={classes.join(' ')} role="listitem">
              <span className="step-number">{String(index + 1).padStart(2, '0')}</span>
              <strong>{step.label}</strong>
              <small>{step.detail || ''}</small>
            </div>
          )
        })}
      </div>
    </div>
  )
}
