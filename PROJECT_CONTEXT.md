# Project Context: CUST Hackathon 2026

This file records what has been verified from the local files and the user-provided image.
It is intended to prevent hallucination during future planning, design, and implementation.

Last analyzed from local workspace: 2026-06-12, Asia/Karachi environment.

## Anti-Hallucination Rules

- Treat only the facts in this file as confirmed unless new files, data, or user instructions are added.
- Do not invent datasets, columns, sample RFPs, scoring formulas, client requirements, or evaluation labels.
- If something is not present in the local files, mark it as missing or assumed.
- If building a prototype, keep synthetic/generated data clearly labeled as synthetic.
- Do not claim the system proves tax evasion or fraud. It can only flag risk or audit candidates.
- Do not treat post-evaluation fields as pre-bid predictors unless explicitly justified.
- Re-check files if they change.

## Local Workspace Contents

Directory analyzed:

`/home/shumail/cust-hackathon`

Files present:

1. `CUST Hackathon 2026_Rubrics.pdf`
2. `CUST Hackathon Problem#1 (TEKROWE).pdf`
3. `CUST Hackathon Problem#2 (CIKLUM).pdf`
4. `Problem#1_Sample_Datasets (TEKROWE).xlsx`

There is no application source code currently in this directory.

## File Metadata Summary

### `CUST Hackathon 2026_Rubrics.pdf`

- Type: PDF
- Pages: 4
- PDF version: 1.6
- Encrypted: yes for copy/change/add notes, but text extraction worked locally
- Created: 2024-11-21 10:20:04 PKT
- Contains judging rubrics for Round 1 and Round 2.

### `CUST Hackathon Problem#1 (TEKROWE).pdf`

- Type: PDF
- Pages: 2
- PDF version: 1.7
- Author metadata: `rizwan fai`
- Creator/producer metadata: `www.smallpdf.com`
- Created/modified: 2026-06-10 11:46:58 PKT
- Contains Problem 1: AI-Powered Bid and Proposal Response Engine.

### `CUST Hackathon Problem#2 (CIKLUM).pdf`

- Type: PDF
- Pages: 1
- PDF version: 1.7
- Author metadata: `rizwan fai`
- Creator/producer metadata: `www.smallpdf.com`
- Created/modified: 2026-06-10 11:47:24 PKT
- Contains Problem 2: Graph AI for Broadening the National Tax Net.

### `Problem#1_Sample_Datasets (TEKROWE).xlsx`

- Type: Microsoft Excel 2007+ workbook
- Created by metadata: `openpyxl`
- Last modified by metadata: `rizwan fai`
- Created: 2026-06-04T08:29:38Z
- Modified: 2026-06-10T10:42:46Z
- Contains 2 worksheets:
  - `PS1 - Bid History`
  - `PS1 - Capability Library`

Note: the actual worksheet names use an en dash in the workbook. This file writes them with ASCII hyphens for portability.

## Hackathon Rubric

### Round 1 Evaluation

Round 1 maximum score: 100.

Criteria:

- Solution Relevance and Effectiveness: 20%
- Innovation and Differentiation: 20%
- Technical Implementation: 30%
- Validation and Reliability: 15%
- Feasibility and Scalability: 15%

Tie-breaking order:

1. Technical Implementation
2. Innovation and Differentiation
3. Solution Relevance and Effectiveness
4. Feasibility and Scalability
5. Judges Committee

Important implication:

Technical implementation is the highest-weighted Round 1 factor. A working, stable, demoable prototype matters more than a broad concept.

### Round 2 Evaluation

Round 2 maximum score: 100.

Criteria:

- Value Proposition: 40%
- Market Viability and Growth Potential: 40%
- Pitch and Delivery: 20%

Tie-breaking order:

1. Value Proposition
2. Market Viability and Growth Potential
3. Pitch and Delivery
4. Judges Committee

Important implication:

Round 2 rewards business clarity, adoption potential, and a convincing pitch.

## Problem 1: AI-Powered Bid and Proposal Response Engine

### Confirmed Problem Statement

Industry vertical:

- Procurement
- Sourcing
- Contract management

Difficulty:

- Advanced

Team size:

- Up to 3 members

Core background:

- Organizations issue many RFPs, RFQs, and tenders.
- Bid and proposal managers spend significant time reading long documents, extracting requirements, mapping capabilities, writing responses, and formatting submissions.
- Missing mandatory requirements or producing weak proposal sections can lead to disqualification.

### Required Capabilities

The proposed system should:

- Ingest an RFP/RFQ/tender document in PDF or DOCX format.
- Extract mandatory requirements.
- Extract evaluation criteria.
- Extract submission deadlines.
- Extract question/answer sections.
- Match extracted requirements against a company capability library.
- Auto-draft a structured proposal response.
- Map relevant content to each question or section.
- Flag compliance gaps where evidence or capability is missing.
- Score bid opportunity using win-probability heuristics.
- Support GO/NO-GO decision making.
- Provide an intuitive UI for bid managers to review, edit, and approve generated content.
- Export the final draft response.

### Expected Deliverables

Confirmed deliverables from the PDF:

- Working prototype or POC.
- Accepts a sample RFP document.
- Generates a structured draft response.
- Separate workspace for each RFP/RFQ/tender.
- Auto-generated compliance checklist.
- Pass/fail mapping against capability library.
- Win-probability dashboard.
- GO/NO-GO decision.
- Demonstrated reduction in manual bid preparation effort by at least 50%.
- UI for review, edit, approval, and export.

### Required AI Components

Confirmed components from the PDF:

- LLM for document parsing, requirement extraction, and narrative generation.
- RAG for querying the capability library.
- Named Entity Recognition for deadlines, budgets, evaluation weights, and compliance clauses.
- Scoring/ranking model for win probability.

### Sample Dataset Expected by PDF

The PDF says teams should receive:

- 3 anonymized sample RFP documents, 15 to 80 pages each.
- Historical bid outcomes: 120 rows x 18 columns.
- Capability library: 50 records.
- Evaluation criteria taxonomy: 15+ entries.

### Actual Problem 1 Dataset Present Locally

Only one workbook is present:

`Problem#1_Sample_Datasets (TEKROWE).xlsx`

It contains:

- Historical bid outcomes: 120 rows x 12 columns.
- Capability library: 50 rows x 8 columns.

Missing locally:

- Sample RFP PDFs/DOCX files.
- Historical bid outcomes with 18 columns.
- Evaluation criteria taxonomy.
- Rich CVs, detailed case studies, reusable proposal text, or certifications beyond simple fields.

## Problem 1 Workbook: Bid History

Worksheet:

`PS1 - Bid History`

Declared title row:

`PS1 - Bid History Dataset`

Declared description row:

`Historical bid outcomes for win-probability modelling | 120 records`

Actual normalized shape:

- Rows: 120 data rows
- Columns: 12

Columns:

1. `Bid ID`
2. `Client`
3. `Sector`
4. `Budget`
5. `Score (%)`
6. `Outcome`
7. `Response Time (hrs)`
8. `Compliance %`
9. `Doc Pages`
10. `Gaps Found`
11. `Bid Manager`
12. `Submission Date`

First row:

- Bid ID: `BID-0001`
- Client: `FWO`
- Sector: `Construction`
- Budget: `PKR 22M`
- Score (%): `92`
- Outcome: `Win`
- Response Time (hrs): `94`
- Compliance %: `75`
- Doc Pages: `144`
- Gaps Found: `2`
- Bid Manager: `Sara Malik`
- Submission Date: `2025-02-22`

Last row:

- Bid ID: `BID-0120`
- Client: `PTCL`
- Sector: `Energy`
- Budget: `PKR 368M`
- Score (%): `70`
- Outcome: `Win`
- Response Time (hrs): `93`
- Compliance %: `92`
- Doc Pages: `306`
- Gaps Found: `7`
- Bid Manager: `Asif Khan`
- Submission Date: `2025-08-13`

### Bid History Outcome Summary

- Wins: 68
- Losses: 52
- Win rate: 56.7%

### Numeric Summary

Budget, interpreted as PKR millions:

- Win average: 282.06
- Loss average: 255.60
- Overall average: 270.59
- Overall median: 266.00
- Overall min: 11
- Overall max: 500

Score (%):

- Win average: 82.81
- Loss average: 56.67
- Overall average: 71.48
- Overall median: 72.00
- Overall min: 45
- Overall max: 96

Response Time (hrs):

- Win average: 93.09
- Loss average: 98.83
- Overall average: 95.58
- Overall median: 91.00
- Overall min: 25
- Overall max: 168

Compliance %:

- Win average: 78.35
- Loss average: 79.04
- Overall average: 78.65
- Overall median: 77.00
- Overall min: 60
- Overall max: 100

Doc Pages:

- Win average: 238.60
- Loss average: 243.63
- Overall average: 240.78
- Overall median: 251.00
- Overall min: 30
- Overall max: 450

Gaps Found:

- Win average: 3.93
- Loss average: 4.00
- Overall average: 3.96
- Overall median: 4.00
- Overall min: 0
- Overall max: 8

### Sector Win Rates

- Energy: 13/20 wins, 65.0%
- Telecom: 11/17 wins, 64.7%
- Logistics: 6/10 wins, 60.0%
- Construction: 13/23 wins, 56.5%
- Healthcare: 6/11 wins, 54.5%
- Finance: 7/13 wins, 53.8%
- IT Services: 6/12 wins, 50.0%
- Education: 6/14 wins, 42.9%

### Client Win Rates

- BISP: 5/6 wins, 83.3%
- ERRA: 5/6 wins, 83.3%
- FWO: 5/6 wins, 83.3%
- NESPAK: 5/6 wins, 83.3%
- PEMRA: 5/6 wins, 83.3%
- PSO: 5/6 wins, 83.3%
- Jazz: 4/6 wins, 66.7%
- NBP: 4/6 wins, 66.7%
- NLC: 4/6 wins, 66.7%
- PIA: 4/6 wins, 66.7%
- OGDCL: 3/6 wins, 50.0%
- PAF: 3/6 wins, 50.0%
- PIMS: 3/6 wins, 50.0%
- PTCL: 3/6 wins, 50.0%
- HEC: 2/6 wins, 33.3%
- NDMA: 2/6 wins, 33.3%
- SBP: 2/6 wins, 33.3%
- WAPDA: 2/6 wins, 33.3%
- CDA: 1/6 wins, 16.7%
- NEPRA: 1/6 wins, 16.7%

### Bid Manager Win Rates

- Sara Malik: 10/12 wins, 83.3%
- Tariq Mehmood: 9/12 wins, 75.0%
- Usman Raza: 9/12 wins, 75.0%
- Bilal Sheikh: 8/12 wins, 66.7%
- Asif Khan: 7/12 wins, 58.3%
- Hira Noor: 7/12 wins, 58.3%
- Nadia Ahmed: 6/12 wins, 50.0%
- Zara Hussain: 6/12 wins, 50.0%
- Faiza Iqbal: 3/12 wins, 25.0%
- Kamran Ali: 3/12 wins, 25.0%

### Threshold Observations

Score (%):

- Score >= 60: 68/88 wins, 77.3%
- Score >= 70: 68/68 wins, 100.0%
- Score >= 80: 41/41 wins, 100.0%
- Score >= 90: 19/19 wins, 100.0%

Important warning:

`Score (%)` appears to perfectly separate wins at 70 and above in this dataset. This is probably post-evaluation information and may be target leakage for a real pre-bid prediction model. Do not use it blindly as an input for pre-bid GO/NO-GO prediction unless the prototype clearly labels it as an estimated internal score.

Compliance %:

- Compliance >= 60: 68/120 wins, 56.7%
- Compliance >= 70: 47/85 wins, 55.3%
- Compliance >= 80: 27/50 wins, 54.0%
- Compliance >= 90: 16/27 wins, 59.3%

Gaps Found:

- Gaps <= 0: 9/12 wins, 75.0%
- Gaps <= 2: 24/39 wins, 61.5%
- Gaps <= 4: 38/70 wins, 54.3%
- Gaps <= 6: 54/96 wins, 56.2%

Response Time:

- Response time <= 48 hours: 14/21 wins, 66.7%
- Response time <= 72 hours: 22/39 wins, 56.4%
- Response time <= 120 hours: 47/82 wins, 57.3%
- Response time <= 168 hours: 68/120 wins, 56.7%

Budget:

- Budget >= PKR 50M: 62/113 wins, 54.9%
- Budget >= PKR 100M: 58/103 wins, 56.3%
- Budget >= PKR 250M: 38/65 wins, 58.5%
- Budget >= PKR 400M: 21/33 wins, 63.6%

### Approximate Correlations With Win Outcome

These are simple Pearson-style correlations where win is encoded as 1 and loss as 0.

- Budget: 0.093
- Score (%): 0.859
- Response Time (hrs): -0.068
- Compliance %: -0.029
- Doc Pages: -0.020
- Gaps Found: -0.015

Interpretation:

- `Score (%)` dominates the dataset.
- Other numeric fields have weak relationship to outcome.
- This dataset is synthetic or simplified and should not be overinterpreted.

## Problem 1 Workbook: Capability Library

Worksheet:

`PS1 - Capability Library`

Declared title row:

`PS1 - Capability Library`

Declared description row:

`Company past projects and certifications for RAG retrieval | 50 records`

Actual normalized shape:

- Rows: 50 data rows
- Columns: 8

Columns:

1. `Cap ID`
2. `Domain`
3. `Project Summary`
4. `Certification`
5. `Year Completed`
6. `Contract Value`
7. `Duration (months)`
8. `Client Type`

First row:

- Cap ID: `CAP-001`
- Domain: `Cybersecurity`
- Project Summary: `Project 1: Cybersecurity deployment for client`
- Certification: `ISO 27001`
- Year Completed: `2023`
- Contract Value: `PKR 15M`
- Duration (months): `34`
- Client Type: `International`

Last row:

- Cap ID: `CAP-050`
- Domain: `ERP Implementation`
- Project Summary: `Project 50: ERP Implementation deployment for client`
- Certification: `ISO 27001`
- Year Completed: `2022`
- Contract Value: `PKR 93M`
- Duration (months): `24`
- Client Type: `Private Sector`

### Capability Domain Counts

- Cybersecurity: 5
- ERP Implementation: 5
- Road Construction: 4
- Bridge Engineering: 4
- Fleet Management: 4
- Hospital IT: 4
- Medical Equipment: 4
- Solar Energy: 4
- Network Design: 4
- LMS Development: 4
- Mobile Banking: 4
- Cloud Infrastructure: 4

### Certification Counts

- ISO 27001: 16
- N/A: 10
- CE Mark: 10
- CMMI L3: 8
- ISO 9001: 4
- PMP: 2

### Year Completed Counts

- 2022: 10
- 2021: 8
- 2020: 8
- 2024: 8
- 2023: 7
- 2025: 5
- 2019: 4

### Client Type Counts

- International: 18
- Federal Govt: 11
- Provincial Govt: 11
- Private Sector: 10

### Capability Value and Duration

Contract value, interpreted as PKR millions:

- Average: 112.02
- Median: 114.00
- Min: 8
- Max: 200

Duration in months:

- Average: 21.00
- Median: 21.00
- Min: 7
- Max: 36

### Capability Library Limitations

The capability library is useful for a prototype, but it is shallow.

Limitations:

- Project summaries are generic templates.
- There are no detailed case studies.
- There are no CVs.
- There are no quantified outcomes.
- There are no supporting document attachments.
- There are no reusable proposal paragraphs.
- There are no source citations for evidence.

For a polished demo, richer synthetic capability text may need to be generated and clearly labeled as synthetic demo content.

## Problem 1 Recommended Prototype Scope

This is a recommendation based on rubric fit and available data, not a confirmed requirement.

Recommended MVP:

1. Upload or select an RFP/tender document.
2. Extract:
   - mandatory requirements
   - deadlines
   - evaluation criteria
   - Q&A sections
   - budget or contract value if present
3. Generate a compliance checklist.
4. Retrieve matching capabilities from the capability library.
5. Mark each requirement as:
   - pass
   - partial
   - gap
6. Generate draft proposal sections.
7. Compute win probability or bid attractiveness.
8. Produce GO/NO-GO recommendation.
9. Show dashboard and editable proposal.
10. Export draft response.

High-value UI screens:

- RFP workspace list.
- Document ingestion and extraction review.
- Compliance matrix.
- Capability evidence panel.
- Draft response editor.
- Win probability dashboard.
- GO/NO-GO decision page.

Important implementation warning:

Because no sample RFP file is present locally, any RFP used in a demo must be obtained from the user, downloaded from a permitted source, or generated as synthetic sample content.

## Problem 2: Graph AI for Broadening the National Tax Net

### Confirmed Problem Statement

Theme:

- FinTech
- Knowledge graphs
- Fraud detection

Core problem:

- Pakistan has a low tax-to-GDP ratio.
- Public agencies hold fragmented datasets.
- These datasets may include vehicle registrations, real estate transactions, luxury travel logs, utility bills, and tax returns.
- These silos are not intelligently linked to identify high-net-worth individuals who are non-filers or under-reporting income.

### Required Challenge

Teams must build:

- A knowledge graph.
- An entity resolution pipeline.
- A system that links disparate identities.
- A Tax Compliance Deviation Score.
- An audit trail explaining why an individual was flagged.

Example from problem statement:

- Person owns a 2000cc vehicle.
- Person has PKR 300,000 monthly electricity bill.
- Person files a zero-tax return.
- System should link these signals and flag the compliance deviation.

### Academic Complexity Mentioned

- Unsupervised entity resolution.
- Graph neural networks for anomaly detection.
- Handling Urdu/English mixed text in name and address fields.

### Industry Applicability Mentioned

- Enterprise fraud detection.
- Banking KYC/AML compliance.
- GovTech tax infrastructure.

### Evaluation Criteria Mentioned

- Precision and recall of entity resolution.
- Depth of graph-based relationship mapping.
- Interpretability of the AI audit trail.

### Problem 2 Missing Locally

No local dataset is present for Problem 2.

Missing:

- Vehicle registry dataset.
- Property dataset.
- Utility billing dataset.
- Tax filing dataset.
- Travel logs dataset.
- Ground-truth identity matches.
- Ground-truth compliance labels.
- Scoring formula.
- Entity schema.
- UI design.

If building Problem 2, synthetic data must be created and labeled clearly.

## User-Provided Image Context

The user provided an image at:

`/tmp/codex-clipboard-9UBae7.png`

The image title:

`Build an Entity Resolution & Knowledge Graph Pipeline`

The image describes a 4-part architecture:

1. Entity Resolution
2. Knowledge Graph
3. Deviation Score
4. Explainable AI UI

### Image: Entity Resolution Section

Confirmed text from image:

- Link the same person across 4 datasets with no shared CNIC.
- Techniques:
  - string embeddings
  - blocking
  - LLM-based parsers
- Must handle:
  - `M. Ahmed`
  - `Muhammad Ahmed`
  - `Chaudhary M. Ahmed`

Interpretation:

- The image reinforces that no common CNIC should be assumed.
- Matching must rely on noisy names, addresses, and other indirect attributes.
- The examples show abbreviation, full-name expansion, and honorific/family-name variation.

### Image: Knowledge Graph Section

Confirmed text from image:

- Build a graph DB.
- Examples:
  - Neo4j
  - NetworkX
- Nodes:
  - Person
  - Vehicle
  - Property
  - Meter
- Edges:
  - owns
  - registered_at
  - filed_in
  - declared_at

Interpretation:

- Neo4j is suitable for persistent graph DB and Cypher queries.
- NetworkX is suitable for Python in-memory prototype and graph analytics.
- A practical MVP can use NetworkX first and optionally export to Neo4j.

### Image: Deviation Score Section

Confirmed text from image:

- Risk score from 0 to 100.
- Compares declared income versus estimated lifestyle value.
- Score 100 means extreme non-compliance gap.

Interpretation:

- The score is a risk indicator, not a legal conclusion.
- A transparent formula is preferable for a hackathon demo.
- The score should show component contributions, not just a final number.

### Image: Explainable AI UI Section

Confirmed text from image:

- Dashboard.
- Visual network graph plus text audit trail per flagged entity.
- Example:
  - Income PKR 50K/month
  - owns 3000cc Land Cruiser
  - PKR 280K bill

Interpretation:

- The UI must show both graph evidence and plain-language explanation.
- Judges should be able to click a flagged person and see why they were flagged.

## Problem 2 Recommended Prototype Scope

This is a recommendation based on the local problem statement and user-provided image.

Recommended synthetic datasets:

1. Tax filings
   - filer_id or return_id
   - name
   - father_name if available
   - address
   - declared_monthly_income
   - declared_annual_income
   - filer_status
   - tax_paid
2. Vehicle registrations
   - vehicle_id
   - owner_name
   - owner_address
   - make_model
   - engine_cc
   - estimated_value
   - registration_city
3. Property ownership
   - property_id
   - owner_name
   - owner_address
   - city
   - property_type
   - estimated_value
4. Utility bills
   - meter_id
   - consumer_name
   - service_address
   - monthly_bill
   - average_12_month_bill

Optional fifth dataset if time permits:

- Luxury travel logs or banking/KYC records.

Important:

- If CNIC is not supposed to be shared, do not include a universal CNIC key across all datasets.
- If IDs exist inside individual datasets, they should be dataset-local.

### Problem 2 Entity Resolution Pipeline

Recommended steps:

1. Normalize text.
   - lowercase
   - remove punctuation
   - normalize common prefixes/suffixes
   - normalize abbreviations
   - standardize address tokens
2. Block records to reduce comparisons.
   - by city
   - by phonetic or initial tokens
   - by address area
   - by father name where available
3. Compare candidate pairs.
   - name similarity
   - address similarity
   - phone/email if available
   - city match
   - father name similarity
   - embedding similarity if available
4. Produce match confidence.
   - exact/high/medium/low
   - avoid merging low-confidence matches automatically
5. Cluster matched records into resolved person entities.
6. Preserve source records and match explanations.

### Problem 2 Knowledge Graph Model

Recommended node types:

- `Person`
- `Vehicle`
- `Property`
- `Meter`
- `TaxReturn`
- `Address`
- `Organization` if needed

The image mentions only Person, Vehicle, Property, and Meter. `TaxReturn` and `Address` are recommended additions for clarity.

Recommended edges:

- `OWNS`
- `REGISTERED_AT`
- `HAS_METER`
- `FILED`
- `DECLARED_AT`
- `RESOLVED_FROM`
- `LOCATED_AT`

The image mentions owns, registered_at, filed_in, and declared_at. Naming can vary, but the meaning should remain consistent.

### Problem 2 Deviation Score

No official formula is present in the files or image.

A transparent MVP formula can be created, but must be labeled as a prototype heuristic.

Possible components:

- declared income
- estimated vehicle value
- total property value
- average monthly electricity bill
- tax paid
- filer status
- asset-to-income ratio
- utility-to-income ratio

Example heuristic idea:

- Higher score if declared income is low and lifestyle indicators are high.
- Higher score if tax paid is zero while assets are expensive.
- Higher score if multiple high-value assets are connected to the same resolved person.
- Lower score if income and lifestyle indicators are consistent.

Critical warning:

The score should be presented as `audit risk`, not `fraud probability`, unless validated ground truth exists.

### Problem 2 Explainability Requirements

For each flagged entity, show:

- Resolved person name.
- Source records that were linked.
- Match confidence and reason.
- Assets and utility indicators.
- Declared income and tax filing status.
- Deviation score.
- Score component breakdown.
- Natural-language audit trail.

Example explanation pattern:

`This entity was flagged because records linked with high confidence show low declared income, ownership of a high-value vehicle, and unusually high monthly utility spending.`

Do not state:

`This person is guilty of tax evasion.`

## User-Provided Example Dataset Image

The user provided another image at:

`/tmp/codex-clipboard-S6DJvd.png`

Important:

- The user explicitly said this image is only an example.
- It is not a confirmed dataset.
- It should be treated as a possible shape for synthetic or future uploaded data.
- Do not claim these files exist unless they are actually created or provided.

The image title:

`4 Synthetically Generated Pakistani Datasets`

Example datasets and columns shown:

### `fbr_tax_records.csv`

Source label:

`FBR Tax Declarations`

Example columns:

- `fbr_id`
- `full_name`
- `declared_income_pkr`
- `tax_paid_pkr`
- `filer_status`
- `reported_address`
- `phone_number`

### `excise_vehicles.csv`

Source label:

`Provincial Excise`

Example columns:

- `vehicle_reg_no`
- `owner_name`
- `engine_capacity_cc`
- `vehicle_make_model`
- `registration_year`
- `owner_address`

### `disco_consumption.csv`

Source label:

`Utility Providers (DISCO)`

Example columns:

- `meter_ref_no`
- `consumer_name`
- `installation_address`
- `avg_monthly_bill_pkr`
- `connection_type`

### `property_transfers.csv`

Source label:

`Real Estate Registry`

Example columns:

- `registry_no`
- `buyer_name`
- `seller_name`
- `property_address`
- `property_value_pkr`
- `transfer_date`
- `area_marla`
- `property_type`

## Additional Requirement: Proxy or Associate Ownership

User clarified that the system should handle cases where a wealthy or high-risk person may not hold all assets directly.

The system should support cases where:

- property is registered under a close associate
- vehicles are registered under relatives, employees, business partners, or household members
- utility meters are under another person's name but connected to the same address or asset cluster
- one person appears low-income but is connected to high-value assets through graph relationships
- a high-risk person may be using related people as proxies or nominees

Important wording:

- Use terms like `proxy ownership risk`, `associate-linked asset risk`, or `beneficial ownership signal`.
- Do not claim legal guilt.
- Do not claim confirmed beneficial ownership unless the source data proves it.
- The system should flag these patterns for audit review.

Recommended graph additions for this requirement:

- `Person`
- `Address`
- `Household`
- `Business`
- `Vehicle`
- `Property`
- `Meter`
- `TaxReturn`
- `PhoneNumber`

Recommended relationship additions:

- `SAME_ADDRESS_AS`
- `SHARES_PHONE_WITH`
- `HOUSEHOLD_MEMBER_OF`
- `ASSOCIATED_WITH`
- `BOUGHT_PROPERTY`
- `SOLD_PROPERTY`
- `OWNS_VEHICLE`
- `HAS_UTILITY_METER`
- `USES_ADDRESS`
- `POSSIBLE_PROXY_FOR`

Recommended explanation behavior:

- The UI should show direct risk separately from associate-linked risk.
- Example direct risk: low declared income plus high-value vehicle in the same person's name.
- Example associate-linked risk: low declared income person is connected to multiple high-value properties registered under people sharing the same address or phone number.
- Match confidence and relationship confidence must be visible.

## Hackathon-Provided Pipeline Slide

The user provided another image at:

`/tmp/codex-clipboard-bns8rQ.png`

The user said this was provided by the hackathon organizer/person.

Important:

- Treat this as stronger guidance than the user's earlier example-only dataset image.
- It defines the intended architecture at a high level.
- It still does not provide actual datasets, labels, scoring formulas, or implementation details.

The image title:

`3-Component AI Pipeline`

### Component 1: Entity Resolution Pipeline

Confirmed text from image:

- String-distance and semantic embeddings.
- Blocking and iterative deduplication.
- LLM-assisted name/address parsing.
- Handles Urdu-English mixed text.
- Output: unified entity IDs.

Implementation interpretation:

- Entity resolution should produce stable internal person/entity IDs.
- Matching should use both deterministic and semantic signals.
- Blocking is required for scalability.
- Deduplication should be iterative because new matches can reveal additional clusters.
- Urdu-English mixed text support should be included at least through normalization and transliteration-aware matching where feasible.
- LLM use should be constrained to parsing or explanation, not unverified matching claims.

### Component 2: Knowledge Graph Engine

Confirmed text from image:

- Graph DB: Neo4j or NetworkX.
- Nodes: Person, Vehicle, Property, Meter.
- Edges: owns, registered_at, filed_in.
- AI layer for anomaly detection.
- Output: graph of financial footprints.

Implementation interpretation:

- NetworkX is acceptable for the MVP if the goal is fast local graph construction and analysis.
- Neo4j is acceptable for a more database-oriented demo if time allows.
- The graph should preserve source evidence for each node and edge.
- The graph should support anomaly detection and relationship-based risk discovery.
- `TaxReturn`, `Address`, and possibly `PhoneNumber` are recommended additions even though the slide only lists Person, Vehicle, Property, and Meter.

### Component 3: Deviation Score and XAI

Confirmed text from image:

- Risk score 0-100 per entity.
- Compares income versus lifestyle signals.
- Dashboard.
- Visual graph plus text audit trail.
- Output: flagged profiles plus reasons.

Implementation interpretation:

- The final score must be per resolved entity.
- The score should be explainable and broken into components.
- Dashboard must show both graph view and text audit trail.
- Output should be flagged profiles with reasons, not legal conclusions.

### Alignment With Current Plan

The current recommended implementation aligns with this slide:

1. Dataset ingestion and column mapping.
2. Entity resolution to unified IDs.
3. Knowledge graph construction.
4. Direct and associate-linked deviation scoring.
5. Explainable dashboard with visual graph and audit trail.

The slide also reinforces that the MVP should prioritize:

- entity resolution quality
- graph construction
- risk score explainability
- dashboard usability

over a complex black-box GNN.

## Hackathon-Provided 100-Point Evaluation Rubric Slide

The user provided another image at:

`/tmp/codex-clipboard-0DJgne.png`

The slide title:

`Evaluation Rubric - 100 Points Total`

The user asked to analyze it.

Important:

- Treat this as hackathon-provided guidance for Problem 2 unless superseded by later official material.
- This rubric is more specific to the tax/graph problem than the generic PDF rubric.
- It divides evaluation evenly across four 25-point categories.

### Category 1: Technical Rigor and ML - 25 Points

Confirmed text from image:

- Custom model architectures.
- Sophisticated Entity Resolution.
- Handling noisy Urdu/English text.
- Avoiding hard-coded lookup tables.

Implementation implications:

- Do not build only rule-based exact matching.
- Include fuzzy string distance, blocking, probabilistic or weighted matching, semantic similarity where feasible, and confidence scoring.
- Include Urdu/English normalization or transliteration-aware handling.
- Avoid demos that only work because values are hardcoded.
- Store matching features and reasons for audit.
- Synthetic data should contain name/address noise to prove robustness.

### Category 2: Data Engineering and Scalability - 25 Points

Confirmed text from image:

- Pipeline latency and throughput.
- Could it handle 30M citizens?
- Proper DB indexing.
- Clean code architecture.

Implementation implications:

- The prototype must discuss and demonstrate scalable architecture, even if the hackathon demo uses small synthetic data.
- Use blocking/indexing to avoid all-to-all comparison.
- Persist normalized records and graph outputs in a structured database.
- Add indexes on canonical IDs, source row IDs, normalized names, city/area, phone hashes, address blocks, and graph node IDs.
- Measure pipeline runtime on synthetic data.
- Present scaling strategy for 30M citizens.
- Keep modular services: ingestion, mapping, ER, graph, scoring, API, UI.

### Category 3: Explainability and XAI - 25 Points

Confirmed text from image:

- AI must explain each risk score.
- Black-box models score poorly.
- Legal-grade defensible audit trails.
- Clear reasoning per flag.

Implementation implications:

- Every flag must include evidence, source rows, match confidence, scoring components, and explanation text.
- Prefer transparent scoring for MVP.
- If ML/embedding methods are used, their outputs should feed visible features and confidence, not opaque final accusations.
- The UI should show why each person was matched and why each risk score was produced.
- Output must be audit-risk language, not guilt/fraud conclusions.

### Category 4: Product Usability and Pitch - 25 Points

Confirmed text from image:

- Dashboard UX for non-tech auditors.
- Functional prototype, not notebook.
- Quality of 5-minute pitch.
- Live Q&A performance.

Implementation implications:

- A notebook-only solution is insufficient.
- Build a working dashboard.
- Prioritize simple auditor workflows:
  - upload data
  - review schema mappings
  - run pipeline
  - inspect flagged profiles
  - view graph
  - read audit trail
  - export report
- Prepare a 5-minute pitch and likely Q&A answers.
- Use plain language in UI.

### Rubric-Driven Build Priorities

The project should optimize for all four categories:

1. Entity resolution quality and noisy Pakistani text handling.
2. Scalable, indexed data pipeline.
3. Defensible XAI and audit trails.
4. Functional dashboard for non-technical auditors.

This rubric makes the following anti-patterns especially risky:

- hardcoded examples
- exact-name-only matching
- black-box risk scores
- notebook-only demo
- no runtime/scaling story
- no source evidence behind flags
- no Urdu/English text handling
- no live dashboard

### External Technical References Checked

These references were checked during planning:

- Splink official documentation describes probabilistic record linkage for deduplication and linking records without unique identifiers.
- NetworkX official documentation describes Python tools for creation, manipulation, and study of complex networks.
- Neo4j Graph Data Science documentation describes graph algorithms and ML procedures, including anomaly and fraud detection use cases.
- NIST AI Risk Management Framework emphasizes trustworthy AI characteristics such as validity, reliability, accountability, transparency, explainability, interpretability, privacy enhancement, and fairness.

## Problem Choice Comparison

### Problem 1 Strengths

- Dataset is present locally.
- Business workflow is clear.
- Easier to demo end-to-end.
- Strong alignment with Round 1 technical implementation.
- Strong alignment with Round 2 value proposition.
- Can be implemented as a realistic enterprise SaaS-style prototype.

### Problem 1 Risks

- Needs a sample RFP document, but none is present locally.
- Capability library is shallow.
- Win-probability model may be weak because the dataset is small and synthetic.
- `Score (%)` may cause target leakage if used incorrectly.

### Problem 2 Strengths

- More innovative.
- Strong social and government impact story.
- Better fit for knowledge graph and explainable AI themes.
- Can be visually compelling if the graph UI is good.

### Problem 2 Risks

- No dataset is present locally.
- Entity resolution is technically difficult.
- Ground truth is required to report precision/recall honestly.
- A GNN is likely too much for a short hackathon unless heavily simplified.
- Must avoid ethical/legal overclaims.

### Current Recommendation

If the goal is to maximize probability of a strong hackathon demo:

- Prefer Problem 1.

If the team specifically wants a more ambitious AI/graph challenge:

- Problem 2 is viable, but should use a transparent synthetic dataset, deterministic matching logic, and explainable graph scoring rather than trying to overbuild a full GNN system.

## Sources Used

Local source files:

- `CUST Hackathon 2026_Rubrics.pdf`
- `CUST Hackathon Problem#1 (TEKROWE).pdf`
- `CUST Hackathon Problem#2 (CIKLUM).pdf`
- `Problem#1_Sample_Datasets (TEKROWE).xlsx`
- User-provided image: `/tmp/codex-clipboard-9UBae7.png`

External documentation referenced during analysis:

- Neo4j documentation: graph databases store data as nodes, relationships, and properties.
- NetworkX documentation: Python package for creation, manipulation, and study of complex networks.

No external dataset has been downloaded or added to the workspace.

## Open Questions

These are not answered by the current files:

1. Which problem will be implemented?
2. What tech stack should be used?
3. Is internet access allowed during the hackathon?
4. Can generated synthetic data be used for Problem 2?
5. Will the user provide sample RFP documents for Problem 1?
6. Does the team need a working backend, frontend, or both?
7. Does the final deliverable need a pitch deck, report, deployed app, or local demo only?
8. Are LLM API keys available?
9. Should the prototype be optimized for judging demo, technical depth, or production realism?

## Recommended Next Context Updates

When decisions are made, append them here:

- Chosen problem.
- Chosen stack.
- Dataset source.
- Demo flow.
- Final scoring formula.
- UI screens.
- Known limitations.
- Validation method.

## Decision Update: Chosen Problem

User has chosen Problem 2:

`Graph AI for Broadening the National Tax Net`

Reason stated by user:

- It is harder than Problem 1.
- Fewer teams may choose it.
- It is differentiated.
- No dataset is currently available.
- The system should be designed to work with arbitrary provided datasets, not only one fixed synthetic dataset.

Important note:

It cannot be verified from local files whether fewer teams will actually choose Problem 2. That is a reasonable strategic guess because this problem has higher data, ML, entity resolution, graph, explainability, and ethics complexity, but it is not confirmed.
