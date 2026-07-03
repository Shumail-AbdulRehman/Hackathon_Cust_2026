import { useState } from 'react'

export default function OnboardingOverlay({ onRunDemo, onUpload }) {
  const [dontShow, setDontShow] = useState(false)

  const dismiss = () => {
    localStorage.setItem('taxnet-onboarding-dismissed', 'true')
    window.dispatchEvent(new Event('taxnet-onboarding-dismissed'))
  }

  const handleRunDemo = () => {
    if (dontShow) dismiss()
    onRunDemo()
  }

  const handleUpload = () => {
    if (dontShow) dismiss()
    onUpload()
  }

  return (
    <div className="onboarding-overlay" role="dialog" aria-modal="true" aria-labelledby="onboarding-title">
      <div className="onboarding-card">
        <div className="brand-mark large">T</div>
        <h2 id="onboarding-title">Welcome to TaxNet XAI</h2>
        <p className="onboarding-subhead">
          Upload civic records — tax, utility, vehicle, property — to detect audit-risk patterns,
          or run a synthetic demo to see how it works.
        </p>
        <div className="onboarding-actions">
          <button className="btn btn-primary" onClick={handleRunDemo}>Run synthetic demo</button>
          <button className="btn btn-secondary" onClick={handleUpload}>Upload CSV records</button>
        </div>
        <label className="onboarding-checkbox">
          <input
            type="checkbox"
            checked={dontShow}
            onChange={(e) => setDontShow(e.target.checked)}
          />
          Don’t show this again
        </label>
        <button className="onboarding-close" onClick={dismiss} aria-label="Close">×</button>
      </div>
    </div>
  )
}
