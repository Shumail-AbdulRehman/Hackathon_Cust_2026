import { csvParse } from 'd3-dsv'

export function parseCsv(text) {
  const rows = []
  let current = ''
  let row = []
  let inQuotes = false
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i]
    const next = text[i + 1]
    if (char === '"' && inQuotes && next === '"') {
      current += '"'
      i += 1
    } else if (char === '"') {
      inQuotes = !inQuotes
    } else if (char === ',' && !inQuotes) {
      row.push(current.trim())
      current = ''
    } else if ((char === '\n' || char === '\r') && !inQuotes) {
      if (char === '\r' && next === '\n') i += 1
      row.push(current.trim())
      if (row.some((cell) => cell.length)) rows.push(row)
      row = []
      current = ''
    } else {
      current += char
    }
  }
  if (current.length || row.length) {
    row.push(current.trim())
    if (row.some((cell) => cell.length)) rows.push(row)
  }
  const headers = rows.shift() || []
  return rows.map((cells, index) => {
    const item = { source_row_id: String(index + 1) }
    headers.forEach((header, col) => {
      item[header] = cells[col] ?? ''
    })
    return item
  })
}

export async function parsePreview(file, maxRows = 100) {
  // Read only the first ~50 KB to avoid loading huge files into memory for preview.
  const previewBytes = 50_000
  const chunk = file.slice(0, Math.min(previewBytes, file.size))
  const text = await chunk.text()
  const all = csvParse(text)
  const rows = all.slice(0, maxRows).map((row, index) => ({
    source_row_id: String(index + 1),
    ...row,
  }))
  return { headers: all.columns, rows, totalHint: all.length }
}
