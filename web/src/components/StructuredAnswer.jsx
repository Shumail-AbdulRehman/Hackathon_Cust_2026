import Markdown from 'react-markdown'

function parseSections(text) {
  if (!text) return {}
  const normalized = text.replace(/\r\n/g, '\n')
  const sections = {}
  let current = 'answer'
  sections[current] = []

  const isHeader = (line) => {
    const l = line.toLowerCase()
    return (
      l.startsWith('why xgboost') ||
      l.startsWith('xgboost') ||
      l.startsWith('legal basis') ||
      l.startsWith('relevant law') ||
      l.startsWith('forensic auditor') ||
      l.startsWith('forensic questions') ||
      l.startsWith('three forensic') ||
      l.startsWith('3 forensic')
    )
  }

  for (const raw of normalized.split('\n')) {
    const line = raw.trim()
    if (!line) continue
    if (isHeader(line)) {
      if (line.includes('xgboost')) current = 'xgboost'
      else if (line.includes('law') || line.includes('legal')) current = 'law'
      else if (line.includes('forensic')) current = 'forensic'
      else current = 'answer'
      if (!sections[current]) sections[current] = []
      continue
    }
    sections[current].push(line)
  }

  return {
    answer: sections.answer?.join('\n\n') || '',
    xgboost: sections.xgboost?.join('\n\n') || '',
    law: sections.law?.join('\n\n') || '',
    forensic: sections.forensic?.join('\n\n') || '',
  }
}

export default function StructuredAnswer({ text, mode }) {
  const { answer, xgboost, law, forensic } = parseSections(text)

  return (
    <div className="structured-answer">
      <section className="answer-section">
        <h4>Answer</h4>
        <div className="markdown-body">
          <Markdown>{answer || text}</Markdown>
        </div>
      </section>

      {mode === 'node' && xgboost && (
        <section className="answer-section xgboost-section">
          <h4>Why XGBoost triggered</h4>
          <div className="markdown-body">
            <Markdown>{xgboost}</Markdown>
          </div>
        </section>
      )}

      {law && (
        <section className="answer-section law-section">
          <h4>Legal basis</h4>
          <div className="markdown-body">
            <Markdown>{law}</Markdown>
          </div>
        </section>
      )}

      {forensic && (
        <section className="answer-section forensic-section">
          <h4>Forensic auditor Q&A</h4>
          <div className="markdown-body">
            <Markdown>{forensic}</Markdown>
          </div>
        </section>
      )}
    </div>
  )
}
