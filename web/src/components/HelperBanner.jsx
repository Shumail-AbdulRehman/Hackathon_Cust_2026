export default function HelperBanner({ onRunDemo, onDismiss }) {
  return (
    <aside className="helper-banner" aria-label="Help">
      <span>New here? Run the synthetic demo to see a sample investigation.</span>
      <div className="helper-banner-actions">
        <button className="btn btn-primary btn-small" onClick={onRunDemo}>Run demo</button>
        <button className="btn btn-ghost btn-small" onClick={onDismiss}>Dismiss</button>
      </div>
    </aside>
  )
}
