import { useState, useRef, useEffect } from 'react'
import { postAsk, postAskTax } from '../api'
import NodeSummarySidebar from './NodeSummarySidebar'
import StructuredAnswer from './StructuredAnswer'

export default function ChatTab({ selectedNodeId, onSelectNode }) {
  const [mode, setMode] = useState('law') // 'law' | 'node'
  const [query, setQuery] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSend = async (e) => {
    e.preventDefault()
    if (!query.trim()) return

    const userMsg = { role: 'user', text: query }
    setMessages((prev) => [...prev, userMsg])
    setLoading(true)

    try {
      let res
      if (mode === 'node') {
        if (!selectedNodeId) {
          throw new Error('Select a node first or search for one in the sidebar.')
        }
        res = await postAskTax(selectedNodeId, query)
      } else {
        res = await postAsk(query)
      }
      setMessages((prev) => [...prev, { role: 'assistant', text: res.answer, mode }])
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'error', text: err.message }])
    } finally {
      setLoading(false)
      setQuery('')
    }
  }

  const placeholder =
    mode === 'node'
      ? selectedNodeId
        ? 'Ask about this entity...'
        : 'Select a node first'
      : 'Ask a tax law question...'

  return (
    <section className="tab-panel active chat-tab" role="tabpanel" aria-labelledby="tab-chat">
      <div className={`chat-layout ${mode === 'node' ? 'node-mode' : ''}`}>
        {mode === 'node' && (
          <NodeSummarySidebar entityId={selectedNodeId} onChangeEntity={onSelectNode} />
        )}

        <div className="chat-main panel">
          <div className="panel-head chat-head">
            <div>
              <p className="eyebrow">SLM Assistant</p>
              <h2>{mode === 'node' ? 'Node Investigation' : 'Law RAG'}</h2>
            </div>
            <div className="mode-toggle">
              <button
                className={`chip ${mode === 'law' ? 'active' : ''}`}
                onClick={() => setMode('law')}
              >
                Law RAG
              </button>
              <button
                className={`chip ${mode === 'node' ? 'active' : ''}`}
                onClick={() => setMode('node')}
              >
                Node Investigation
              </button>
            </div>
          </div>

          <div className="chat-messages">
            {messages.length === 0 && (
              <div className="empty-state">
                <p>Ask a question to get started.</p>
                {mode === 'node' && !selectedNodeId && (
                  <p>Select a node from Profiles/Graph or search in the sidebar.</p>
                )}
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`chat-message ${m.role}`}>
                {m.role === 'user' && <div className="message-bubble user">{m.text}</div>}
                {m.role === 'assistant' && (
                  <div className="message-bubble assistant">
                    <StructuredAnswer text={m.text} mode={m.mode || mode} />
                  </div>
                )}
                {m.role === 'error' && <div className="message-bubble error">{m.text}</div>}
              </div>
            ))}
            {loading && (
              <div className="chat-message assistant">
                <div className="message-bubble assistant loading">Thinking...</div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <form className="chat-input-bar" onSubmit={handleSend}>
            <input
              className="input"
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={placeholder}
              disabled={loading || (mode === 'node' && !selectedNodeId)}
            />
            <button
              className="btn btn-primary"
              type="submit"
              disabled={loading || !query.trim() || (mode === 'node' && !selectedNodeId)}
            >
              Send
            </button>
          </form>
        </div>
      </div>
    </section>
  )
}
