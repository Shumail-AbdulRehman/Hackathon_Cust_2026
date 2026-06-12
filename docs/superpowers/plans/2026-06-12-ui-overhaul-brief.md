# TaxNet XAI — UI Overhaul Design Brief

> Produced by `$impeccable shape`. Awaits explicit user confirmation before implementation.

---

## 1. Feature Summary

Rebuild the TaxNet XAI frontend as a tabbed, evidence-first audit dashboard. The current single-page dashboard is replaced with a full re-architecture that surfaces every new backend capability — NIC geocoding, Benford's Law, the LLI metric, temporal asset-burst detection, ANN blocking, and offshore/sanctions data — alongside the existing entity resolution, scoring, and SHAP explanations. A dedicated **Graph Investigation** tab provides an interactive D3 force-directed network view where users can select nodes, inspect relationships, and navigate child/parent connections.

## 2. Primary User Action

A forensic investigator opens the dashboard, runs (or uploads) data, and immediately understands:
- Which entities are flagged and why.
- The evidence graph around a selected entity.
- The breakdown of risk scores, lifestyle vs. income metrics, temporal patterns, and geographic signals.
- Then they can switch to Graph Investigation to explore the full network interactively.

## 3. Design Direction

- **Color strategy:** Full palette — Royal Ink Blue (authority/primary), Sage Green (success/low-risk), Aged Parchment Gold (value highlights), Amber Alert (medium risk), Burnt Sienna Signal (high/critical risk), warm paper neutrals.
- **Theme scene sentence:** An FBR auditor reviews a flagged taxpayer profile on a large monitor in a well-lit office; the interface must feel as credible and organized as a courtroom evidence board.
- **Anchor references:** Palantir-style evidence networks, UK Companies House beneficial-ownership explorers, The Economist's data-driven editorial pages, and the calm restraint of a government case-management tool.

## 4. Scope

- **Fidelity:** Production-ready.
- **Breadth:** Whole frontend surface — replace `index.html`, `styles.css`, and `app.js`.
- **Interactivity:** Fully interactive single-page app with D3 charts and graph view.
- **Time intent:** Ship-quality for the hackathon demo; responsive down to tablet, gracefully usable on mobile.

## 5. Layout Strategy

**Persistent chrome:**
- Top bar: product title (serif), global actions (Run synthetic audit, Upload CSVs, Benchmark), and tab navigation (Overview | Profiles | Graph Investigation).
- Subtle 1px rule-line separator; sticky position.

**Tab 1 — Overview:**
- Pipeline status strip (3 steps: Ingest → Resolve → Score).
- Key metrics row: records ingested, entities resolved, flagged profiles, average confidence, top risk tier distribution.
- Upload / benchmark controls and dataset profile summary.

**Tab 2 — Profiles:**
- Left sidebar: sortable/filterable flagged-profile queue with search and risk-filter chips.
- Main area: selected-entity "case file".
  - Header: name, entity ID, risk tier chip, deviation score, LLI ratio, confidence.
  - Score-components bar chart (D3) showing direct, associate, ML, LLI gap, asset burst, etc.
  - Evidence summary: income vs. lifestyle, asset list, offshore links, SHAP top features.
  - Temporal timeline chart (D3) for asset events vs. income events.
  - Benford digit-distribution mini chart when data exists.
  - NIC geocoding chips (province/district) when available.
  - Source rows accordion.
  - Mini graph preview of the selected entity's ego network with a link to the full Graph tab.

**Tab 3 — Graph Investigation:**
- Full-width D3 force-directed graph of the entire resolved network.
- Node legend by type (Person, Vehicle, Property, Utility, Tax Return, Offshore Entity, Address/Phone hub) with distinct shapes and colors.
- Edge legend by relationship (owns, shares address, shares phone, linked to offshore, associate/proxy) with distinct stroke styles and arrowheads.
- Hover: highlight node + ego neighborhood, show tooltip.
- Click: fix selection, reveal detail card, and expand/collapse child nodes.
- Zoom and pan.
- Filter controls to show/hide node types and relationship types.

## 6. Key States

- **Empty / first-run:** Friendly, non-technical prompt to run the synthetic audit or upload CSVs.
- **Loading:** Skeleton placeholders in panels; pipeline steps animate minimally (respect `prefers-reduced-motion`).
- **No flagged profiles:** Empty queue with explanation and suggestion to lower thresholds or upload more data.
- **No graph data:** Empty graph state with illustration text.
- **Error:** Inline alert banner with retry action.
- **Mobile:** Stacked single-column layout; tabs become a bottom or top dropdown.

## 7. Interaction Model

- Tabs switch content without full page reload.
- Click a profile in the queue → load its case file and scroll the Profile tab into view.
- Click "Investigate in Graph" → switch to Graph tab, center on the entity, highlight its ego network.
- Hover graph node → tooltip with name, type, and key score/value.
- Click graph node → persist selection and show detail card; double-click or "Expand" button fetches/Shows connected neighbors one hop deeper.
- Zoom/pan with mouse wheel and touch gestures.
- Upload CSVs → schema mapping panel opens inline on Overview tab.

## 8. Content Requirements

- Tab labels: Overview, Profiles, Graph Investigation.
- Risk tiers: Critical, High, Medium, Low (with explicit labels + color/shape).
- Microcopy: "Run synthetic audit", "Upload civic records", "Investigate network", "No flagged profiles yet.", "Select an entity to view evidence."
- Chart labels and tooltips for all D3 visualizations.
- Legend entries for graph node types and edge types.

## 9. Recommended References

- `spatial-design.md` — tabbed layout and responsive grid.
- `typography.md` — serif/sans/mono hierarchy.
- `interaction-design.md` — tab switching, selection, upload flow.
- `motion-design.md` — reduced-motion transitions.
- `color-and-contrast.md` — color-blind-safe risk encoding.

## 10. Open Questions

1. Should the Graph tab load the full graph for large datasets (e.g., 1000+ ICIJ nodes) or default to an ego network around the highest-risk entity?
2. Should the Profiles tab default to the first flagged profile, or stay empty until the user selects one?
3. Do you want the mini graph preview on the Profiles tab to be a static D3 render or a read-only version of the interactive graph?
