import { useState, useCallback, useMemo } from 'react'
import {
  getDemo,
  getBenchmark,
  postProfile,
  postRun,
} from './api'
import { parseCsv } from './csvParser'
import { TIER_LABELS, TIER_ORDER, NODE_TYPES, EDGE_TYPES } from './constants'
import Header from './components/Header'
import TabNav from './components/TabNav'
import PipelineStrip from './components/PipelineStrip'
import MetricsRow from './components/MetricsRow'
import UploadZone from './components/UploadZone'
import MappingReview from './components/MappingReview'
import DatasetProfiles from './components/DatasetProfiles'
import TierChart from './components/TierChart'
import ProfileQueue from './components/ProfileQueue'
import CaseFile from './components/CaseFile'
import GraphCanvas from './components/GraphCanvas'
import GraphControls from './components/GraphControls'
import GraphDetail from './components/GraphDetail'
import ChatTab from './components/ChatTab'

const TABS = ['overview', 'profiles', 'graph', 'chat']

function formatPKR(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return '—'
  return `PKR ${num.toLocaleString()}`
}

function safe(str) {
  return String(str ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
}

function tierClass(tier) {
  return TIER_ORDER.includes(tier) ? tier : 'green'
}

export default function App() {
  const [activeTab, setActiveTab] = useState('overview')
  const [result, setResult] = useState(null)
  const [uploaded, setUploaded] = useState({})
  const [uploadProfiles, setUploadProfiles] = useState([])
  const [mappings, setMappings] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [toast, setToast] = useState(null)
  const [selectedEntityId, setSelectedEntityId] = useState(null)
  const [selectedGraphNodeId, setSelectedGraphNodeId] = useState(null)
  const [pipelineStep, setPipelineStep] = useState('ingest')
  const [benchmarkCitizens, setBenchmarkCitizens] = useState(500)
  const [visibleNodeTypes, setVisibleNodeTypes] = useState(() => new Set(NODE_TYPES.map((t) => t.key)))
  const [visibleEdgeTypes, setVisibleEdgeTypes] = useState(() => new Set(EDGE_TYPES.map((t) => t.key)))

  const profiles = result?.scoring?.profiles || []
  const flaggedProfiles = result?.scoring?.flagged_profiles || []
  const selectedProfile = profiles.find((p) => p.entity_id === selectedEntityId)

  const showToast = useCallback((message) => {
    setToast(message)
    setTimeout(() => setToast(null), 3000)
  }, [])

  const handleError = useCallback((err) => {
    setError(err.message || 'An error occurred')
    setLoading(false)
  }, [])

  const runDemo = useCallback(async () => {
    setLoading(true)
    setError(null)
    setPipelineStep('ingest')
    try {
      const data = await getDemo()
      setResult(data)
      setPipelineStep('score')
      setSelectedEntityId(data.scoring?.flagged_profiles?.[0]?.entity_id || data.scoring?.profiles?.[0]?.entity_id || null)
      setActiveTab('profiles')
      showToast('Synthetic audit complete')
    } catch (err) {
      handleError(err)
    } finally {
      setLoading(false)
    }
  }, [handleError, showToast])

  const runBenchmark = useCallback(async () => {
    const citizens = Math.max(1, Math.min(5000, Number(benchmarkCitizens) || 500))
    setBenchmarkCitizens(citizens)
    setLoading(true)
    setError(null)
    setPipelineStep('score')
    try {
      const summary = await getBenchmark(citizens)
      setResult({
        mode: 'benchmark',
        benchmark: summary,
        scoring: { profiles: [], flagged_profiles: [], summary: summary.scoring_summary },
      })
      setActiveTab('overview')
      showToast(`Benchmark complete: ${summary.throughput_records_per_second} records/s`)
    } catch (err) {
      handleError(err)
    } finally {
      setLoading(false)
    }
  }, [benchmarkCitizens, handleError, showToast])

  const handleFiles = useCallback(async (files) => {
    if (!files || files.length === 0) return
    setLoading(true)
    setError(null)
    setPipelineStep('ingest')
    try {
      const loaded = {}
      for (const file of files) {
        const text = await file.text()
        loaded[file.name] = parseCsv(text)
      }
      const nextUploaded = { ...uploaded, ...loaded }
      setUploaded(nextUploaded)
      const response = await postProfile(nextUploaded)
      const profiles = response.profiles || []
      setUploadProfiles(profiles)
      const initialMappings = {}
      profiles.forEach((profile) => {
        initialMappings[profile.name] = {
          detected_kind: profile.detected_kind,
          fields: { ...(profile.mapping || {}) },
        }
      })
      setMappings(initialMappings)
      setResult(null)
      setSelectedEntityId(null)
      setPipelineStep('resolve')
      setActiveTab('overview')
      showToast('CSV profiled; review mappings before running')
    } catch (err) {
      handleError(err)
    } finally {
      setLoading(false)
    }
  }, [uploaded, handleError, showToast])

  const handleRunUploaded = useCallback(async () => {
    const names = Object.keys(uploaded)
    if (names.length === 0) {
      showToast('Load one or more CSV files first.')
      return
    }
    setLoading(true)
    setError(null)
    setPipelineStep('ingest')
    try {
      const payload = {}
      Object.entries(mappings).forEach(([name, data]) => {
        payload[name] = {
          _kind: data.detected_kind,
          ...data.fields,
        }
      })
      const data = await postRun(uploaded, payload)
      setResult(data)
      setPipelineStep('score')
      setSelectedEntityId(data.scoring?.flagged_profiles?.[0]?.entity_id || data.scoring?.profiles?.[0]?.entity_id || null)
      setActiveTab('profiles')
      showToast('Uploaded files processed')
    } catch (err) {
      handleError(err)
    } finally {
      setLoading(false)
    }
  }, [uploaded, mappings, handleError, showToast])

  const handleExport = useCallback(() => {
    if (!result) return
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `taxnet-report-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }, [result])

  const handleMappingChange = useCallback((datasetName, canonical, sourceColumn) => {
    setMappings((prev) => ({
      ...prev,
      [datasetName]: {
        ...prev[datasetName],
        fields: {
          ...prev[datasetName]?.fields,
          [canonical]: sourceColumn,
        },
      },
    }))
  }, [])

  const handleKindChange = useCallback((datasetName, kind) => {
    setMappings((prev) => ({
      ...prev,
      [datasetName]: {
        ...prev[datasetName],
        detected_kind: kind,
      },
    }))
  }, [])

  const metrics = useMemo(() => {
    if (!result) return null
    if (result.mode === 'benchmark') {
      return {
        records: result.benchmark?.canonical_record_count || 0,
        entities: result.benchmark?.entity_count || 0,
        flagged: '—',
        confidence: '—',
        topTier: '—',
      }
    }
    const allProfiles = result.scoring?.profiles || []
    const flagged = result.scoring?.flagged_profiles || []
    const avgConfidence = allProfiles.length
      ? (allProfiles.reduce((sum, p) => sum + (p.scoring_confidence || 0), 0) / allProfiles.length).toFixed(1)
      : '—'
    const tierCounts = {}
    allProfiles.forEach((p) => {
      tierCounts[p.risk_tier] = (tierCounts[p.risk_tier] || 0) + 1
    })
    const topTier = TIER_ORDER.find((t) => tierCounts[t] && tierCounts[t] > 0) || '—'
    return {
      records: result.canonical_record_count || 0,
      entities: result.resolution?.entities?.length || 0,
      flagged: flagged.length,
      confidence: avgConfidence === '—' ? avgConfidence : `${avgConfidence}%`,
      topTier: TIER_LABELS[topTier] || topTier,
    }
  }, [result])

  return (
    <>
      <a href="#main-content" className="skip-link">Skip to main content</a>
      <Header
        onRunDemo={runDemo}
        onRunBenchmark={runBenchmark}
        onRunUploaded={handleRunUploaded}
        onExport={handleExport}
        onFilesSelected={handleFiles}
        benchmarkCitizens={benchmarkCitizens}
        onBenchmarkCitizensChange={setBenchmarkCitizens}
        canExport={!!result}
        loading={loading}
      />
      <main id="main-content" className="main-content">
        {error && <div className="error-state" style={{ marginBottom: 'var(--space-lg)' }}>{error}</div>}
        <TabNav tabs={TABS} activeTab={activeTab} onChange={setActiveTab} />

        {activeTab === 'overview' && (
          <section className="tab-panel active" role="tabpanel" aria-labelledby="tab-overview">
            <div className="overview-layout">
              <PipelineStrip step={pipelineStep} />
              <MetricsRow metrics={metrics} loading={loading && !result} />
              <div className="overview-grid">
                <section className="panel upload-panel">
                  <div className="panel-head">
                    <div>
                      <p className="eyebrow">Data source</p>
                      <h2>Load data</h2>
                    </div>
                  </div>
                  <UploadZone onFiles={handleFiles} />
                  {Object.keys(uploaded).length > 0 && (
                    <div className="uploaded-files">
                      {Object.entries(uploaded).map(([name, rows]) => (
                        <span key={name} className="file-tag">
                          {name} <small>({rows.length} rows)</small>
                        </span>
                      ))}
                    </div>
                  )}
                </section>
                <section className="panel tier-distribution-panel">
                  <div className="panel-head">
                    <div>
                      <p className="eyebrow">Risk distribution</p>
                      <h2>Tier breakdown</h2>
                    </div>
                  </div>
                  <TierChart profiles={profiles} />
                </section>
              </div>
              {uploadProfiles.length > 0 && (
                <section className="panel mapping-panel">
                  <div className="panel-head">
                    <div>
                      <p className="eyebrow">Schema review</p>
                      <h2>CSV Field Mapping</h2>
                    </div>
                    <span className="count">{uploadProfiles.length}</span>
                  </div>
                  <MappingReview
                    profiles={uploadProfiles}
                    mappings={mappings}
                    onMappingChange={handleMappingChange}
                    onKindChange={handleKindChange}
                  />
                </section>
              )}
              <section className="panel dataset-profiles-panel">
                <div className="panel-head">
                  <div>
                    <p className="eyebrow">Ingestion</p>
                    <h2>Dataset profiles</h2>
                  </div>
                </div>
                <DatasetProfiles profiles={result?.profiles || uploadProfiles} />
              </section>
            </div>
          </section>
        )}

        {activeTab === 'profiles' && (
          <section className="tab-panel active" role="tabpanel" aria-labelledby="tab-profiles">
            <div className="profiles-layout">
              <ProfileQueue
                flagged={flaggedProfiles}
                selectedId={selectedEntityId}
                onSelect={setSelectedEntityId}
              />
              <CaseFile
                profile={selectedProfile}
                graph={result?.graph}
                onInvestigateInGraph={(entityId) => {
                  setSelectedGraphNodeId(entityId)
                  setActiveTab('graph')
                }}
                formatPKR={formatPKR}
                tierClass={tierClass}
                safe={safe}
              />
            </div>
          </section>
        )}

        {activeTab === 'graph' && (
          <section className="tab-panel active" role="tabpanel" aria-labelledby="tab-graph">
            <div className="graph-layout">
              <GraphControls
                visibleNodeTypes={visibleNodeTypes}
                visibleEdgeTypes={visibleEdgeTypes}
                onNodeTypesChange={setVisibleNodeTypes}
                onEdgeTypesChange={setVisibleEdgeTypes}
                onReset={() => {
                  setSelectedGraphNodeId(null)
                }}
                onFit={() => {}}
              />
              <div className="graph-canvas-wrapper panel">
                <div className="panel-head graph-canvas-head">
                  <div>
                    <p className="eyebrow">Investigation</p>
                    <h2>Network view</h2>
                  </div>
                  <div className="graph-toolbar">
                    <span id="graphStats" className="graph-stats" />
                  </div>
                </div>
                <GraphCanvas
                  graph={result?.graph}
                  selectedNodeId={selectedGraphNodeId}
                  onSelectNode={setSelectedGraphNodeId}
                  visibleNodeTypes={visibleNodeTypes}
                  visibleEdgeTypes={visibleEdgeTypes}
                />
              </div>
              <GraphDetail
                graph={result?.graph}
                selectedNodeId={selectedGraphNodeId}
                profiles={profiles}
                onOpenInProfiles={(entityId) => {
                  setSelectedEntityId(entityId)
                  setActiveTab('profiles')
                }}
              />
            </div>
          </section>
        )}

        {activeTab === 'chat' && (
          <ChatTab selectedNodeId={selectedEntityId} onSelectNode={setSelectedEntityId} />
        )}
      </main>
      {toast && <div className="toast" role="status" aria-live="polite">{toast}</div>}
    </>
  )
}
