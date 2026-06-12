import { useState, useCallback } from 'react'

export default function UploadZone({ onFiles }) {
  const [dragOver, setDragOver] = useState(false)

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    setDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e) => {
    e.preventDefault()
    setDragOver(false)
  }, [])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setDragOver(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFiles(e.dataTransfer.files)
    }
  }, [onFiles])

  return (
    <div
      className={`upload-zone ${dragOver ? 'dragover' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <p>Drag CSV files here or use the <strong>Upload CSVs</strong> button in the top bar.</p>
      <p className="hint">
        Supported: FBR tax, excise vehicles, DISCO utility, property transfers, plus offshore/sanctions dumps.
      </p>
    </div>
  )
}
