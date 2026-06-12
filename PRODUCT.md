# Product Context

## Name

TaxNet XAI

## Register

product

## Purpose

TaxNet XAI is an auditor-facing prototype for Pakistan-focused tax compliance screening. It ingests civic datasets, resolves identities without relying on a shared CNIC, builds a graph of financial footprint evidence, and flags entities for audit review with explainable deviation scores.

## Primary Users

- Non-technical tax auditors.
- Data analysts supporting public-sector compliance teams.
- Hackathon judges evaluating technical rigor, scalability, explainability, and usability.

## Product Principles

- Evidence first: every flag must link back to source rows.
- Audit-risk language only: do not claim legal guilt or confirmed fraud.
- Flexible ingestion: datasets may have different column names and shapes.
- Transparent scoring: black-box scores are avoided in the MVP.
- Graph reasoning: direct ownership and associate-linked ownership are treated separately.

## Anti-References

- Notebook-only demo.
- Exact-name matching.
- Hardcoded sample lookup tables.
- Black-box risk scores.
- Dashboards that require a data scientist to interpret the result.

