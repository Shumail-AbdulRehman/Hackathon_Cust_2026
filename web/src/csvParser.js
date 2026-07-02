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
