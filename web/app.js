/* global d3 */

const state = {
  result: null,
  selectedId: null,
  uploaded: {},
  uploadProfiles: [],
  mappings: {},
  reportUrl: null,
  activeTab: "overview",
  graph: {
    simulation: null,
    svg: null,
    zoom: null,
    selectedNodeId: null,
    visibleNodeTypes: new Set(NODE_TYPES.map((t) => t.key)),
    visibleEdgeTypes: new Set(EDGE_TYPES.map((t) => t.key)),
  },
};

const KIND_FIELDS = {
  tax: ["person_name", "address", "phone", "declared_income", "tax_paid", "filer_status"],
  vehicle: ["person_name", "address", "vehicle_reg_no", "engine_capacity_cc", "vehicle_make_model", "registration_year"],
  utility: ["person_name", "address", "meter_ref_no", "monthly_bill", "connection_type"],
  property: ["person_name", "seller_name", "address", "registry_no", "property_value", "transfer_date", "area_marla", "property_type"],
  generic: ["person_name", "address", "phone"],
};

const FIELD_LABELS = {
  person_name: "Person name",
  seller_name: "Seller name",
  address: "Address",
  phone: "Phone",
  declared_income: "Declared income",
  tax_paid: "Tax paid",
  filer_status: "Filer status",
  vehicle_reg_no: "Vehicle reg no",
  engine_capacity_cc: "Engine capacity",
  vehicle_make_model: "Vehicle model",
  registration_year: "Registration year",
  meter_ref_no: "Meter ref no",
  monthly_bill: "Monthly bill",
  connection_type: "Connection type",
  registry_no: "Registry no",
  property_value: "Property value",
  transfer_date: "Transfer date",
  area_marla: "Area marla",
  property_type: "Property type",
};

const TIER_ORDER = ["critical", "red", "orange", "yellow", "green"];
const TIER_LABELS = { critical: "Critical", red: "High", orange: "Medium", yellow: "Low", green: "Clean" };

const NODE_TYPES = [
  { key: "Person", label: "Person", color: "#1a2b4a", shape: "circle" },
  { key: "Vehicle", label: "Vehicle", color: "#3d6b52", shape: "square" },
  { key: "Property", label: "Property", color: "#d4b876", shape: "diamond" },
  { key: "Meter", label: "Utility meter", color: "#5e5c58", shape: "triangle" },
  { key: "TaxReturn", label: "Tax return", color: "#7a9e7e", shape: "circle" },
  { key: "OffshoreEntity", label: "Offshore entity", color: "#c88a2a", shape: "hexagon" },
  { key: "Address", label: "Address", color: "#a64b2a", shape: "square" },
  { key: "PhoneNumber", label: "Phone number", color: "#7d5a44", shape: "square" },
];

const EDGE_TYPES = [
  { key: "USES_ADDRESS", label: "Uses address", color: "#a64b2a", dash: "0" },
  { key: "USES_PHONE", label: "Uses phone", color: "#7d5a44", dash: "0" },
  { key: "FILED_IN", label: "Filed tax return", color: "#7a9e7e", dash: "0" },
  { key: "OWNS_VEHICLE", label: "Owns vehicle", color: "#3d6b52", dash: "0" },
  { key: "HAS_UTILITY_METER", label: "Has utility meter", color: "#5e5c58", dash: "0" },
  { key: "BOUGHT_PROPERTY", label: "Bought property", color: "#d4b876", dash: "0" },
  { key: "LINKED_TO_OFFSHORE_ENTITY", label: "Offshore link", color: "#c88a2a", dash: "0" },
  { key: "SAME_ADDRESS_AS", label: "Same address", color: "#1a2b4a", dash: "4 4" },
  { key: "SHARES_PHONE_WITH", label: "Shares phone", color: "#3d6b52", dash: "2 2" },
];

function tierClass(tier) {
  return TIER_ORDER.includes(tier) ? tier : "low";
}

const el = (id) => document.getElementById(id);
const safe = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

function formatNumber(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "—";
  if (Math.abs(num) >= 1_000_000) return `₨ ${(num / 1_000_000).toFixed(2)}M`;
  if (Math.abs(num) >= 1_000) return `₨ ${(num / 1_000).toFixed(1)}K`;
  return `₨ ${num.toLocaleString()}`;
}

function formatPKR(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "—";
  return `PKR ${num.toLocaleString()}`;
}

function showToast(message) {
  const toast = el("toast");
  toast.textContent = message;
  toast.hidden = false;
  setTimeout(() => {
    toast.hidden = true;
  }, 3000);
}

async function parseJsonResponse(response) {
  const text = await response.text();
  if (!response.ok) throw new Error(text || response.statusText);
  return text ? JSON.parse(text) : {};
}

async function getJson(url) {
  return parseJsonResponse(await fetch(url));
}

async function postJson(url, payload) {
  return parseJsonResponse(
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

function setPipelineStatus(step, label) {
  const statuses = { ingest: el("ingestStatus"), resolve: el("resolveStatus"), score: el("scoreStatus") };
  const steps = ["ingest", "resolve", "score"];
  const index = steps.indexOf(step);
  if (index === -1) return;
  statuses[step].textContent = label;
  document.querySelectorAll(".pipeline-step").forEach((node, idx) => {
    node.classList.remove("active", "done");
    if (idx < index) node.classList.add("done");
    if (idx === index) node.classList.add("active");
  });
}

function setLoading() {
  setPipelineStatus("ingest", "Running");
  el("resolveStatus").textContent = "Waiting";
  el("scoreStatus").textContent = "Waiting";
  el("exportReport").disabled = true;
  document.querySelectorAll(".metric-card").forEach((card) => card.classList.add("loading"));
}

function recordResult(result) {
  state.result = result;
  const flagged = result.scoring?.flagged_profiles || [];
  const profiles = result.scoring?.profiles || [];
  state.selectedId = flagged[0]?.entity_id || profiles[0]?.entity_id || null;
  state.reportUrl = null;
}

async function runDemo() {
  try {
    setLoading();
    el("mappingPanel").hidden = true;
    const result = await getJson("/api/demo");
    recordResult(result);
    switchTab("profiles");
    render();
    showToast("Synthetic audit complete");
  } catch (error) {
    alert(`Pipeline failed: ${error.message}`);
  }
}

async function runBenchmark() {
  const requested = Number(el("benchmarkCitizens").value || 500);
  const citizens = Math.max(1, Math.min(5000, Number.isFinite(requested) ? requested : 500));
  el("benchmarkCitizens").value = String(citizens);
  try {
    setLoading();
    el("mappingPanel").hidden = true;
    const summary = await getJson(`/api/benchmark?citizens=${encodeURIComponent(citizens)}`);
    renderBenchmark(summary);
    showToast(`Benchmark complete: ${summary.throughput_records_per_second} records/s`);
  } catch (error) {
    alert(`Benchmark failed: ${error.message}`);
  }
}

async function runUploadedFiles() {
  const names = Object.keys(state.uploaded);
  if (!names.length) {
    showToast("Load one or more CSV files first.");
    return;
  }
  try {
    setLoading();
    const result = await postJson("/api/run", {
      datasets: state.uploaded,
      mappings: buildMappingsPayload(),
    });
    recordResult(result);
    switchTab("profiles");
    render();
    showToast("Uploaded files processed");
  } catch (error) {
    alert(`Pipeline failed: ${error.message}`);
  }
}

async function handleFiles(event) {
  const files = Array.from(event.target.files || []);
  if (!files.length) return;
  try {
    setPipelineStatus("ingest", "Profiling");
    const loaded = {};
    for (const file of files) {
      const text = await file.text();
      loaded[file.name] = parseCsv(text);
    }
    state.uploaded = { ...state.uploaded, ...loaded };
    const response = await postJson("/api/profile", { datasets: state.uploaded });
    state.uploadProfiles = response.profiles || [];
    initializeMappings(state.uploadProfiles);
    renderMappingReview();
    renderUploadedFiles();
    state.result = null;
    state.selectedId = null;
    el("resolveStatus").textContent = `${Object.keys(state.uploaded).length} CSV loaded`;
    el("scoreStatus").textContent = "Ready to run";
    el("exportReport").disabled = true;
    switchTab("overview");
    renderOverview();
    showToast("CSV profiled; review mappings before running");
  } catch (error) {
    alert(`CSV profiling failed: ${error.message}`);
  }
  event.target.value = "";
}

function parseCsv(text) {
  const rows = [];
  let current = "";
  let row = [];
  let inQuotes = false;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];
    if (char === '"' && inQuotes && next === '"') {
      current += '"';
      i += 1;
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === "," && !inQuotes) {
      row.push(current.trim());
      current = "";
    } else if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && next === "\n") i += 1;
      row.push(current.trim());
      if (row.some((cell) => cell.length)) rows.push(row);
      row = [];
      current = "";
    } else {
      current += char;
    }
  }
  if (current.length || row.length) {
    row.push(current.trim());
    if (row.some((cell) => cell.length)) rows.push(row);
  }
  const headers = rows.shift() || [];
  return rows.map((cells, index) => {
    const item = { source_row_id: String(index + 1) };
    headers.forEach((header, col) => {
      item[header] = cells[col] ?? "";
    });
    return item;
  });
}

function initializeMappings(profiles) {
  state.mappings = {};
  profiles.forEach((profile) => {
    state.mappings[profile.name] = {
      detected_kind: profile.detected_kind,
      fields: {},
    };
    const fieldMap = profile.mapping || {};
    Object.entries(fieldMap).forEach(([canonical, source]) => {
      state.mappings[profile.name].fields[canonical] = source;
    });
  });
}

function buildMappingsPayload() {
  const payload = {};
  Object.entries(state.mappings).forEach(([name, data]) => {
    payload[name] = {
      _kind: data.detected_kind,
      ...data.fields,
    };
  });
  return payload;
}

function renderMappingReview() {
  const container = el("mappingReview");
  const panel = el("mappingPanel");
  if (!state.uploadProfiles.length) {
    panel.hidden = true;
    container.innerHTML = "";
    return;
  }
  panel.hidden = false;
  el("mappingCount").textContent = String(state.uploadProfiles.length);

  container.innerHTML = state.uploadProfiles
    .map((profile) => {
      const kind = state.mappings[profile.name]?.detected_kind || profile.detected_kind || "generic";
      const fieldsHtml = (KIND_FIELDS[kind] || KIND_FIELDS.generic)
        .map((canonical) => {
          const current = state.mappings[profile.name]?.fields?.[canonical] || "";
          const options = profile.columns
            .map((col) => `<option value="${safe(col)}" ${col === current ? "selected" : ""}>${safe(col)}</option>`)
            .join("");
          return `
            <div class="mapping-field">
              <label for="map-${safe(profile.name)}-${canonical}">${FIELD_LABELS[canonical] || canonical}</label>
              <select id="map-${safe(profile.name)}-${canonical}" data-dataset="${safe(profile.name)}" data-field="${canonical}">
                <option value="">— ignore —</option>
                ${options}
              </select>
            </div>
          `;
        })
        .join("");
      return `
        <div class="mapping-dataset">
          <h3>${safe(profile.name)} <span class="kind-badge">${safe(kind)}</span></h3>
          <div class="mapping-fields">${fieldsHtml}</div>
        </div>
      `;
    })
    .join("");

  container.querySelectorAll("select").forEach((select) => {
    select.addEventListener("change", (e) => {
      const dataset = e.target.dataset.dataset;
      const field = e.target.dataset.field;
      if (!state.mappings[dataset]) state.mappings[dataset] = { fields: {} };
      state.mappings[dataset].fields[field] = e.target.value;
    });
  });
}

function renderUploadedFiles() {
  const container = el("uploadedFiles");
  const names = Object.keys(state.uploaded);
  if (!names.length) {
    container.innerHTML = "";
    return;
  }
  container.innerHTML = names
    .map((name) => `<span class="file-tag">${safe(name)} <small>(${state.uploaded[name].length} rows)</small></span>`)
    .join("");
}

function renderBenchmark(summary) {
  setPipelineStatus("score", "Done");
  document.querySelectorAll(".metric-card").forEach((card) => card.classList.remove("loading"));
  el("metricRecords").textContent = String(summary.canonical_record_count || 0);
  el("metricEntities").textContent = String(summary.entity_count || 0);
  el("metricFlagged").textContent = "—";
  el("metricConfidence").textContent = "—";
  el("metricTopTier").textContent = "—";
  renderTierChart([]);
  el("datasetProfiles").innerHTML = `<p class="empty-state">Benchmark mode skipped dataset profiling.</p>`;
  switchTab("overview");
}

function getProfiles() {
  return state.result?.scoring?.profiles || [];
}

function getFlaggedProfiles() {
  return state.result?.scoring?.flagged_profiles || [];
}

function getSelectedProfile() {
  return getProfiles().find((p) => p.entity_id === state.selectedId);
}

function getGraphData() {
  return state.result?.graph || { nodes: [], edges: [] };
}

function switchTab(tabId) {
  state.activeTab = tabId;
  const tabs = ["overview", "profiles", "graph"];
  tabs.forEach((id) => {
    const btn = el(`tab${id.charAt(0).toUpperCase() + id.slice(1)}`);
    const panel = el(`panel${id.charAt(0).toUpperCase() + id.slice(1)}`);
    const isActive = id === tabId;
    btn.classList.toggle("active", isActive);
    btn.setAttribute("aria-selected", String(isActive));
    btn.tabIndex = isActive ? 0 : -1;
    panel.classList.toggle("active", isActive);
    panel.hidden = !isActive;
  });
  if (tabId === "profiles") renderProfiles();
  if (tabId === "graph") renderGraph();
}

function render() {
  renderOverview();
  if (state.activeTab === "profiles") renderProfiles();
  if (state.activeTab === "graph") renderGraph();
}

function renderOverview() {
  const result = state.result;
  const profiles = getProfiles();
  const flagged = getFlaggedProfiles();

  if (!result) {
    document.querySelectorAll(".metric-card").forEach((card) => card.classList.add("loading"));
    return;
  }

  document.querySelectorAll(".metric-card").forEach((card) => card.classList.remove("loading"));
  setPipelineStatus("score", "Done");

  const canonicalCount = result.canonical_record_count ?? 0;
  const entityCount = result.resolution?.entities?.length ?? 0;
  const avgConfidence = profiles.length
    ? (profiles.reduce((sum, p) => sum + (p.scoring_confidence || 0), 0) / profiles.length).toFixed(1)
    : "—";
  const tierCounts = {};
  profiles.forEach((p) => {
    tierCounts[p.risk_tier] = (tierCounts[p.risk_tier] || 0) + 1;
  });
  const topTier = TIER_ORDER.find((t) => tierCounts[t] && tierCounts[t] > 0) || "—";

  el("metricRecords").textContent = String(canonicalCount);
  el("metricEntities").textContent = String(entityCount);
  el("metricFlagged").textContent = String(flagged.length);
  el("metricConfidence").textContent = avgConfidence === "—" ? avgConfidence : `${avgConfidence}%`;
  el("metricTopTier").textContent = TIER_LABELS[topTier] || topTier;

  renderTierChart(profiles);
  renderDatasetProfiles();
  renderUploadedFiles();
  el("exportReport").disabled = !result;
}

function renderTierChart(profiles) {
  const container = el("tierChart");
  container.innerHTML = "";
  if (!profiles.length) {
    container.innerHTML = `<p class="empty-state">No profiles to display.</p>`;
    return;
  }
  const counts = { critical: 0, high: 0, medium: 0, low: 0 };
  profiles.forEach((p) => {
    counts[p.risk_tier] = (counts[p.risk_tier] || 0) + 1;
  });
  const data = TIER_ORDER.map((tier) => ({ tier, count: counts[tier] || 0, label: TIER_LABELS[tier] })).filter(
    (d) => d.count > 0,
  );
  const total = profiles.length;

  const margin = { top: 10, right: 16, bottom: 32, left: 64 };
  const width = container.clientWidth || 400;
  const height = 220;
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;

  const svg = d3
    .select(container)
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid meet");

  const colorScale = d3.scaleOrdinal().domain(TIER_ORDER).range(["#a64b2a", "#c14528", "#c88a2a", "#d4b876", "#3d6b52"]);

  const x = d3.scaleLinear().domain([0, total]).nice().range([0, innerW]);
  const y = d3
    .scaleBand()
    .domain(data.map((d) => d.label))
    .range([0, innerH])
    .padding(0.25);

  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  g.selectAll("rect.bar")
    .data(data)
    .join("rect")
    .attr("class", "bar")
    .attr("y", (d) => y(d.label))
    .attr("height", y.bandwidth())
    .attr("x", 0)
    .attr("width", 0)
    .attr("fill", (d) => colorScale(d.tier))
    .attr("rx", 4)
    .transition()
    .duration(250)
    .attr("width", (d) => x(d.count));

  g.selectAll("text.value")
    .data(data)
    .join("text")
    .attr("class", "value")
    .attr("x", (d) => x(d.count) + 6)
    .attr("y", (d) => y(d.label) + y.bandwidth() / 2)
    .attr("dy", "0.35em")
    .style("font-family", "JetBrains Mono, monospace")
    .style("font-size", "0.8125rem")
    .style("font-weight", "600")
    .style("fill", "#1e1e24")
    .text((d) => `${d.count} (${((d.count / total) * 100).toFixed(0)}%)`);

  g.append("g").attr("transform", `translate(0,${innerH})`).call(d3.axisBottom(x).ticks(5).tickSizeOuter(0));
  g.append("g").call(d3.axisLeft(y).tickSizeOuter(0));

  g.selectAll(".domain, .tick line").style("stroke", "#dcd6cc");
  g.selectAll(".tick text").style("fill", "#5e5c58").style("font-family", "Source Sans 3, sans-serif");
}

function renderDatasetProfiles() {
  const container = el("datasetProfiles");
  const profiles = state.result?.profiles || state.uploadProfiles || [];
  if (!profiles.length) {
    container.innerHTML = `<p class="empty-state">Run an audit or upload files to see dataset profiles.</p>`;
    return;
  }
  container.innerHTML = profiles
    .map((p) => {
      const cols = p.columns?.length ?? 0;
      const mapped = Object.entries(p.mapping || {})
        .map(([k, v]) => `${FIELD_LABELS[k] || k}: ${safe(v)}`)
        .join(", ");
      return `
        <div class="dataset-profile">
          <h3>${safe(p.name)}</h3>
          <span class="hint">${safe(p.detected_kind)} · ${p.row_count ?? "?"} rows · ${cols} columns</span>
          <p class="hint">${mapped || "Auto-detected mapping"}</p>
        </div>
      `;
    })
    .join("");
}

function renderProfiles() {
  renderProfileQueue();
  renderCaseFile();
}

function renderProfileQueue() {
  const tbody = el("profileRows");
  const search = (el("profileSearch").value || "").toLowerCase();
  const activeTier = document.querySelector('.filter-chips .chip.active')?.dataset.tier || "all";
  const profiles = getFlaggedProfiles();

  const filtered = profiles.filter((p) => {
    const matchesSearch =
      !search ||
      (p.name || "").toLowerCase().includes(search) ||
      (p.entity_id || "").toLowerCase().includes(search);
    const matchesTier = activeTier === "all" || p.risk_tier === activeTier;
    return matchesSearch && matchesTier;
  });

  el("queueCount").textContent = String(filtered.length);

  tbody.innerHTML = filtered
    .map((p) => {
      const selectedClass = p.entity_id === state.selectedId ? "selected" : "";
      return `
        <tr class="${selectedClass}" data-id="${safe(p.entity_id)}">
          <td>
            <div class="queue-name">${safe(p.name || p.entity_id)}</div>
            <div class="queue-id">${safe(p.entity_id)}</div>
          </td>
          <td><span class="risk-chip ${safe(tierClass(p.risk_tier))}">${TIER_LABELS[p.risk_tier] || p.risk_tier}</span></td>
          <td class="numeric">${(p.deviation_score ?? 0).toFixed(1)}</td>
          <td class="numeric">${((p.aggregate?.lli_ratio || 0)).toFixed(1)}x</td>
        </tr>
      `;
    })
    .join("");

  tbody.querySelectorAll("tr").forEach((row) => {
    row.addEventListener("click", () => {
      state.selectedId = row.dataset.id;
      renderProfiles();
    });
  });
}

function renderCaseFile() {
  const container = el("caseFile");
  const profile = getSelectedProfile();
  if (!profile) {
    container.innerHTML = `
      <div class="case-file-empty">
        <h2>Run the pipeline to open a case file</h2>
        <p>Use <strong>Run synthetic audit</strong> or upload CSVs to begin.</p>
      </div>
    `;
    return;
  }

  const agg = profile.aggregate || {};
  const lliRatio = agg.lli_ratio || 0;
  const lliClass = lliRatio > 3 ? "danger" : lliRatio > 1.5 ? "warning" : "positive";

  container.innerHTML = `
    <header class="case-header">
      <div class="case-header-row">
        <div>
          <p class="eyebrow">Case file</p>
          <h2 class="case-name">${safe(profile.name || profile.entity_id)}</h2>
          <div class="case-meta">
            <span>ID: ${safe(profile.entity_id)}</span>
            <span>Sources: ${(profile.source_record_ids || []).length}</span>
            <span>Confidence: ${(profile.scoring_confidence ?? 0).toFixed(1)}%</span>
          </div>
        </div>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
          <span class="risk-chip ${safe(tierClass(profile.risk_tier))}">${TIER_LABELS[profile.risk_tier] || profile.risk_tier}</span>
          <button class="btn btn-secondary" id="investigateInGraph">Investigate in graph</button>
        </div>
      </div>
      <div class="score-grid">
        <div class="score-item">
          <span class="score-label">Deviation score</span>
          <span class="score-value ${safe(tierClass(profile.risk_tier))}">${(profile.deviation_score ?? 0).toFixed(1)}</span>
        </div>
        <div class="score-item">
          <span class="score-label">Direct risk</span>
          <span class="score-value">${(profile.direct_score ?? 0).toFixed(1)}</span>
        </div>
        <div class="score-item">
          <span class="score-label">LLI ratio</span>
          <span class="score-value ${lliClass}">${lliRatio.toFixed(1)}x</span>
        </div>
        <div class="score-item">
          <span class="score-label">Asset events</span>
          <span class="score-value">${Math.round(agg.asset_event_count || 0)}</span>
        </div>
        <div class="score-item">
          <span class="score-label">Vehicle value</span>
          <span class="score-value">${formatPKR(agg.estimated_vehicle_value || 0)}</span>
        </div>
        <div class="score-item">
          <span class="score-label">Property value</span>
          <span class="score-value">${formatPKR(agg.estimated_property_value || 0)}</span>
        </div>
      </div>
    </header>

    <section class="case-section">
      <div class="case-section-header"><h3>Direct reasons</h3></div>
      <div class="case-section-body">
        <ul class="reasons-list">
          ${(profile.direct_reasons || []).map((r) => `<li>${safe(r)}</li>`).join("") || "<li>No direct reasons recorded.</li>"}
        </ul>
      </div>
    </section>

    <section class="case-section">
      <div class="case-section-header"><h3>Score breakdown</h3></div>
      <div class="case-section-body chart-container" id="scoreComponentsChart"></div>
    </section>

    <section class="case-section">
      <div class="case-section-header"><h3>Asset timeline</h3></div>
      <div class="case-section-body chart-container" id="assetTimelineChart"></div>
    </section>

    <section class="case-section">
      <div class="case-section-header"><h3>Evidence signals</h3></div>
      <div class="case-section-body">
        <div class="overview-grid" style="grid-template-columns:repeat(auto-fit,minmax(280px,1fr));">
          <div>
            <p class="eyebrow">Source mix</p>
            <div id="sourceMixChart" class="chart-container small"></div>
          </div>
          <div>
            <p class="eyebrow">Benford first digits</p>
            <div id="benfordChart" class="chart-container small"></div>
          </div>
          <div>
            <p class="eyebrow">Geography</p>
            <div id="geoChips" class="geo-chips"></div>
          </div>
        </div>
      </div>
    </section>

    <section class="case-section">
      <div class="case-section-header"><h3>Ego network</h3></div>
      <div class="case-section-body chart-container" id="egoGraphChart"></div>
    </section>

    <section class="case-section">
      <div class="case-section-header"><h3>Source rows</h3></div>
      <div class="case-section-body">
        <div class="source-rows" id="caseSourceRows"></div>
      </div>
    </section>
  `;

  el("investigateInGraph").addEventListener("click", () => {
    switchTab("graph");
    state.graph.selectedNodeId = profile.entity_id;
    renderGraph();
  });

  renderScoreComponentsChart(profile);
  renderAssetTimelineChart(profile);
  renderSourceMixChart(profile);
  renderBenfordChart(profile);
  renderGeoChips(profile);
  renderEgoGraph(profile);
  renderCaseSourceRows(profile);
}

function renderScoreComponentsChart(profile) {
  const container = el("scoreComponentsChart");
  const components = profile.score_components || {};
  const data = Object.entries(components)
    .filter(([, value]) => value > 0)
    .map(([key, value]) => ({ key: key.replace(/_/g, " "), value }))
    .sort((a, b) => b.value - a.value);

  if (!data.length) {
    container.innerHTML = `<p class="empty-state">No score components available.</p>`;
    return;
  }

  drawHorizontalBarChart(container, data, { valueFormat: (d) => d.toFixed(1), color: "#1a2b4a" });
}

function renderAssetTimelineChart(profile) {
  const container = el("assetTimelineChart");
  const records = profile.source_rows || [];
  const events = [];
  records.forEach((row) => {
    const raw = row.raw || {};
    const type = row.record_type;
    if (type === "property" && raw.transfer_date) {
      const year = parseInt(String(raw.transfer_date).slice(0, 4), 10);
      if (year) events.push({ year, label: "Property", value: Number(raw.property_value || 0) });
    }
    if (type === "vehicle" && raw.registration_year) {
      const year = Number(raw.registration_year);
      if (year) events.push({ year, label: "Vehicle", value: Number(raw.engine_capacity_cc || 0) * 1000 });
    }
  });

  if (!events.length) {
    container.innerHTML = `<p class="empty-state">No dated asset events for this entity.</p>`;
    return;
  }

  drawTimelineChart(container, events);
}

function renderSourceMixChart(profile) {
  const container = el("sourceMixChart");
  const records = profile.source_rows || [];
  const counts = {};
  records.forEach((r) => {
    counts[r.record_type] = (counts[r.record_type] || 0) + 1;
  });
  const data = Object.entries(counts).map(([type, count]) => ({ type, count }));
  if (!data.length) {
    container.innerHTML = `<p class="empty-state">No source rows.</p>`;
    return;
  }
  drawDonutChart(container, data);
}

function renderBenfordChart(profile) {
  const container = el("benfordChart");
  const records = profile.source_rows || [];
  const values = records
    .filter((r) => r.record_type === "tax")
    .flatMap((r) => [r.raw?.declared_income_pkr, r.raw?.tax_paid_pkr])
    .filter(Boolean);

  if (values.length < 10) {
    container.innerHTML = `<p class="empty-state">Not enough numeric records for Benford analysis.</p>`;
    return;
  }

  const digitCounts = {};
  for (let d = 1; d <= 9; d += 1) digitCounts[d] = 0;
  values.forEach((v) => {
    const text = String(v).replace(/[^0-9]/g, "");
    for (const ch of text) {
      if (ch !== "0") {
        digitCounts[ch] = (digitCounts[ch] || 0) + 1;
        break;
      }
    }
  });
  const total = Object.values(digitCounts).reduce((a, b) => a + b, 0);
  if (total < 5) {
    container.innerHTML = `<p class="empty-state">Not enough first digits.</p>`;
    return;
  }
  const expected = [0.301, 0.176, 0.125, 0.097, 0.079, 0.067, 0.058, 0.051, 0.046];
  const data = Array.from({ length: 9 }, (_, i) => ({
    digit: String(i + 1),
    observed: total ? digitCounts[String(i + 1)] / total : 0,
    expected: expected[i],
  }));
  drawGroupedBarChart(container, data);
}

function renderGeoChips(profile) {
  const container = el("geoChips");
  const records = profile.source_rows || [];
  const provinces = new Set();
  const districts = new Set();
  records.forEach((r) => {
    const raw = r.raw || {};
    if (raw.nic_province) provinces.add(raw.nic_province);
    if (raw.nic_district) districts.add(raw.nic_district);
  });
  if (!provinces.size && !districts.size) {
    container.innerHTML = `<p class="empty-state">No geocoded CNIC data.</p>`;
    return;
  }
  const chips = [
    ...Array.from(provinces).map((p) => `<span class="geo-chip">${safe(p)}</span>`),
    ...Array.from(districts).map((d) => `<span class="geo-chip">${safe(d)}</span>`),
  ];
  container.innerHTML = chips.join("");
}

function renderEgoGraph(profile) {
  const container = el("egoGraphChart");
  const graph = getGraphData();
  if (!graph.nodes.length) {
    container.innerHTML = `<p class="empty-state">No graph data.</p>`;
    return;
  }
  const nodeIds = new Set([profile.entity_id]);
  graph.edges.forEach((e) => {
    if (e.source === profile.entity_id || e.target === profile.entity_id) {
      nodeIds.add(typeof e.source === "object" ? e.source.id : e.source);
      nodeIds.add(typeof e.target === "object" ? e.target.id : e.target);
    }
  });
  const egoNodes = graph.nodes.filter((n) => nodeIds.has(n.id));
  const egoEdges = graph.edges.filter((e) => {
    const s = typeof e.source === "object" ? e.source.id : e.source;
    const t = typeof e.target === "object" ? e.target.id : e.target;
    return s === profile.entity_id || t === profile.entity_id;
  });
  drawForceGraph(container, { nodes: egoNodes, edges: egoEdges }, { height: 260, enableZoom: false });
}

function renderCaseSourceRows(profile) {
  const container = el("caseSourceRows");
  const rows = profile.source_rows || [];
  if (!rows.length) {
    container.innerHTML = `<p class="empty-state">No source rows.</p>`;
    return;
  }
  container.innerHTML = rows
    .map((row) => {
      const raw = row.raw || {};
      const fields = Object.entries(raw)
        .filter(([k]) => !k.startsWith("_"))
        .map(([k, v]) => `<div><dt>${safe(k)}</dt><dd>${safe(v)}</dd></div>`)
        .join("");
      return `
        <article class="source-row">
          <header>
            <span>${safe(row.dataset)}</span>
            <span>${safe(row.record_type)}</span>
            <span>${safe(row.row_id)}</span>
          </header>
          <dl>${fields}</dl>
        </article>
      `;
    })
    .join("");
}

/* D3 chart helpers */
function getChartSize(container) {
  const width = container.clientWidth || 400;
  return { width, height: container.clientHeight || 240 };
}

function drawHorizontalBarChart(container, data, options = {}) {
  container.innerHTML = "";
  const { width, height } = getChartSize(container);
  const margin = { top: 8, right: 56, bottom: 24, left: 120 };
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;

  const svg = d3.select(container).append("svg").attr("width", width).attr("height", height);
  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  const x = d3.scaleLinear().domain([0, d3.max(data, (d) => d.value) || 1]).nice().range([0, innerW]);
  const y = d3
    .scaleBand()
    .domain(data.map((d) => d.key))
    .range([0, innerH])
    .padding(0.2);

  g.selectAll("rect")
    .data(data)
    .join("rect")
    .attr("y", (d) => y(d.key))
    .attr("height", y.bandwidth())
    .attr("x", 0)
    .attr("width", 0)
    .attr("fill", options.color || "#1a2b4a")
    .attr("rx", 4)
    .transition()
    .duration(250)
    .attr("width", (d) => x(d.value));

  g.selectAll("text.value")
    .data(data)
    .join("text")
    .attr("x", (d) => x(d.value) + 6)
    .attr("y", (d) => y(d.key) + y.bandwidth() / 2)
    .attr("dy", "0.35em")
    .style("font-family", "JetBrains Mono, monospace")
    .style("font-size", "0.75rem")
    .style("fill", "#1e1e24")
    .text((d) => (options.valueFormat ? options.valueFormat(d.value) : d.value));

  g.append("g").attr("transform", `translate(0,${innerH})`).call(d3.axisBottom(x).ticks(4).tickSizeOuter(0));
  g.append("g").call(d3.axisLeft(y).tickSizeOuter(0));

  g.selectAll(".domain, .tick line").style("stroke", "#dcd6cc");
  g.selectAll(".tick text").style("fill", "#5e5c58").style("font-family", "Source Sans 3, sans-serif");
}

function drawTimelineChart(container, events) {
  container.innerHTML = "";
  const { width, height } = getChartSize(container);
  const margin = { top: 16, right: 24, bottom: 32, left: 56 };
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;

  const svg = d3.select(container).append("svg").attr("width", width).attr("height", height);
  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  const years = events.map((e) => e.year);
  const x = d3.scaleLinear().domain(d3.extent(years)).nice().range([0, innerW]);
  const y = d3.scaleLinear().domain([0, d3.max(events, (d) => d.value) || 1]).nice().range([innerH, 0]);
  const color = d3
    .scaleOrdinal()
    .domain(["Property", "Vehicle"])
    .range(["#d4b876", "#3d6b52"]);

  g.append("g").attr("transform", `translate(0,${innerH})`).call(d3.axisBottom(x).tickFormat(d3.format("d")));
  g.append("g").call(d3.axisLeft(y).ticks(5).tickFormat((d) => formatNumber(d)));

  g.selectAll(".domain, .tick line").style("stroke", "#dcd6cc");
  g.selectAll(".tick text").style("fill", "#5e5c58").style("font-family", "Source Sans 3, sans-serif");

  g.selectAll("circle")
    .data(events)
    .join("circle")
    .attr("cx", (d) => x(d.year))
    .attr("cy", (d) => y(d.value))
    .attr("r", 6)
    .attr("fill", (d) => color(d.label))
    .attr("stroke", "#fdfcf9")
    .attr("stroke-width", 2);

  const line = d3
    .line()
    .x((d) => x(d.year))
    .y((d) => y(d.value))
    .curve(d3.curveMonotoneX);

  g.append("path")
    .datum(events.sort((a, b) => a.year - b.year))
    .attr("fill", "none")
    .attr("stroke", "#1a2b4a")
    .attr("stroke-width", 2)
    .attr("d", line);

  const legend = svg.append("g").attr("transform", `translate(${margin.left}, 8)`);
  color.domain().forEach((label, i) => {
    const item = legend.append("g").attr("transform", `translate(${i * 90}, 0)`);
    item.append("circle").attr("r", 5).attr("fill", color(label));
    item.append("text").attr("x", 12).attr("y", 0).attr("dy", "0.35em").style("font-size", "0.75rem").text(label);
  });
}

function drawDonutChart(container, data) {
  container.innerHTML = "";
  const { width, height } = getChartSize(container);
  const radius = Math.min(width, height) / 2 - 16;
  const svg = d3.select(container).append("svg").attr("width", width).attr("height", height);
  const g = svg.append("g").attr("transform", `translate(${width / 2},${height / 2})`);

  const color = d3.scaleOrdinal().domain(data.map((d) => d.type)).range(["#1a2b4a", "#3d6b52", "#d4b876", "#c88a2a", "#5e5c58"]);
  const pie = d3.pie().value((d) => d.count).sort(null);
  const arc = d3.arc().innerRadius(radius * 0.55).outerRadius(radius);

  g.selectAll("path")
    .data(pie(data))
    .join("path")
    .attr("d", arc)
    .attr("fill", (d) => color(d.data.type))
    .attr("stroke", "#fdfcf9")
    .attr("stroke-width", 2);

  const total = data.reduce((sum, d) => sum + d.count, 0);
  g.append("text").attr("text-anchor", "middle").attr("dy", "0.35em").style("font-family", "JetBrains Mono, monospace").style("font-weight", "600").text(total);

  const legend = svg.append("g").attr("transform", `translate(16, ${height - 20})`);
  data.forEach((d, i) => {
    const item = legend.append("g").attr("transform", `translate(${i * 80}, 0)`);
    item.append("rect").attr("width", 10).attr("height", 10).attr("fill", color(d.type));
    item.append("text").attr("x", 16).attr("y", 9).style("font-size", "0.75rem").text(d.type);
  });
}

function drawGroupedBarChart(container, data) {
  container.innerHTML = "";
  const { width, height } = getChartSize(container);
  const margin = { top: 16, right: 16, bottom: 32, left: 32 };
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;

  const svg = d3.select(container).append("svg").attr("width", width).attr("height", height);
  const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

  const x0 = d3.scaleBand().domain(data.map((d) => d.digit)).range([0, innerW]).padding(0.2);
  const x1 = d3.scaleBand().domain(["observed", "expected"]).range([0, x0.bandwidth()]).padding(0.1);
  const y = d3.scaleLinear().domain([0, d3.max(data, (d) => Math.max(d.observed, d.expected)) || 1]).nice().range([innerH, 0]);
  const color = d3.scaleOrdinal().domain(["observed", "expected"]).range(["#1a2b4a", "#d4b876"]);

  g.append("g").attr("transform", `translate(0,${innerH})`).call(d3.axisBottom(x0));
  g.append("g").call(d3.axisLeft(y).ticks(5).tickFormat((d) => `${(d * 100).toFixed(0)}%`));

  g.selectAll(".domain, .tick line").style("stroke", "#dcd6cc");
  g.selectAll(".tick text").style("fill", "#5e5c58").style("font-family", "Source Sans 3, sans-serif");

  const groups = g.selectAll("g.digit-group").data(data).join("g").attr("class", "digit-group").attr("transform", (d) => `translate(${x0(d.digit)},0)`);

  groups
    .selectAll("rect")
    .data((d) => [
      { key: "observed", value: d.observed },
      { key: "expected", value: d.expected },
    ])
    .join("rect")
    .attr("x", (d) => x1(d.key))
    .attr("y", (d) => y(d.value))
    .attr("width", x1.bandwidth())
    .attr("height", (d) => innerH - y(d.value))
    .attr("fill", (d) => color(d.key))
    .attr("rx", 2);

  const legend = svg.append("g").attr("transform", `translate(${width - 110}, 16)`);
  ["observed", "expected"].forEach((key, i) => {
    const item = legend.append("g").attr("transform", `translate(0, ${i * 18})`);
    item.append("rect").attr("width", 10).attr("height", 10).attr("fill", color(key));
    item.append("text").attr("x", 16).attr("y", 9).style("font-size", "0.75rem").text(key);
  });
}

/* Graph investigation */
function renderGraph() {
  const container = el("graphCanvas");
  container.innerHTML = "";
  const graph = getGraphData();
  if (!graph.nodes.length) {
    container.innerHTML = `<p class="empty-state" style="padding:48px;">Run the pipeline to load the network.</p>`;
    return;
  }
  renderGraphLegends();
  drawForceGraph(container, graph, { height: container.clientHeight || 600, enableZoom: true });
  renderGraphDetail();
}

function renderGraphLegends() {
  const nodeLegend = el("nodeLegend");
  const edgeLegend = el("edgeLegend");

  nodeLegend.innerHTML = NODE_TYPES.map(
    (t) => `
    <label class="legend-item">
      <input type="checkbox" value="${safe(t.key)}" checked />
      <span class="legend-swatch ${safe(t.shape)}" style="background:${t.color}"></span>
      <span>${safe(t.label)}</span>
    </label>
  `
  ).join("");

  edgeLegend.innerHTML = EDGE_TYPES.map(
    (t) => `
    <label class="legend-item">
      <input type="checkbox" value="${safe(t.key)}" checked />
      <svg width="20" height="10" style="flex-shrink:0">
        <line x1="0" y1="5" x2="18" y2="5" stroke="${t.color}" stroke-width="2" stroke-dasharray="${t.dash}" />
      </svg>
      <span>${safe(t.label)}</span>
    </label>
  `
  ).join("");

  nodeLegend.querySelectorAll("input").forEach((input) => {
    input.addEventListener("change", () => {
      state.graph.visibleNodeTypes = new Set(
        Array.from(nodeLegend.querySelectorAll("input:checked")).map((i) => i.value),
      );
      renderGraph();
    });
  });

  edgeLegend.querySelectorAll("input").forEach((input) => {
    input.addEventListener("change", () => {
      state.graph.visibleEdgeTypes = new Set(
        Array.from(edgeLegend.querySelectorAll("input:checked")).map((i) => i.value),
      );
      renderGraph();
    });
  });
}

function renderGraphDetail() {
  const container = el("graphDetail");
  const graph = getGraphData();
  const node = graph.nodes.find((n) => n.id === state.graph.selectedNodeId);
  if (!node) {
    container.innerHTML = `
      <div class="case-file-empty">
        <h2>Select a node</h2>
        <p>Click any node in the graph to inspect its evidence and relationships.</p>
      </div>
    `;
    return;
  }

  const edges = graph.edges.filter((e) => {
    const s = typeof e.source === "object" ? e.source.id : e.source;
    const t = typeof e.target === "object" ? e.target.id : e.target;
    return s === node.id || t === node.id;
  });

  const neighborIds = new Set();
  edges.forEach((e) => {
    const s = typeof e.source === "object" ? e.source.id : e.source;
    const t = typeof e.target === "object" ? e.target.id : e.target;
    neighborIds.add(s === node.id ? t : s);
  });

  const neighbors = graph.nodes.filter((n) => neighborIds.has(n.id));
  const profile = getProfiles().find((p) => p.entity_id === node.id);

  container.innerHTML = `
    <div class="panel-head">
      <div>
        <p class="eyebrow">${safe(node.type || "Node")}</p>
        <h2>${safe(node.label || node.id)}</h2>
      </div>
    </div>
    <div style="padding:16px 24px;display:grid;gap:16px;">
      ${profile ? `
        <div class="score-grid" style="grid-template-columns:repeat(2,1fr);">
          <div class="score-item"><span class="score-label">Score</span><span class="score-value">${(profile.deviation_score || 0).toFixed(1)}</span></div>
          <div class="score-item"><span class="score-label">LLI</span><span class="score-value">${(profile.aggregate?.lli_ratio || 0).toFixed(1)}x</span></div>
        </div>
      ` : ""}
      <div>
        <p class="eyebrow">Properties</p>
        <dl class="source-row">
          ${Object.entries(node.meta || {}).map(([k, v]) => {
            let display = v;
            if (v === null || v === undefined) display = "";
            else if (typeof v === "object") display = JSON.stringify(v);
            return `<div><dt>${safe(k)}</dt><dd>${safe(display)}</dd></div>`;
          }).join("")}
        </dl>
      </div>
      <div>
        <p class="eyebrow">Connections (${neighbors.length})</p>
        <ul class="reasons-list">
          ${neighbors.map((n) => `<li>${safe(n.label || n.id)} <span style="color:var(--ink-muted)">(${safe(n.type || "unknown")})</span></li>`).join("")}
        </ul>
      </div>
      ${profile ? `<button class="btn btn-secondary" id="openInProfiles">Open case file</button>` : ""}
    </div>
  `;

  const openBtn = container.querySelector("#openInProfiles");
  if (openBtn) {
    openBtn.addEventListener("click", () => {
      state.selectedId = node.id;
      switchTab("profiles");
    });
  }
}

function drawForceGraph(container, graphData, options = {}) {
  const { width, height } = getChartSize(container);
  const heightPx = options.height || height;

  const filteredNodes = graphData.nodes.filter((n) => state.graph.visibleNodeTypes.has(n.type));
  const nodeById = new Map(filteredNodes.map((n) => [n.id, n]));
  const filteredEdges = graphData.edges.filter((e) => {
    const s = typeof e.source === "object" ? e.source.id : e.source;
    const t = typeof e.target === "object" ? e.target.id : e.target;
    return state.graph.visibleEdgeTypes.has(e.relation) && nodeById.has(s) && nodeById.has(t);
  });

  if (!filteredNodes.length) {
    container.innerHTML = `<p class="empty-state" style="padding:48px;">No visible nodes with current filters.</p>`;
    return;
  }

  const svg = d3
    .select(container)
    .append("svg")
    .attr("width", width)
    .attr("height", heightPx)
    .attr("viewBox", [0, 0, width, heightPx]);

  const tooltip = d3.select(container).append("div").attr("class", "graph-tooltip");

  const g = svg.append("g");
  const zoom = d3
    .zoom()
    .scaleExtent([0.1, 4])
    .on("zoom", (event) => {
      g.attr("transform", event.transform);
      state.graph.transform = event.transform;
    });

  if (options.enableZoom !== false) {
    svg.call(zoom);
    if (state.graph.transform) {
      svg.call(zoom.transform, state.graph.transform);
    }
  }

  svg
    .append("defs")
    .selectAll("marker")
    .data(EDGE_TYPES)
    .join("marker")
    .attr("id", (d) => `arrow-${d.key}`)
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 20)
    .attr("refY", 0)
    .attr("markerWidth", 6)
    .attr("markerHeight", 6)
    .attr("orient", "auto")
    .append("path")
    .attr("d", "M0,-5L10,0L0,5")
    .attr("fill", (d) => d.color);

  const simulation = d3
    .forceSimulation(filteredNodes)
    .force(
      "link",
      d3
        .forceLink(filteredEdges)
        .id((d) => d.id)
        .distance((d) => (d.relation === "SAME_ADDRESS_AS" || d.relation === "SHARES_PHONE_WITH" ? 70 : 100)),
    )
    .force("charge", d3.forceManyBody().strength(-220))
    .force("center", d3.forceCenter(width / 2, heightPx / 2))
    .force("collide", d3.forceCollide().radius((d) => nodeRadius(d) + 6));

  state.graph.simulation = simulation;
  state.graph.svg = svg;
  state.graph.zoom = zoom;

  if (options.enableZoom !== false) {
    el("graphStats").textContent = `${filteredNodes.length} nodes · ${filteredEdges.length} edges`;
  }

  const link = g
    .append("g")
    .attr("class", "links")
    .selectAll("line")
    .data(filteredEdges)
    .join("line")
    .attr("class", "graph-link")
    .attr("stroke", (d) => EDGE_TYPES.find((t) => t.key === d.relation)?.color || "#5e5c58")
    .attr("stroke-dasharray", (d) => EDGE_TYPES.find((t) => t.key === d.relation)?.dash || "0")
    .attr("marker-end", (d) => `url(#arrow-${d.relation})`)
    .attr("stroke-width", (d) => (d.confidence ? Math.max(1.5, d.confidence * 2) : 1.5));

  const node = g
    .append("g")
    .attr("class", "nodes")
    .selectAll("path")
    .data(filteredNodes)
    .join("path")
    .attr("class", (d) => `graph-node ${d.id === state.graph.selectedNodeId ? "selected" : ""}`)
    .attr("d", (d) => nodeShapePath(d))
    .attr("fill", (d) => NODE_TYPES.find((t) => t.key === d.type)?.color || "#5e5c58")
    .attr("transform", (d) => `translate(${d.x || width / 2},${d.y || heightPx / 2})`)
    .call(
      d3
        .drag()
        .on("start", (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on("drag", (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on("end", (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        }),
    );

  const label = g
    .append("g")
    .attr("class", "labels")
    .selectAll("text")
    .data(filteredNodes)
    .join("text")
    .attr("class", "graph-label")
    .attr("text-anchor", "middle")
    .attr("dy", (d) => -nodeRadius(d) - 6)
    .text((d) => (d.label || d.id).slice(0, 22));

  node
    .on("mouseenter", (event, d) => {
      tooltip.html(`<strong>${safe(d.label || d.id)}</strong><br>${safe(d.type || "Node")}`).classed("visible", true);
      highlightEgo(d.id, node, link, label);
    })
    .on("mousemove", (event) => {
      tooltip.style("left", `${event.offsetX + 12}px`).style("top", `${event.offsetY + 12}px`);
    })
    .on("mouseleave", () => {
      tooltip.classed("visible", false);
      clearHighlight(node, link, label);
    })
    .on("click", (_event, d) => {
      state.graph.selectedNodeId = d.id;
      renderGraphDetail();
      node.attr("class", (n) => `graph-node ${n.id === d.id ? "selected" : ""}`);
    });

  simulation.on("tick", () => {
    link
      .attr("x1", (d) => d.source.x)
      .attr("y1", (d) => d.source.y)
      .attr("x2", (d) => d.target.x)
      .attr("y2", (d) => d.target.y);

    node.attr("transform", (d) => `translate(${d.x},${d.y})`);
    label.attr("x", (d) => d.x).attr("y", (d) => d.y);
  });

  if (state.graph.selectedNodeId) {
    const selected = filteredNodes.find((n) => n.id === state.graph.selectedNodeId);
    if (selected) highlightEgo(selected.id, node, link, label);
  }
}

function nodeRadius(d) {
  if (d.type === "Person") return 14;
  if (d.type === "AddressHub" || d.type === "PhoneHub") return 8;
  return 10;
}

function nodeShapePath(d) {
  const r = nodeRadius(d);
  const type = NODE_TYPES.find((t) => t.key === d.type)?.shape || "circle";
  switch (type) {
    case "square":
      return `M${-r},${-r} h${r * 2} v${r * 2} h${-r * 2} z`;
    case "diamond":
      return `M0,${-r} L${r},0 L0,${r} L${-r},0 z`;
    case "triangle":
      return `M0,${-r} L${r},${r} L${-r},${r} z`;
    case "hexagon":
      return d3
        .symbol()
        .type(d3.symbolWye)
        .size(r * r * 4)();
    default:
      return d3.symbol().type(d3.symbolCircle).size(r * r * 4)();
  }
}

function highlightEgo(centerId, node, link, label) {
  const neighborIds = new Set([centerId]);
  link.each(function (d) {
    const s = typeof d.source === "object" ? d.source.id : d.source;
    const t = typeof d.target === "object" ? d.target.id : d.target;
    if (s === centerId || t === centerId) {
      neighborIds.add(s);
      neighborIds.add(t);
    }
  });

  node.classed("dimmed", (d) => !neighborIds.has(d.id));
  link.classed("dimmed", (d) => {
    const s = typeof d.source === "object" ? d.source.id : d.source;
    const t = typeof d.target === "object" ? d.target.id : d.target;
    return s !== centerId && t !== centerId;
  });
  label.classed("dimmed", (d) => !neighborIds.has(d.id));
}

function clearHighlight(node, link, label) {
  node.classed("dimmed", false);
  link.classed("dimmed", false);
  label.classed("dimmed", false);
}

/* Event wiring */
function init() {
  el("runDemo").addEventListener("click", runDemo);
  el("runBenchmark").addEventListener("click", runBenchmark);
  el("runFiles").addEventListener("click", runUploadedFiles);
  el("fileInput").addEventListener("change", handleFiles);
  el("exportReport").addEventListener("click", () => {
    if (!state.result) return;
    const blob = new Blob([JSON.stringify(state.result, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `taxnet-report-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  });

  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.id.replace("tab", "").toLowerCase()));
  });

  document.querySelectorAll(".filter-chips .chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".filter-chips .chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      renderProfileQueue();
    });
  });

  el("profileSearch").addEventListener("input", renderProfileQueue);

  el("resetGraph").addEventListener("click", () => {
    state.graph.selectedNodeId = null;
    renderGraph();
  });

  el("fitGraph").addEventListener("click", () => {
    if (state.graph.svg && state.graph.zoom) {
      state.graph.svg.transition().duration(500).call(state.graph.zoom.transform, d3.zoomIdentity);
    }
  });

  window.addEventListener("resize", () => {
    if (state.activeTab === "overview") renderTierChart(getProfiles());
    if (state.activeTab === "profiles") renderProfiles();
    if (state.activeTab === "graph") renderGraph();
  });

  renderOverview();
}

init();
