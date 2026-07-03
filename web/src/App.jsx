import { useState, useEffect, useCallback, useMemo } from 'react'

import {
  getDemo,
  getBenchmark,
  postUpload,
  postRunFiles,
} from './api'
import { parsePreview } from './csvParser'
import { NODE_TYPES, EDGE_TYPES } from './constants'
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
import OnboardingOverlay from './components/OnboardingOverlay'
import HelperBanner from './components/HelperBanner'

const TABS = ['overview', 'profiles', 'graph', 'chat']

export default function App() {
  const [activeTab, setActiveTab] = useState('overview')
  const [result, setResult] = useState(null)
  const [uploadFiles, setUploadFiles] = useState([])
  const [uploadProgress, setUploadProgress] = useState(null)
  const [uploadProfiles, setUploadProfiles] = useState([])
  const [mappings, setMappings] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [toast, setToast] = useState(null)
  const [selectedEntityId, setSelectedEntityId] = useState(null)
  const [selectedGraphNodeId, setSelectedGraphNodeId] = useState(null)
  const [pipelineStep, setPipelineStep] = useState('ingest')
  const [benchmarkCitizens, setBenchmarkCitizens] = useState(500)
  const [onboardingDismissed, setOnboardingDismissed] = useState(
    () => localStorage.getItem('taxnet-onboarding-dismissed') === 'true'
  )
  const [helperBannerDismissed, setHelperBannerDismissed] = useState(
    () => localStorage.getItem('taxnet-helper-banner-dismissed') === 'true'
  )
  const [visibleNodeTypes, setVisibleNodeTypes] = useState(() => new Set(NODE_TYPES.map((t) => t.key)))
  const [visibleEdgeTypes, setVisibleEdgeTypes] = useState(() => new Set(EDGE_TYPES.map((t) => t.key)))

  useEffect(() => {
    const onDismiss = () => setOnboardingDismissed(true)
    window.addEventListener('taxnet-onboarding-dismissed', onDismiss)
    return () => window.removeEventListener('taxnet-onboarding-dismissed', onDismiss)
  }, [])

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
    const oversized = Array.from(files).find((f) => f.size > 100 * 1024 * 1024)
    if (oversized) {
      setError(`File too large: ${oversized.name}. Max size is 100 MB.`)
      return
    }
    setLoading(true)
    setError(null)
    setPipelineStep('ingest')
    try {
      setUploadProgress('Reading preview…')
      await Promise.all(Array.from(files).map((f) => parsePreview(f, 100)))
      setUploadFiles((prev) => [...prev, ...Array.from(files)])

      setUploadProgress('Uploading…')
      const response = await postUpload(Array.from(files))
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
      setUploadProgress(null)
    }
  }, [handleError, showToast])

  const handleRunUploaded = useCallback(async () => {
    if (uploadFiles.length === 0) {
      showToast('Load one or more CSV files first.')
      return
    }
    setLoading(true)
    setError(null)
    setPipelineStep('ingest')
    try {
      const payload = {}
      Object.entries(mappings).forEach(([name, data]) => {
        payload[name] = { _kind: data.detected_kind, ...data.fields }
      })
      const data = await postRunFiles(uploadFiles, payload)
      setResult(data)
      setPipelineStep('score')
      setSelectedEntityId(
        data.scoring?.flagged_profiles?.[0]?.entity_id ||
        data.scoring?.profiles?.[0]?.entity_id ||
        null
      )
      setActiveTab('profiles')
      showToast(`Uploaded files processed${data.ml_used ? ' with XGBoost' : ''}`)
    } catch (err) {
      handleError(err)
    } finally {
      setLoading(false)
    }
  }, [uploadFiles, mappings, handleError, showToast])

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

  const handleMappingReviewChange = useCallback((datasetName, field, value) => {
    if (field === '_kind') {
      handleKindChange(datasetName, value)
    } else {
      handleMappingChange(datasetName, field, value)
    }
  }, [handleKindChange, handleMappingChange])

  const handleNodeTypeToggle = useCallback((key) => {
    setVisibleNodeTypes((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }, [])

  const handleEdgeTypeToggle = useCallback((key) => {
    setVisibleEdgeTypes((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }, [])

  const selectedGraphNode = useMemo(() => {
    return result?.graph?.nodes?.find((n) => n.id === selectedGraphNodeId) || null
  }, [result?.graph?.nodes, selectedGraphNodeId])

  const metrics = useMemo(() => {
    if (!result) return null
    const profiles = result.scoring?.profiles || []
    const flagged = result.scoring?.flagged_profiles || []
    return {
      records: result.canonical_record_count ?? (result.canonical_records || []).length,
      entities: Object.keys(result.resolution?.entities || {}).length,
      flagged: `${flagged.length} (${profiles.length ? ((flagged.length / profiles.length) * 100).toFixed(0) : 0}%)`,
      ml: result.ml_used ? 'XGBoost active' : 'Rule-based only',
    }
  }, [result])

  return (
    <>
      <a href="#main-content" className="skip-link">Skip to main content</a>
      {!onboardingDismissed && !result && (
        <OnboardingOverlay
          onRunDemo={runDemo}
          onUpload={() => document.getElementById('topbar-file-input')?.click()}
        />
      )}
      {onboardingDismissed && !helperBannerDismissed && !result && (
        <HelperBanner
          onRunDemo={runDemo}
          onDismiss={() => {
            localStorage.setItem('taxnet-helper-banner-dismissed', 'true')
            setHelperBannerDismissed(true)
          }}
        />
      )}
      <Header onRunDemo={runDemo}>
        <button className="btn btn-primary" onClick={runDemo} disabled={loading}>
          Run synthetic audit
        </button>
        <label className="btn btn-secondary file-button">
          Upload CSVs
          <input
            id="topbar-file-input"
            type="file"
            multiple
            accept=".csv"
            onChange={(e) => handleFiles(e.target.files)}
            disabled={loading}
          />
        </label>
        <button className="btn btn-secondary" onClick={handleRunUploaded} disabled={loading}>
          Run uploaded
        </button>
        <div className="benchmark-control">
          <input
            type="number"
            min={1}
            max={5000}
            value={benchmarkCitizens}
            onChange={(e) => setBenchmarkCitizens(e.target.value)}
            disabled={loading}
            aria-label="Benchmark citizens"
          />
          <button className="btn btn-secondary" onClick={runBenchmark} disabled={loading}>
            Run benchmark
          </button>
        </div>
        <button className="btn btn-secondary" onClick={handleExport} disabled={!result || loading}>
          Export
        </button>
      </Header>
      <main id="main-content" className="main-content">
        {error && <div className="error-state" style={{ marginBottom: 'var(--space-lg)' }}>{error}</div>}
        <TabNav tabs={TABS} activeTab={activeTab} onChange={setActiveTab} />

        {activeTab === 'overview' && (
          <section className="tab-panel active" role="tabpanel" aria-labelledby="tab-overview">
            <div className="overview-layout">
              <PipelineStrip step={pipelineStep} />
              <MetricsRow metrics={metrics} loading={loading} />
              <div className="overview-grid">
                <section className="panel upload-panel">
                  <div className="panel-head">
                    <div>
                      <p className="eyebrow">Data source</p>
                      <h2>Load data</h2>
                    </div>
                  </div>
                  {uploadFiles.length === 0 && !result && (
                    <div className="upload-steps">
                      <h3>Get started</h3>
                      <ol>
                        <li>Drop one or more CSV files.</li>
                        <li>Review the detected column mappings.</li>
                        <li>Click <strong>Run uploaded</strong> to score entities.</li>
                      </ol>
                    </div>
                  )}
                  <UploadZone onFiles={handleFiles} />
                  {uploadFiles.length > 0 && (
                    <div className="uploaded-files">
                      {uploadFiles.map((file, index) => (
                        <span key={`${file.name}-${index}`} className="file-tag">
                          {file.name}
                          <button
                            type="button"
                            className="file-remove"
                            onClick={() => {
                              setUploadFiles((prev) => prev.filter((_, i) => i !== index))
                              setUploadProfiles((prev) => prev.filter((_, i) => i !== index))
                            }}
                            aria-label={`Remove ${file.name}`}
                          >
                            ×
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                  {uploadProgress && (
                    <div className="upload-progress" aria-live="polite">
                      <div className="upload-progress-bar" />
                      <span>{uploadProgress}</span>
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
                    onChange={handleMappingReviewChange}
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
                profiles={flaggedProfiles}
                selectedId={selectedEntityId}
                onSelect={setSelectedEntityId}
              />
              <CaseFile
                profile={selectedProfile}
                graphData={result?.graph}
                onInvestigateInGraph={(entityId) => {
                  setSelectedGraphNodeId(entityId)
                  setActiveTab('graph')
                }}
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
                onNodeTypeToggle={handleNodeTypeToggle}
                onEdgeTypeToggle={handleEdgeTypeToggle}
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
                  graphData={result?.graph}
                  selectedNodeId={selectedGraphNodeId}
                  onSelectNode={(entityId) => {
                    setSelectedGraphNodeId(entityId)
                    setSelectedEntityId(entityId)
                  }}
                  visibleNodeTypes={visibleNodeTypes}
                  visibleEdgeTypes={visibleEdgeTypes}
                />
              </div>
              <GraphDetail
                node={selectedGraphNode}
                graphData={result?.graph}
                profiles={profiles}
                onOpenCaseFile={(entityId) => {
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
