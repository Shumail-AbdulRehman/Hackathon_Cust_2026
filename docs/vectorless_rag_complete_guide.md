# Vectorless RAG: Complete Evaluation & Implementation Guide
## PageIndex + Proxy-Pointer — What It Is, When to Use It, How to Build It

---

## 1. What Is Vectorless RAG?

Traditional RAG has a core assumption that has gone unchallenged for years: "embed your documents, find the nearest vectors." It works. Until it doesn't.

**Vectorless RAG (PageIndex)** — released September 2025 by VectifyAI — throws out that entire pipeline. No embeddings, no vector DB, no chunking. Instead, it builds a **hierarchical tree index** of your document's natural structure and uses an LLM to *reason* through it — the same way you read a book by checking the table of contents, then flipping to the right chapter.

The core insight is borrowed from AlphaGo: instead of searching exhaustively, use a learned strategy to navigate the search space intelligently.

---

## 2. Why Traditional Vector RAG Fails on Structured Documents

The standard pipeline: chunk → embed → cosine similarity → top-k context → generate.

**Where it breaks:**

- **Chunking destroys structure.** A 512-token window doesn't care about chapter boundaries, table headers, or section flow. A number in a cell is meaningless without its column header — and that header is often in a different chunk.
- **Semantic similarity ≠ true relevance.** In finance/legal/medical docs, hierarchy, page references, and logical flow matter more than cosine distance. Asking "What does Table A2.1.1 say?" returns everything *about* tables — not the actual table.
- **Context overload.** Feeding 300 pages even into a 128k context window causes loss of focus and generically vague answers.
- **No traceability.** You can't trace which section produced a claim. In healthcare AI, this is a critical safety problem.

**The numbers bear this out:** traditional vector RAG scores ~50% on FinanceBench. PageIndex scores 98.7% on the same benchmark.

---

## 3. How PageIndex Works (Two Phases)

### Phase 1: Indexing — Build the Tree (Once per Document)

The document is fed to a reasoning LLM. The LLM analyzes heading structure and builds a hierarchical tree. Every node gets:

```json
{
  "node_id": "0011",
  "title": "Chapter 1. Deceptive Strength",
  "summary": "Covers South Asia's growth outlook, inflation trends, financial vulnerabilities...",
  "line_num": 621,
  "nodes": [
    {
      "node_id": "0012",
      "title": "Introduction",
      "summary": "Summarizes key themes including regional growth...",
      "line_num": 625
    }
  ]
}
```

**No fixed chunk size. No embeddings. Pure LLM-driven structural detection.**

### Phase 2: Querying — Reason Over the Tree (Per Query)

1. User asks a question.
2. The LLM receives the **entire tree of summaries** (titles + summaries only — tiny context).
3. LLM reasons about which nodes are relevant and returns node IDs.
4. PageIndex uses the line boundaries in those nodes to slice the **exact, contiguous, full section** from the original document.
5. That section (not chunks) goes to the final answer-generation LLM.

**Result:** dramatically smaller context, exact page references, reasoning-based relevance instead of similarity matching.

---

## 4. Benchmark & Accuracy Evaluation

### FinanceBench Results

| System | Accuracy on FinanceBench |
|---|---|
| Traditional Vector RAG | ~50% |
| GPT-4o (standalone) | ~67% |
| Perplexity | ~72% |
| **PageIndex (Mafin 2.5)** | **98.7%** |

### Why the gap is so large

- **Structural queries fail completely in vector RAG.** "What does Annexure Table A2.1.1 say?" → vector RAG retrieves everything mentioning tables but misses the actual content. PageIndex navigates directly to node `0131` labelled "ANNEX TABLE A2.1.1" and returns the full section verbatim.
- **Chapter-level queries are unreachable.** "What questions does Chapter 2 answer?" → vector RAG retrieves every fragment mentioning "Chapter 2" across the doc. PageIndex reads the tree, finds the "Questions" node inside Chapter 2, returns that exact section.
- **Table headers get detached from their data.** Vector chunking separates table headers from values. PageIndex keeps entire tables intact inside their nodes.

### The Benchmark Caveat

The 98.7% figure is on FinanceBench — a benchmark of **deep, structured, single-document** financial reports. This is not a general RAG benchmark. On broader QA datasets (BEIR, MTEB), the picture is different. The benchmark was designed to highlight exactly the failure mode that PageIndex solves.

---

## 5. Real Trade-Offs (No Sugarcoating)

This is the most important section. There is zero public data from VectifyAI on latency, throughput, or cost per query.

### Cost of Indexing

For a 131-page document, PageIndex generates ~137 structural nodes. That means:
- **137 LLM API calls** just for indexing (one summary per node)
- Using GPT-4.1: approximately **$10–15 per document** for indexing
- Using GPT-4.1 Mini or Gemini Flash: **~$1–2 per document** (90% cost reduction, some quality tradeoff)
- Indexing time: **5–10 minutes per document**

Compare to vector RAG: 30 seconds, $0.01–0.05 in embedding API costs.

### Cost of Querying

Every query runs an LLM reasoning step over the tree of summaries (just titles + summaries, not full text). This adds one extra LLM call per query on top of the final synthesis call. Standard vector RAG has only one LLM call (synthesis).

### Scalability Ceiling

**PageIndex's tree-based approach cannot practically scale to multi-document scenarios.** For a 500-document knowledge base that updates weekly: ~7,000 LLM calls just for initial indexing, and per-document tree traversal at query time. It's a non-starter for high-volume production systems.

### Where It Makes Sense

| Use Case | Verdict |
|---|---|
| Deep Q&A on 1–20 critical structured documents | ✅ Use PageIndex |
| Finance/legal/medical/regulatory doc analysis | ✅ Use PageIndex |
| Healthcare AI on clinical guidelines or reports | ✅ Strong fit |
| 500+ document enterprise knowledge base | ❌ Impractical |
| Customer support FAQ, unstructured text | ❌ Overkill |
| Weekly-updating document corpus | ❌ Re-indexing cost too high |

---

## 6. The Real Answer: Proxy-Pointer RAG (Best of Both Worlds)

Researchers at Towards Data Science (April 2026) built and tested a hybrid called **Proxy-Pointer RAG** that closes the quality gap with PageIndex while keeping the cost and scalability of standard vector RAG.

**Verdict from head-to-head testing:** Proxy-Pointer matches or beats PageIndex on **8 out of 10 queries** at the cost of standard vector RAG.

The core insight: **you don't need an LLM to encode document structure. You just need to encode structure into the embeddings themselves.**

Five zero-cost engineering techniques replace the expensive LLM-navigated tree:

### Technique 1: Skeleton Tree (No LLM, No Cost)

PageIndex's tree parser doesn't actually need an LLM. The heading detection is regex-based (finds Markdown `#`, `##`, `###` headers). The LLM is only used to summarize. Build the structure without summaries:

```python
# Zero cost — pure regex parsing, runs in milliseconds
pageindex = PageIndex(doc_path, enable_ai=False)
tree = pageindex.build_structure()
# Result: same 137 nodes, same nesting, same line numbers — no summaries
```

### Technique 2: Breadcrumb Injection (Zero Cost, Big Impact)

Standard vector RAG embeds raw text with no structural context. A chunk from Chapter 1 has no idea it belongs to Chapter 1. Add the full ancestry path before embedding:

```python
# Before:
"While private investment growth has slowed in both South Asia and other EMDEs..."

# After breadcrumb injection:
"[Chapter 1. Deceptive Strength > Economic Activity > BOX 1.1 Accelerating Private Investment]
While private investment growth has slowed in both South Asia and other EMDEs..."

# Build breadcrumb from tree node ancestry
current_crumb = f"{parent_breadcrumb} > {node_title}"
enriched_text = f"[{current_crumb}]\n{section_text}"
chunks = text_splitter.split_text(enriched_text)
```

Now the embedding vector encodes both content AND structural location. A query about "Chapter 1" retrieves the right chunks because "Chapter 1. Deceptive Strength" is embedded in every chunk from that chapter.

### Technique 3: Metadata Pointers (Chunks Are Proxies, Not Context)

In standard RAG, retrieved chunks ARE the context. In Proxy-Pointer, chunks identify which section is relevant, then the full section is fetched using metadata pointers:

```python
# Every chunk carries structural metadata
metadata = {
    "doc_id": "report_2024",
    "node_id": "0012",
    "title": "Chapter 1 > Introduction",
    "start_line": 624,
    "end_line": 672
}

# At retrieval time:
# 1. FAISS finds top-k matching chunks
# 2. Deduplicate by (doc_id, node_id) to get unique sections
# 3. Fetch full sections via start_line:end_line pointers
# 4. LLM gets complete, pristine sections — not fragments

retrieved_nodes = deduplicate_by_node_id(faiss_results)
full_sections = [fetch_lines(doc, node.start_line, node.end_line)
                 for node in retrieved_nodes]
```

### Technique 4: Structure-Guided Chunking (No Blind Sliding Windows)

Instead of a sliding window across the entire document, chunk within each node's boundaries:

```python
# Standard RAG: blind sliding window
# [====chunk1====][====chunk2====]  (ignores section boundaries)

# Proxy-Pointer: chunk within node boundaries
for node in tree.walk():
    section_text = extract_lines(doc, node.start_line, node.end_line)
    if len(section_text) < MIN_CHARS:
        continue  # skip nearly-empty structural nodes
    chunks = text_splitter.split_text(f"[{breadcrumb}]\n{section_text}")
    for chunk in chunks:
        embed_with_metadata(chunk, node_metadata)
```

Guarantees: chunks never cross section boundaries, each chunk belongs to exactly one node, breadcrumbs are accurate per-chunk.

### Technique 5: Noise Filtering (Removes the Worst Retrieval Distractors)

Table of contents, executive summary, abbreviations, and acknowledgments contaminate the vector space — they match almost every query without providing useful content:

```python
NOISE_TITLES = {
    "contents", "table of contents", "abbreviations",
    "acknowledgments", "foreword", "executive summary", "references"
}

for node in tree.walk():
    if node.title.strip().lower() in NOISE_TITLES:
        continue  # Skip entirely
```

Removing 7 nodes on a 131-page document immediately fixed the most common retrieval failure mode (returning executive summary instead of actual content).

---

## 7. Complete Cost Comparison

| Metric | PageIndex | Proxy-Pointer | Standard Vector RAG |
|---|---|---|---|
| Indexing LLM calls | ~137 per doc | **0** | 0 |
| Indexing time | 5–10 min/doc | **< 30 sec/doc** | < 30 sec/doc |
| Indexing cost ($/doc) | $10–15 (GPT-4.1) | **~$0.01** | ~$0.01 |
| Retrieval quality | ★★★★★ | **★★★★★ (8/10 vs PageIndex)** | ★★★☆☆ |
| Multi-doc scalability | Poor | **Excellent** | Excellent |
| Structural awareness | Full (LLM-navigated) | **High (breadcrumb-encoded)** | None |
| Index rebuild on update | Expensive | **Cheap (re-embed affected nodes)** | Cheap |
| Explainability | High | **High** | Low |

---

## 8. Decision Framework: Which to Use

```
Is your use case document-centric QA on structured/hierarchical docs?
├── No (general knowledge base, unstructured FAQ, chatbot)
│   └── → Standard Vector RAG
│
└── Yes
    ├── How many documents?
    │   ├── 1–20 critical documents (annual reports, contracts, guidelines)
    │   │   └── Is re-indexing cost acceptable? (static docs, high accuracy need)
    │   │       ├── Yes → PageIndex (full vectorless RAG)
    │   │       └── No  → Proxy-Pointer RAG
    │   │
    │   └── 20+ documents OR frequently updating corpus
    │       └── → Proxy-Pointer RAG
    │
    └── Is perfect structural navigation essential? (audit, compliance, legal)
        ├── Yes + small doc set → PageIndex
        └── Yes + large doc set → Proxy-Pointer RAG
```

**For your healthcare AI project (agentic-caregivers):** Clinical guidelines, patient records, drug interaction sheets, and medical reports are exactly the highly-structured, hierarchically-organized documents where Proxy-Pointer RAG delivers major gains over standard RAG. The explainability (section-level provenance) is also critical for medical AI. **Proxy-Pointer is the right choice unless your doc set is tiny and static.**

---

## 9. Installation & Setup

### Install PageIndex

```bash
# With uv (your setup)
uv add pageindex

# Optional: for agentic mode
uv add openai-agents
```

### Install dependencies for Proxy-Pointer

```bash
uv add pageindex faiss-cpu sentence-transformers langchain-text-splitters polars
# OR for GPU:
uv add pageindex faiss-gpu sentence-transformers langchain-text-splitters polars
```

---

## 10. PageIndex Implementation (Full Vectorless RAG)

```python
from pageindex import PageIndex

# ── Step 1: Index document (expensive — do once, cache result) ────────────────
pi = PageIndex("medical_guideline.md", enable_ai=True)  # enable_ai=True → LLM summaries
tree = pi.build_structure()

# Inspect the tree
pi.print_tree()
# └── Medical Guideline (root)
#     ├── Chapter 1: Diagnosis Criteria  (node: 0001)
#     │   ├── Section 1.1: Symptoms      (node: 0002)
#     │   └── Section 1.2: Tests         (node: 0003)
#     └── Chapter 2: Treatment Protocols (node: 0004)

# ── Step 2: Query (LLM tree navigation per query) ─────────────────────────────
result = pi.query(
    question="What are the diagnostic criteria for Stage 2 hypertension?",
    model="gpt-4o-mini"   # Use cheaper model for tree navigation step
)

print(result.answer)
print(result.source_nodes)   # ['0002', '0003'] — exact section IDs
print(result.source_pages)   # line ranges used for traceability
```

### Agentic Mode (OpenAI Agents SDK)

```bash
python3 examples/agentic_vectorless_rag_demo.py
```

---

## 11. Proxy-Pointer RAG Implementation (Full Pipeline)

This is the recommended implementation for most cases.

### Step 1: Convert Document to Markdown

Structure must be preserved. Use:
- **Adobe PDF Extract API** — best quality, preserves tables/charts
- **pymupdf4llm** — good open-source option
- **marker-pdf** — fast, open-source, good on scientific PDFs

```bash
uv add pymupdf4llm
```

```python
import pymupdf4llm

md_text = pymupdf4llm.to_markdown("clinical_guidelines.pdf")
with open("clinical_guidelines.md", "w") as f:
    f.write(md_text)
```

### Step 2: Build Skeleton Tree (Zero Cost)

```python
from pageindex import PageIndex

pi = PageIndex("clinical_guidelines.md", enable_ai=False)  # NO LLM calls
tree = pi.build_structure()
# Identical structure to the summarized tree — same nodes, same line numbers
# Cost: $0. Time: < 1 second.
```

### Step 3: Ingest with Breadcrumbs + Metadata Pointers

```python
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

NOISE_TITLES = {
    "contents", "table of contents", "abbreviations",
    "acknowledgments", "foreword", "executive summary", "references"
}

def get_doc_lines(doc_path):
    with open(doc_path) as f:
        return f.readlines()

def build_breadcrumb(node, parent_crumb=""):
    return f"{parent_crumb} > {node['title']}" if parent_crumb else node['title']

def walk_tree(node, doc_lines, parent_crumb="", chunks=[], metadatas=[]):
    title = node.get("title", "").strip()
    current_crumb = build_breadcrumb(node, parent_crumb)

    # Skip noise nodes
    if title.lower() in NOISE_TITLES:
        return

    start = node.get("line_num", 0)
    # Get end line from next sibling or parent end
    end = node.get("end_line", len(doc_lines))

    # Extract section text
    section_lines = doc_lines[start:end]
    section_text = "".join(section_lines).strip()

    if len(section_text) > 100:  # Skip nearly-empty structural headers
        # Inject breadcrumb before embedding
        enriched = f"[{current_crumb}]\n{section_text}"
        for chunk in splitter.split_text(enriched):
            chunks.append(chunk)
            metadatas.append({
                "doc_id": "clinical_guidelines",
                "node_id": node.get("node_id", ""),
                "title": title,
                "breadcrumb": current_crumb,
                "start_line": start,
                "end_line": end,
            })

    # Recurse into children
    for child in node.get("nodes", []):
        walk_tree(child, doc_lines, current_crumb, chunks, metadatas)

# Run ingestion
doc_lines = get_doc_lines("clinical_guidelines.md")
all_chunks = []
all_meta = []
walk_tree(tree, doc_lines, chunks=all_chunks, metadatas=all_meta)

# Embed all chunks
print(f"Embedding {len(all_chunks)} chunks...")
embeddings = model.encode(all_chunks, batch_size=64, normalize_embeddings=True, show_progress_bar=True)

# Build FAISS index
dim = embeddings.shape[1]
index = faiss.IndexFlatIP(dim)  # Inner Product = cosine when normalized
index.add(embeddings.astype(np.float32))

# Save index + metadata
faiss.write_index(index, "proxy_pointer.index")
import json
with open("proxy_pointer_meta.json", "w") as f:
    json.dump({"chunks": all_chunks, "metadatas": all_meta}, f)

print(f"Index built: {index.ntotal} vectors")
```

### Step 4: Retrieval with Pointer Follow-Through

```python
import faiss, json, numpy as np
from sentence_transformers import SentenceTransformer

# Load index
index = faiss.read_index("proxy_pointer.index")
with open("proxy_pointer_meta.json") as f:
    store = json.load(f)
chunks, metadatas = store["chunks"], store["metadatas"]
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def retrieve(query: str, doc_lines: list, top_k: int = 10) -> list[dict]:
    # Embed query
    q_emb = model.encode([query], normalize_embeddings=True).astype(np.float32)

    # FAISS search — get top_k matching chunks (proxies)
    scores, indices = index.search(q_emb, top_k)

    # Deduplicate by (doc_id, node_id) — chunks are proxies, not context
    seen = set()
    unique_nodes = []
    for idx in indices[0]:
        meta = metadatas[idx]
        key = (meta["doc_id"], meta["node_id"])
        if key not in seen:
            seen.add(key)
            unique_nodes.append(meta)

    # Follow pointers — fetch full sections from original document
    results = []
    for node_meta in unique_nodes:
        full_section = "".join(doc_lines[node_meta["start_line"]:node_meta["end_line"]])
        results.append({
            "title": node_meta["title"],
            "breadcrumb": node_meta["breadcrumb"],
            "node_id": node_meta["node_id"],
            "content": full_section,  # complete, pristine section
        })
    return results

# ── Usage ─────────────────────────────────────────────────────────────────────
doc_lines = get_doc_lines("clinical_guidelines.md")

retrieved = retrieve(
    query="What are the recommended first-line treatments for Type 2 diabetes?",
    doc_lines=doc_lines,
    top_k=10
)

# Each result = a complete document section, with full structural context
for r in retrieved:
    print(f"[{r['breadcrumb']}]")
    print(r['content'][:300])
    print("---")
```

### Step 5: Answer Generation (Full RAG Pipeline)

```python
from anthropic import Anthropic  # or openai

client = Anthropic()

def answer(query: str, doc_lines: list) -> str:
    retrieved_sections = retrieve(query, doc_lines, top_k=8)

    # Build context from full sections (not chunks)
    context = "\n\n---\n\n".join([
        f"[Section: {r['breadcrumb']}]\n{r['content']}"
        for r in retrieved_sections
    ])

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": f"""Answer the question using ONLY the provided document sections.
Cite the section title for every claim.

QUESTION: {query}

DOCUMENT SECTIONS:
{context}

Answer:"""
        }]
    )
    return response.content[0].text

# Run
doc_lines = get_doc_lines("clinical_guidelines.md")
print(answer(
    "What are the diagnostic criteria for hypertensive crisis?",
    doc_lines
))
```

---

## 12. Evaluation Metrics

Once your pipeline is running, evaluate these three axes:

| Metric | How to Measure | Target |
|---|---|---|
| **Structural Recall** | % of structural queries (chapter-level, table-level) answered correctly | > 85% |
| **Factual Accuracy** | LLM-as-judge on 50 factual Q&A pairs | > 90% |
| **Context Precision** | % of retrieved sections that are actually relevant | > 70% |
| **Traceability** | % of answers with correct section citations | 100% (for medical AI) |
| **Latency** | Time from query to answer | < 3s (vector), < 10s (PageIndex) |

### Quick Evaluation Harness

```python
import polars as pl

# Create test pairs: question, expected_section_title
test_cases = pl.DataFrame({
    "question": [
        "What are the first-line treatments for Type 2 diabetes?",
        "What does Table 3.2 say about dosage?",
        "What questions does Chapter 4 answer?",
    ],
    "expected_node_title": [
        "Treatment Protocols > First-Line Therapy",
        "TABLE 3.2",
        "Questions",
    ]
})

# Run retrieval and check if expected section was retrieved
results = []
for row in test_cases.iter_rows(named=True):
    retrieved = retrieve(row["question"], doc_lines, top_k=10)
    retrieved_titles = [r["title"].lower() for r in retrieved]
    hit = any(row["expected_node_title"].lower() in t for t in retrieved_titles)
    results.append({"question": row["question"], "hit": hit})

eval_df = pl.DataFrame(results)
print(f"Structural Recall: {eval_df['hit'].mean():.1%}")
```

---

## 13. Summary Recommendation

| Scenario | Recommendation |
|---|---|
| 1–10 static critical docs, highest accuracy needed | Pure PageIndex |
| 10–500 docs, mix of structured/unstructured | **Proxy-Pointer RAG** ← for most cases |
| 500+ docs, chatbot, support KB | Standard Vector RAG |
| Healthcare AI with structured guidelines | **Proxy-Pointer RAG** (explainability + accuracy) |

Proxy-Pointer is the practical production answer. It delivers the structural awareness of PageIndex at the cost and scalability of standard vector RAG, with zero LLM calls during indexing and no extra LLM calls per query.
