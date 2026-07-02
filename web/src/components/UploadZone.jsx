// web/src/components/UploadZone.jsx
import { useState } from 'react'

export default function UploadZone({ onFiles, hint = 'Drop CSV files here or click to browse.' }) {
  const [drag, setDrag] = useState(false)

  const handleChange = (e) => {
    if (onFiles && e.target.files) {
      onFiles(Array.from(e.target.files))
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDrag(false)
    if (onFiles && e.dataTransfer.files) {
      onFiles(Array.from(e.dataTransfer.files))
    }
  }

  return (
    <label
      className={`upload-zone file-button ${drag ? 'drag-over' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
      onDragLeave={() => setDrag(false)}
      onDrop={handleDrop}
    >
      <input type="file" accept=".csv,text/csv" multiple onChange={handleChange} />
      <div>
        <strong>Upload CSV datasets</strong>
        <p className="hint">{hint}</p>
      </div>
    </label>
  )
}
