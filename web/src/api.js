const API_BASE = ''

async function parseJsonResponse(response) {
  const text = await response.text()
  if (!response.ok) {
    let message = text || response.statusText
    try {
      const parsed = JSON.parse(message)
      if (parsed.error) message = parsed.error
    } catch {
      // keep raw text
    }
    throw new Error(message)
  }
  return text ? JSON.parse(text) : {}
}

export async function getHealth() {
  const response = await fetch(`${API_BASE}/api/health`)
  return parseJsonResponse(response)
}

export async function getDemo() {
  const response = await fetch(`${API_BASE}/api/demo`)
  return parseJsonResponse(response)
}

export async function getBenchmark(citizens = 500, seed = 42) {
  const params = new URLSearchParams({ citizens: String(citizens), seed: String(seed) })
  const response = await fetch(`${API_BASE}/api/benchmark?${params}`)
  return parseJsonResponse(response)
}

export async function postProfile(datasets, mappings = null) {
  const response = await fetch(`${API_BASE}/api/profile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ datasets, mappings }),
  })
  return parseJsonResponse(response)
}

export async function postRun(datasets, mappings = null) {
  const response = await fetch(`${API_BASE}/api/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ datasets, mappings }),
  })
  return parseJsonResponse(response)
}

export async function getProfiles(query = '') {
  const params = query ? `?q=${encodeURIComponent(query)}` : ''
  const response = await fetch(`${API_BASE}/api/profiles${params}`)
  return parseJsonResponse(response)
}

export async function getProfile(entityId) {
  const response = await fetch(`${API_BASE}/api/profiles/${encodeURIComponent(entityId)}`)
  return parseJsonResponse(response)
}

export async function getSlmProvider() {
  const response = await fetch(`${API_BASE}/api/slm-provider`)
  return parseJsonResponse(response)
}

export async function postAsk(question, topK = 5) {
  const response = await fetch(`${API_BASE}/api/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, top_k: topK }),
  })
  return parseJsonResponse(response)
}

export async function postAskTax(entityId, query, topK = 5) {
  const response = await fetch(`${API_BASE}/api/ask-tax`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ entity_id: entityId, query, top_k: topK }),
  })
  return parseJsonResponse(response)
}
