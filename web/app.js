const state = {
  result: null,
  selectedId: null,
  uploaded: {},
  uploadProfiles: [],
  mappings: {},
  reportUrl: null,
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

const KIND_OPTIONS = ["tax", "vehicle", "utility", "property", "generic"];
const el = (id) => document.getElementById(id);
const svgNS = "http://www.w3.org/2000/svg";

function safe(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
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

function setLoading(label) {
  el("erStatus").textContent = label;
  el("graphStatus").textContent = "Waiting";
  el("scoreStatus").textContent = "Waiting";
  el("exportReport").disabled = true;
}

async function runDemo() {
  try {
    setLoading("Running");
    el("mappingPanel").hidden = true;
    const result = await getJson("/api/demo");
    state.result = result;
    state.selectedId = result.scoring.flagged_profiles[0]?.entity_id || result.scoring.profiles[0]?.entity_id || null;
    render();
  } catch (error) {
    alert(`Pipeline failed: ${error.message}`);
  }
}

async function runBenchmark() {
  const requested = Number(el("benchmarkCitizens").value || 500);
  const citizens = Math.max(1, Math.min(5000, Number.isFinite(requested) ? requested : 500));
  el("benchmarkCitizens").value = String(citizens);
  try {
    setLoading("Benchmarking");
    el("mappingPanel").hidden = true;
    const summary = await getJson(`/api/benchmark?citizens=${encodeURIComponent(citizens)}`);
    renderBenchmark(summary);
  } catch (error) {
    alert(`Benchmark failed: ${error.message}`);
  }
}

async function runUploadedFiles() {
  const names = Object.keys(state.uploaded);
  if (!names.length) {
    alert("Load one or more CSV files first.");
    return;
  }
  try {
    setLoading("Running");
    const result = await postJson("/api/run", {
      datasets: state.uploaded,
      mappings: buildMappingsPayload(),
    });
    state.result = result;
    state.selectedId = result.scoring.flagged_profiles[0]?.entity_id || result.scoring.profiles[0]?.entity_id || null;
    render();
  } catch (error) {
    alert(`Pipeline failed: ${error.message}`);
  }
}

async function handleFiles(event) {
  const files = Array.from(event.target.files || []);
  if (!files.length) return;

  try {
    setLoading("Profiling");
    const loaded = {};
    for (const file of files) {
      const text = await file.text();
      loaded[file.name] = parseCsv(text);
    }
    state.uploaded = loaded;
    const response = await postJson("/api/profile", { datasets: state.uploaded });
    state.uploadProfiles = response.profiles || [];
    initializeMappings(state.uploadProfiles);
    renderMappingReview();
    state.result = null;
    state.selectedId = null;
    el("erStatus").textContent = "Review mappings";
    el("graphStatus").textContent = `${files.length} CSV loaded`;
    el("scoreStatus").textContent = "Ready to run";
    el("exportReport").disabled = true;
  } catch (error) {
    alert(`CSV profiling failed: ${error.message}`);
  }
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
      _kind: profile.detected_kind || "generic",
      ...(profile.mapping || {}),
    };
  });
}

function buildMappingsPayload() {
  const payload = {};
  state.uploadProfiles.forEach((profile) => {
    payload[profile.name] = { ...(state.mappings[profile.name] || {}) };
  });
  return payload;
}

function renderMappingReview() {
  const panel = el("mappingPanel");
  const profiles = state.uploadProfiles;
  panel.hidden = !profiles.length;
  el("mappingCount").textContent = String(profiles.length);
  el("mappingReview").innerHTML = profiles.map((profile, index) => renderMappingDataset(profile, index)).join("");

  document.querySelectorAll("[data-kind-index]").forEach((select) => {
    select.addEventListener("change", () => {
      const profile = state.uploadProfiles[Number(select.dataset.kindIndex)];
      state.mappings[profile.name] = {
        ...(state.mappings[profile.name] || {}),
        _kind: select.value,
      };
      renderMappingReview();
    });
  });

  document.querySelectorAll("[data-map-index]").forEach((select) => {
    select.addEventListener("change", () => {
      const profile = state.uploadProfiles[Number(select.dataset.mapIndex)];
      const mapping = state.mappings[profile.name] || { _kind: profile.detected_kind || "generic" };
      mapping[select.dataset.mapField] = select.value;
      state.mappings[profile.name] = mapping;
    });
  });
}

function renderMappingDataset(profile, index) {
  const mapping = state.mappings[profile.name] || { _kind: profile.detected_kind || "generic" };
  const kind = mapping._kind || profile.detected_kind || "generic";
  const fields = KIND_FIELDS[kind] || KIND_FIELDS.generic;
  const fieldRows = fields
    .map(
      (field) => `
        <label class="mapping-field">
          <span>${safe(FIELD_LABELS[field] || field)}</span>
          <select data-map-index="${index}" data-map-field="${safe(field)}">
            ${columnOptions(profile.columns, mapping[field])}
          </select>
        </label>
      `,
    )
    .join("");

  return `
    <article class="mapping-dataset">
      <div class="mapping-summary">
        <div>
          <strong>${safe(profile.name)}</strong>
          <small>${safe(profile.row_count)} rows | detected as ${safe(profile.detected_kind)}</small>
        </div>
        <label>
          <span>Dataset type</span>
          <select data-kind-index="${index}">
            ${KIND_OPTIONS.map((option) => `<option value="${option}" ${option === kind ? "selected" : ""}>${option}</option>`).join("")}
          </select>
        </label>
      </div>
      <div class="mapping-fields">${fieldRows}</div>
    </article>
  `;
}

function columnOptions(columns, selected) {
  const options = [`<option value="">Not mapped</option>`];
  columns.forEach((column) => {
    options.push(`<option value="${safe(column)}" ${column === selected ? "selected" : ""}>${safe(column)}</option>`);
  });
  return options.join("");
}

function render() {
  const result = state.result;
  if (!result) return;
  el("erStatus").textContent = "Unified IDs";
  el("graphStatus").textContent = `${result.graph.summary.nodes} nodes`;
  el("scoreStatus").textContent = `${result.scoring.summary.flagged} flagged`;
  el("exportReport").disabled = false;
  renderMetrics(result);
  renderProfiles(result);
  renderSelected(result);
  renderProfilesMeta(result.profiles);
}

function renderBenchmark(summary) {
  state.result = null;
  state.selectedId = null;
  el("erStatus").textContent = `${summary.entity_count} entities`;
  el("graphStatus").textContent = `${summary.graph_summary.nodes} nodes`;
  el("scoreStatus").textContent = `${summary.throughput_records_per_second} rec/s`;
  el("exportReport").disabled = true;
  el("metrics").innerHTML = [
    metric("Synthetic citizens", summary.citizens),
    metric("Canonical records", summary.canonical_record_count),
    metric("Unified entities", summary.entity_count),
    metric("Candidate pairs", summary.resolution_runtime_stats.candidate_pairs_after_blocking),
    metric("Blocking reduction", `${summary.resolution_runtime_stats.blocking_reduction_pct}%`),
    metric("Throughput", `${summary.throughput_records_per_second} rec/s`),
  ].join("");
  el("queueCount").textContent = "0";
  el("profileRows").innerHTML = '<tr><td colspan="3">Benchmark summary only; no profile payload returned.</td></tr>';
  el("graphTitle").textContent = "Benchmark summary";
  el("selectedScore").textContent = String(summary.scoring_summary.flagged);
  el("graphSvg").replaceChildren();
  el("detailTitle").textContent = "Benchmark complete";
  el("riskLevel").textContent = "summary";
  el("riskLevel").className = "risk low";
  el("explanation").textContent = `Processed ${summary.canonical_record_count} canonical records for ${summary.citizens} synthetic citizens in ${summary.timing_ms.total} ms. Ground-truth pairwise metrics are skipped in benchmark mode to avoid quadratic validation cost.`;
  el("scoreBreakdown").innerHTML = Object.entries(summary.timing_ms)
    .map(
      ([label, value]) => `
        <div class="bar-row">
          <strong>${safe(label.replaceAll("_", " "))}</strong>
          <div class="bar-track"><div class="bar-fill" style="width:${Math.min(100, Number(value) / Math.max(summary.timing_ms.total, 1) * 100)}%"></div></div>
          <span>${safe(value)} ms</span>
        </div>
      `,
    )
    .join("");
  el("confidencePanel").innerHTML = `<p class="empty">Benchmark mode returns aggregate throughput, graph, and scoring counts only.</p>`;
  el("matchEvidence").innerHTML = `<div class="match-block"><h3>Scalability notes</h3><p>${safe(summary.scalability_notes.thirty_million)}</p></div>`;
  el("sourceRows").innerHTML = '<p class="empty">No row-level payload is returned for benchmark mode.</p>';
  renderProfilesMeta([
    {
      name: "benchmark",
      row_count: summary.canonical_record_count,
      detected_kind: "synthetic aggregate",
      mapping: summary.resolution_runtime_stats,
    },
  ]);
}

function metric(label, value) {
  return `<div class="metric"><span>${safe(label)}</span><strong>${safe(value)}</strong></div>`;
}

function renderMetrics(result) {
  const er = result.resolution.resolution_metrics;
  const stats = result.resolution.runtime_stats;
  const scoring = result.scoring.summary;
  el("metrics").innerHTML = [
    metric("Canonical records", result.canonical_record_count),
    metric("Unified entities", result.resolution.entities.length),
    metric("Flagged", scoring.flagged),
    metric("ER F1", er.available ? er.f1 : "n/a"),
    metric("Blocking reduction", `${stats.blocking_reduction_pct}%`),
    metric("Total runtime", `${result.timing_ms.total} ms`),
  ].join("");
}

function renderProfiles(result) {
  const profiles = result.scoring.flagged_profiles.length ? result.scoring.flagged_profiles : result.scoring.profiles;
  el("queueCount").textContent = String(profiles.length);
  el("profileRows").innerHTML = profiles
    .map(
      (profile) => `
        <tr data-id="${safe(profile.entity_id)}" class="${profile.entity_id === state.selectedId ? "selected" : ""}">
          <td><strong>${safe(profile.name)}</strong><br><small>${safe(profile.entity_id)}</small></td>
          <td><span class="risk ${safe(profile.risk_level)}">${safe(profile.risk_level)}</span></td>
          <td><strong>${safe(profile.deviation_score)}</strong></td>
        </tr>
      `,
    )
    .join("");

  document.querySelectorAll("#profileRows tr").forEach((row) => {
    row.addEventListener("click", () => {
      state.selectedId = row.dataset.id;
      renderSelected(state.result);
      renderProfiles(state.result);
    });
  });
}

function selectedProfile(result) {
  return result.scoring.profiles.find((profile) => profile.entity_id === state.selectedId) || result.scoring.profiles[0];
}

function renderSelected(result) {
  const profile = selectedProfile(result);
  if (!profile) return;
  el("graphTitle").textContent = profile.name;
  el("detailTitle").textContent = profile.name;
  el("selectedScore").textContent = String(profile.deviation_score);
  el("riskLevel").textContent = profile.risk_level;
  el("riskLevel").className = `risk ${profile.risk_level}`;
  el("explanation").textContent = profile.explanation;
  renderBreakdown(profile);
  renderConfidencePanel(result, profile);
  renderSourceRows(profile);
  renderGraph(result, profile);
}

function renderBreakdown(profile) {
  const rows = [
    ["Direct score", profile.direct_score],
    ["Associate score", profile.associate_proxy_score],
    ...Object.entries(profile.score_components).map(([key, value]) => [key.replaceAll("_", " "), value]),
  ];
  el("scoreBreakdown").innerHTML = rows
    .map(([label, value]) => {
      const width = Math.max(0, Math.min(100, Number(value)));
      return `
        <div class="bar-row">
          <strong>${safe(label)}</strong>
          <div class="bar-track"><div class="bar-fill" style="width:${width}%"></div></div>
          <span>${safe(value)}</span>
        </div>
      `;
    })
    .join("");
}

function renderConfidencePanel(result, profile) {
  const flags = profile.uncertainty_flags || [];
  const possible = profile.possible_matches || [];
  const confirmed = confirmedMatchesForProfile(result, profile);
  const flagChips = flags.length
    ? flags.map((flag) => `<span class="chip warning">${safe(flag)}</span>`).join("")
    : '<span class="chip muted">No uncertainty flags</span>';

  el("confidencePanel").innerHTML = `
    <div class="confidence-stats">
      ${confidenceStat("Scoring confidence", profile.scoring_confidence)}
      ${confidenceStat("Evidence coverage", profile.evidence_coverage)}
      ${confidenceStat("Risk basis", profile.risk_basis)}
    </div>
    <div class="chip-section">
      <strong>Uncertainty flags</strong>
      <div class="chip-list">${flagChips}</div>
    </div>
  `;

  el("matchEvidence").innerHTML = `
    <div class="match-block">
      <h3>Confirmed match confidence</h3>
      ${confirmed.length ? confirmed.map(renderConfirmedMatch).join("") : '<p class="empty compact">No cross-row confirmed match evidence for this profile.</p>'}
    </div>
    <div class="match-block">
      <h3>Possible identity matches</h3>
      ${possible.length ? possible.map(renderPossibleMatch).join("") : '<p class="empty compact">No unresolved possible matches.</p>'}
    </div>
  `;
}

function confidenceStat(label, value) {
  const numeric = Number(value);
  const hasBar = Number.isFinite(numeric);
  return `
    <div class="confidence-stat">
      <span>${safe(label)}</span>
      <strong>${safe(value)}</strong>
      ${hasBar ? `<div class="mini-track"><div style="width:${Math.max(0, Math.min(100, numeric))}%"></div></div>` : ""}
    </div>
  `;
}

function confirmedMatchesForProfile(result, profile) {
  const sourceIds = new Set(profile.source_record_ids || []);
  return (result.resolution.matches || [])
    .filter((match) => sourceIds.has(match.left) || sourceIds.has(match.right))
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, 8);
}

function renderConfirmedMatch(match) {
  return `
    <div class="match-row">
      <div>
        <strong>${safe(match.left)} -> ${safe(match.right)}</strong>
        <small>${safe((match.reasons || []).join(", "))}</small>
      </div>
      <span>${safe(match.confidence)}%</span>
    </div>
  `;
}

function renderPossibleMatch(match) {
  return `
    <div class="match-row possible">
      <div>
        <strong>${safe(match.other_entity_name || match.other_entity_id || match.other_record)}</strong>
        <small>${safe(match.this_record)} -> ${safe(match.other_record)} | ${safe((match.reasons || []).join(", "))}</small>
      </div>
      <span>${safe(match.confidence)}%</span>
    </div>
  `;
}

function renderSourceRows(profile) {
  if (!profile.source_rows.length) {
    el("sourceRows").innerHTML = '<p class="empty">No source rows for this entity.</p>';
    return;
  }
  el("sourceRows").innerHTML = profile.source_rows
    .map(
      (row) => `
        <div class="source-row">
          <strong>${safe(row.dataset)} row ${safe(row.row_id)} (${safe(row.record_type)})</strong>
          <div class="raw">${safe(JSON.stringify(row.raw, null, 2))}</div>
        </div>
      `,
    )
    .join("");
}

function renderProfilesMeta(profiles) {
  el("datasetProfiles").innerHTML = profiles
    .map(
      (profile) => `
        <div class="dataset-profile">
          <strong>${safe(profile.name)}</strong>
          <div class="raw">${safe(
            JSON.stringify(
              {
                rows: profile.row_count,
                kind: profile.detected_kind,
                mapping: profile.mapping,
              },
              null,
              2,
            ),
          )}</div>
        </div>
      `,
    )
    .join("");
}

function renderGraph(result, profile) {
  const svg = el("graphSvg");
  svg.replaceChildren();

  const selected = profile.entity_id;
  const edges = result.graph.edges.filter((edge) => edge.source === selected || edge.target === selected);
  const nodeIds = new Set([selected]);
  edges.forEach((edge) => {
    nodeIds.add(edge.source);
    nodeIds.add(edge.target);
  });
  const nodes = result.graph.nodes.filter((node) => nodeIds.has(node.id));
  const nodeById = Object.fromEntries(nodes.map((node) => [node.id, node]));

  const positions = {};
  positions[selected] = { x: 380, y: 180 };
  const others = nodes.filter((node) => node.id !== selected);
  const radiusX = 270;
  const radiusY = 120;
  others.forEach((node, index) => {
    const angle = (Math.PI * 2 * index) / Math.max(others.length, 1) - Math.PI / 2;
    positions[node.id] = {
      x: 380 + Math.cos(angle) * radiusX,
      y: 180 + Math.sin(angle) * radiusY,
    };
  });

  edges.forEach((edge) => {
    const source = positions[edge.source];
    const target = positions[edge.target];
    if (!source || !target) return;
    const line = document.createElementNS(svgNS, "line");
    line.setAttribute("x1", source.x);
    line.setAttribute("y1", source.y);
    line.setAttribute("x2", target.x);
    line.setAttribute("y2", target.y);
    line.setAttribute("class", "graph-edge");
    svg.appendChild(line);

    const relation = document.createElementNS(svgNS, "text");
    relation.setAttribute("x", (source.x + target.x) / 2);
    relation.setAttribute("y", (source.y + target.y) / 2 - 4);
    relation.setAttribute("text-anchor", "middle");
    relation.setAttribute("class", "graph-relation");
    relation.textContent = edge.relation;
    svg.appendChild(relation);
  });

  nodes.forEach((node) => {
    const pos = positions[node.id];
    const group = document.createElementNS(svgNS, "g");
    const circle = document.createElementNS(svgNS, "circle");
    const color = nodeColor(node.type, node.id === selected);
    circle.setAttribute("cx", pos.x);
    circle.setAttribute("cy", pos.y);
    circle.setAttribute("r", node.id === selected ? 30 : 22);
    circle.setAttribute("fill", color);
    circle.setAttribute("class", "graph-node");
    group.appendChild(circle);

    const label = document.createElementNS(svgNS, "text");
    label.setAttribute("x", pos.x);
    label.setAttribute("y", pos.y + (node.id === selected ? 46 : 38));
    label.setAttribute("text-anchor", "middle");
    label.setAttribute("class", "graph-label");
    label.textContent = trimLabel(nodeById[node.id]?.label || node.id);
    group.appendChild(label);
    svg.appendChild(group);
  });
}

function nodeColor(type, selected) {
  if (selected) return "oklch(0.47 0.19 252)";
  if (type === "Vehicle") return "oklch(0.62 0.14 78)";
  if (type === "Property") return "oklch(0.56 0.16 28)";
  if (type === "Meter") return "oklch(0.57 0.13 190)";
  if (type === "TaxReturn") return "oklch(0.54 0.13 150)";
  if (type === "Address") return "oklch(0.70 0.05 240)";
  return "oklch(0.50 0.09 230)";
}

function trimLabel(label) {
  const text = String(label || "");
  return text.length > 24 ? `${text.slice(0, 21)}...` : text;
}

function exportReport() {
  const result = state.result;
  if (!result) return;
  const profiles = result.scoring.flagged_profiles;
  const payload = {
    generated_at: new Date().toISOString(),
    mode: result.mode,
    canonical_record_count: result.canonical_record_count,
    scoring_summary: result.scoring.summary,
    graph_summary: result.graph.summary,
    resolution_runtime_stats: result.resolution.runtime_stats,
    profiles: profiles.map((profile) => ({
      entity_id: profile.entity_id,
      name: profile.name,
      risk_level: profile.risk_level,
      deviation_score: profile.deviation_score,
      direct_score: profile.direct_score,
      associate_proxy_score: profile.associate_proxy_score,
      risk_basis: profile.risk_basis,
      scoring_confidence: profile.scoring_confidence,
      evidence_coverage: profile.evidence_coverage,
      score_components: profile.score_components,
      direct_reasons: profile.direct_reasons,
      associate_reasons: profile.associate_reasons,
      uncertainty_flags: profile.uncertainty_flags,
      possible_matches: profile.possible_matches,
      explanation: profile.explanation,
      source_rows: profile.source_rows,
    })),
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  if (state.reportUrl) URL.revokeObjectURL(state.reportUrl);
  state.reportUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const stamp = new Date().toISOString().replaceAll(":", "-").slice(0, 19);
  link.href = state.reportUrl;
  link.download = `taxnet-audit-report-${stamp}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
}

el("runDemo").addEventListener("click", runDemo);
el("runFiles").addEventListener("click", runUploadedFiles);
el("runBenchmark").addEventListener("click", runBenchmark);
el("exportReport").addEventListener("click", exportReport);
el("fileInput").addEventListener("change", handleFiles);

runDemo();
