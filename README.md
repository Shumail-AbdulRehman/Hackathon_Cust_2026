# TaxNet XAI

TaxNet XAI is a working CUST Hackathon prototype for **Problem #2: Graph AI for Broadening the National Tax Net**.

It ingests Pakistani civic-style datasets, resolves noisy identities without assuming a shared CNIC, builds a financial-footprint evidence graph, and produces explainable audit-risk scores for review.

The implementation is intentionally evidence-first:

- every resolved entity links back to source rows
- every identity match includes confidence features
- every risk score includes component reasons
- every flag is worded as audit risk, not legal guilt

## Current Status

This is a functional hackathon prototype, not a production tax system.

Working today:

- CSV upload and schema profiling
- automatic and manual field mapping
- synthetic demo pipeline
- noisy entity resolution
- Urdu/English-aware text normalization
- evidence graph construction
- direct and associate-linked scoring
- audit-trail explanations
- browser dashboard
- JSON report export
- synthetic benchmark mode
- backend unit tests

Known limitations:

- scoring is rule-based, not trained ML
- no GNN model yet
- no SHAP/LIME attribution yet
- graph is an in-memory evidence graph, not Neo4j/FalkorDB
- benchmark mode is useful for demonstration but not national-scale proof
- synthetic labels validate demo behavior, not real-world FBR data performance

## Run

Start the server:

```bash
python3 run.py
```

Open the frontend:

```text
http://127.0.0.1:8000
```

API health:

```bash
curl http://127.0.0.1:8000/api/health
```

Run synthetic pipeline:

```bash
curl http://127.0.0.1:8000/api/demo
```

Run benchmark:

```bash
curl "http://127.0.0.1:8000/api/benchmark?citizens=500"
```

## Tests

Use explicit discovery:

```bash
python3 -m unittest discover -s tests -v
```

Current verified result:

```text
Ran 8 tests
OK
```

Note: `python3 -m unittest` alone may discover zero tests depending on the environment.

## Project Structure

```text
taxnet/
  app.py                 HTTP server and API routes
  ingestion.py           dataset profiling and canonical field mapping
  normalization.py       Urdu/English-aware normalization helpers
  entity_resolution.py   blocking, fuzzy matching, clustering, validation metrics
  graph_engine.py        evidence graph construction
  scoring.py             direct and associate-linked risk scoring
  synthetic.py           synthetic Pakistani civic datasets with hidden truth labels
  pipeline.py            end-to-end orchestration

web/
  index.html             auditor dashboard
  styles.css             product UI styling
  app.js                 browser app, CSV upload, mapping review, graph rendering

tests/
  test_pipeline.py       backend pipeline checks

data/complex_csv/
  fbr_tax_records_complex.csv
  excise_vehicles_complex.csv
  disco_consumption_complex.csv
  property_transfers_complex.csv
  README.md

PRODUCT.md               product positioning
DESIGN.md                UI/design context
PROJECT_CONTEXT.md       hackathon context and anti-hallucination notes
kimi-response.txt        external AI critique / strategy conversation
```

## Complex CSV Test Set

A complex upload test set is included in:

```text
data/complex_csv/
```

Upload these four files together, or one by one:

```text
fbr_tax_records_complex.csv
excise_vehicles_complex.csv
disco_consumption_complex.csv
property_transfers_complex.csv
```

The test set includes:

- noisy name variants
- Urdu name text
- Pakistan phone formats
- missing phones
- shared addresses
- proxy/associate ownership
- luxury assets with low or zero declared income
- high utility bills
- property transfer records
- commercial/seller noise records

Verified complex CSV result:

```text
canonical records: 69
resolved entities: 18
graph nodes: 122
graph edges: 171
flagged profiles: 12
high risk: 10
medium risk: 2
low risk: 6
average scoring confidence: 87.9
```

## Supported Dataset Shape

The system does not require exact filenames. It profiles uploaded CSV files and maps likely columns into canonical concepts.

Example accepted fields:

```text
full_name, owner_name, consumer_name, buyer_name
reported_address, owner_address, installation_address, property_address
phone_number, owner_phone
declared_income_pkr
tax_paid_pkr
filer_status
engine_capacity_cc
vehicle_make_model
avg_monthly_bill_pkr
property_value_pkr
area_marla
transfer_date
registration_year
```

If a column is missing, the pipeline uses available evidence and lowers certainty rather than inventing values.

## Pipeline

```text
Datasets
  -> profile and map columns
  -> canonical records
  -> entity resolution
  -> evidence graph
  -> direct and associate-linked scoring
  -> dashboard and audit trail
```

## Entity Resolution

The matcher uses:

- text normalization
- Urdu/Arabic character approximation
- honorific and title cleanup
- address normalization
- phone normalization
- blocking by phone, city plus surname, address block, and initials
- weighted comparison features
- iterative union-find clustering

Same-person examples:

```text
M. Ahmed
Muhammad Ahmed
Mohd Ahmed Khan
Chaudhary M. Ahmed
```

The synthetic dataset includes hidden truth labels. The default synthetic run reports pairwise precision, recall, and F1.

## Proxy and Associate Ownership

The graph separates same-person resolution from associate relationships.

Example:

```text
Ali Raza has low declared income.
Noman Raza and Sana Ali share Ali's address.
Noman and Sana hold high-value assets.
Ali receives associate-linked risk, not confirmed ownership.
```

This distinction matters because shared address or phone can mean household/proxy risk, but it should not automatically merge identities.

## Deviation Score

Each entity receives:

- final deviation score
- direct score
- associate/proxy score
- risk basis
- evidence coverage
- scoring confidence
- component breakdown
- direct reasons
- associate reasons
- uncertainty flags
- source rows

Signals include:

- declared income
- tax paid
- filer status
- utility bill pressure
- vehicle engine capacity and estimated value
- property value
- shared-address or shared-phone asset links
- peer outlier checks

The output is always framed as audit-risk review.

## Dashboard Guide

Main controls:

- **Run synthetic audit**: runs the built-in demo data.
- **Load CSVs**: uploads one or more CSV files. Files can be added one by one.
- **Run uploaded files**: runs the pipeline on uploaded CSVs.
- **Benchmark**: runs a synthetic scalability benchmark.
- **Export report**: downloads the current flagged profiles as JSON.

Main panels:

- **Entity Resolution**: shows whether records were unified into entities.
- **Knowledge Graph**: shows generated graph size.
- **Deviation + XAI**: shows flagged profile count.
- **Audit Queue**: ranked flagged profiles.
- **Graph Evidence**: selected entity and connected evidence.
- **Audit Trail**: natural-language explanation and score breakdown.
- **Confidence Review**: uncertainty flags, possible matches, confirmed match evidence.
- **Rows Used**: raw source rows supporting the selected profile.

## Why Python Backend Instead of Node.js

Node.js is useful for API gateways, authentication, realtime dashboards, and serving frontend assets.

This project uses Python as the primary backend because the hard parts are data science and graph/entity-resolution work:

- fuzzy matching
- record linkage
- batch data profiling
- graph analytics
- model validation
- numerical scoring
- future ML/embedding integration

This prototype uses only Python standard-library modules so it runs without package installation, while keeping a clean path to add Pandas, DuckDB, Splink, NetworkX, FastAPI, FalkorDB, Neo4j, or embeddings later.

## Kimi Review And Codex Response

`kimi-response.txt` contains an external AI review and strategy discussion. The review is useful, but it should be read as a technical critique, not as a source of official requirements.

### What Kimi Got Right

Kimi correctly identified that the project already has:

- working entity resolution
- multi-key blocking
- fuzzy name matching
- phone normalization
- Urdu/English normalization
- pairwise validation metrics
- CSV ingestion and field mapping
- graph construction
- direct and associate-linked scoring
- explainable audit trails
- frontend visualization
- benchmark mode
- report export

Kimi also correctly identified the biggest real gap:

```text
The current scoring engine is deterministic and rule-based, not a trained ML/GNN model.
```

That is true. The current system is explainable and demo-stable, but it is not yet an XGBoost, LightGBM, SHAP, or GNN implementation.

### Corrections To Kimi's Review

Some Kimi statements need correction:

- Address normalization does not "expand" abbreviations. It normalizes full words into compact tokens, for example `House -> h`, `Street -> st`, and `Phase -> ph`.
- The graph has `Property` nodes with transfer metadata, but no separate `Transaction` node type.
- Some exact benchmark numbers may differ between runs and repo versions.
- Missing items such as Benford's Law, PEP cross-reference, SHAP, FalkorDB, D3, and five risk tiers are possible enhancements, not explicit official rubric requirements.
- The project does not have a named Lavish Lifestyle Index, but it does compute a similar `lifestyle_pressure` signal.

### Response To Kimi's Three Strategies

Kimi proposed three possible directions:

1. **Approach A: ML + XAI Powerhouse**
2. **Approach B: Graph Intelligence First**
3. **Approach C: Production-Grade Data Platform**

Codex assessment:

- Approach A is directionally best, but the full version is too large and risky for a short hackathon window.
- Approach B has strong visual/innovation upside, but a full GNN on synthetic data is fragile and harder to explain.
- Approach C is not recommended for a 48-hour hackathon because infrastructure can consume time without improving the core intelligent demo.

Recommended path:

```text
Keep the working rule engine.
Add graph analytics and better visual explanations.
Optionally add ML as a second scoring head, not as a full replacement.
Keep deterministic audit explanations as the source of truth.
```

### Practical Upgrade Plan

Highest-value improvements:

1. Add simple graph analytics:
   - degree count
   - shared-address count
   - shared-phone count
   - associate asset value
   - high-risk neighbor count
   - lightweight PageRank-style centrality
2. Add five risk tiers:
   - low
   - watch
   - elevated
   - high
   - critical
3. Add better visualizations:
   - reported income vs lifestyle pressure
   - direct assets vs associate-linked assets
   - timeline of asset acquisitions
   - graph node sizing by risk/centrality
4. Add temporal red flags using transfer and registration dates:
   - luxury asset after low/zero tax filing
   - multiple high-value acquisitions in a short period
   - recent property/vehicle acquisition by non-filer
5. Add optional interpretable ML:
   - train on engineered synthetic features
   - keep original feature names
   - avoid PCA for the scoring model
   - use feature attribution only as supporting evidence

### PCA Decision

PCA is not recommended for the main scoring model.

Reason:

```text
PCA mixes original features into abstract components.
An explanation like "PC2 increased risk" is not useful to an auditor.
```

Better:

```text
Use interpretable engineered features directly:
- income_lifestyle_ratio
- vehicle_value_to_income_ratio
- property_value_to_income_ratio
- utility_to_income_ratio
- associate_asset_value
- shared_address_count
- shared_phone_count
- peer_z_score_assets
- peer_z_score_utility
```

This keeps explanations understandable:

```text
Utility bill is 6.9x declared income.
Vehicle value is high relative to income.
Shared address links to high-value assets.
```

## Rubric-Oriented Assessment

Against the Round 1 rubric, this project is strongest in:

- solution relevance
- technical implementation
- interpretability
- demo stability

It is weaker in:

- trained ML/GNN depth
- production-scale benchmarking
- real-world validation
- advanced graph analytics

Estimated current Round 1 strength:

```text
Strong prototype / finalist-worthy if presented well.
Not a guaranteed winner without polish and at least one deeper AI/graph upgrade.
```

## Production Upgrade Path

For a real deployment:

- Replace the standard-library server with FastAPI.
- Persist canonical records and graph edges in PostgreSQL, DuckDB, FalkorDB, or Neo4j.
- Use Splink or a trained probabilistic linkage model for large-scale entity resolution.
- Add interpretable graph features and an optional trained scoring head.
- Add queue-based batch processing for large datasets.
- Add row-level access control and audit logging.
- Add manual review workflows for uncertain matches.
- Add benchmark runs on millions of synthetic records to support the 30M-citizen scaling story.
- Keep audit-risk language and avoid legal-guilt claims.
