export default function UploadZone({ onChange, hint = 'Drop CSV files here or click to browse.' }) {
  return (
    <label className="upload-zone file-button">
      <input type="file" accept=".csv" multiple onChange={onChange} />
      <div>
        <strong>Upload CSV datasets</strong>
        <p className="hint">{hint}</p>
      </div>
    </label>
  )
}
