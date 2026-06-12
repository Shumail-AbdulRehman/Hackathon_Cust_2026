#!/usr/bin/env python3
"""file1.py — Download Pakistan tax laws and build a vectorless RAG index.

Run on the server:
    uv run python file1.py

Outputs (in server_artifacts/law_rag/):
    law_index.faiss      FAISS inner-product index (cosine after normalization)
    law_chunks.jsonl     One JSON object per chunk
    law_metadata.jsonl   One JSON object per chunk with breadcrumb / pointer info

The script is idempotent: completed stages are skipped unless --force is passed.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from server_utils import (
    download_if_missing,
    is_checkpoint_complete,
    load_checkpoint,
    log as _log,
    read_jsonl,
    save_checkpoint,
    write_jsonl,
)

# Optional progress bars; fallback to no-op if tqdm is missing.
try:
    from tqdm import tqdm
except Exception:  # pragma: no cover

    def tqdm(iterable=None, **kwargs):  # type: ignore[misc]
        return iterable


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

STAGE = "file1"

ROOT = Path(__file__).resolve().parent
ARTIFACTS_DIR = ROOT / "server_artifacts" / "law_rag"
PDFS_DIR = ARTIFACTS_DIR / "pdfs"
MD_DIR = ARTIFACTS_DIR / "markdown"
INDEX_PATH = ARTIFACTS_DIR / "law_index.faiss"
CHUNKS_PATH = ARTIFACTS_DIR / "law_chunks.jsonl"
META_PATH = ARTIFACTS_DIR / "law_metadata.jsonl"

# Embedding model. all-MiniLM-L6-v2 is small, fast, and good enough for
# retrieving legal sections. It produces 384-dimensional vectors.
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
VECTOR_DIM = 384

# Chunking parameters. We chunk *within* a section, never across sections.
CHUNK_WORDS = 300
CHUNK_OVERLAP = 50
MIN_SECTION_WORDS = 20

# Direct PDF links confirmed by the user.
LAW_URLS: list[dict[str, str]] = [
    {
        "name": "Income Tax Ordinance 2001",
        "url": "https://download1.fbr.gov.pk/Docs/2026226162211364IncomeTaxOrdinance2001-Amended-20.02.2026.pdf",
        "filename": "income_tax_ordinance_2001.pdf",
    },
    {
        "name": "Income Tax Rules 2002",
        "url": "https://download1.fbr.gov.pk/Docs/2023112416114319348IncomeTaxRules2002AmendedUpto24.11.2023.pdf",
        "filename": "income_tax_rules_2002.pdf",
    },
    {
        "name": "Tax Laws Amendment Act 2024",
        "url": "https://download1.fbr.gov.pk/Docs/202457145950700TaxLaws(Amendment)Act2024.pdf",
        "filename": "tax_laws_amendment_act_2024.pdf",
    },
    {
        "name": "Tax Amendment Ordinance 2002",
        "url": "https://download1.fbr.gov.pk/Docs/20223314306805TaxAmendmentOrdinance2002.pdf",
        "filename": "tax_amendment_ordinance_2002.pdf",
    },
    {
        "name": "Finance Act 2025",
        "url": "https://download1.fbr.gov.pk/Docs/2025629106147620FInanceAct2025.pdf",
        "filename": "finance_act_2025.pdf",
    },
    {
        "name": "Sales Tax Act 1990",
        "url": "https://download1.fbr.gov.pk/Docs/202586148252375SalesTaxActupdatedupto2025-26.pdf",
        "filename": "sales_tax_act_1990.pdf",
    },
    {
        "name": "FED Act 2005",
        "url": "https://download1.fbr.gov.pk/Docs/202588138517680FEDAct,2005withindexupdatedupto30-06-2025.pdf",
        "filename": "fed_act_2005.pdf",
    },
    {
        "name": "FED Rules 2005",
        "url": "https://download1.fbr.gov.pk/Docs/2023111018112130929FED-Rules-2005-updated-upto-31.10.2023.pdf",
        "filename": "fed_rules_2005.pdf",
    },
    {
        "name": "Customs Act 1969",
        "url": "https://download1.fbr.gov.pk/Docs/20258121285942396CustomsAct1969(June2025)-(12.8.25).pdf",
        "filename": "customs_act_1969.pdf",
    },
    {
        "name": "Customs Rules SRO 450(I) 2001",
        "url": "https://download1.fbr.gov.pk/Docs/2023102014103110714Customs-Rules-SRO-450(I)-2001.pdf",
        "filename": "customs_rules_sro_450_2001.pdf",
    },
    {
        "name": "Sales Tax Rules 2006",
        "url": "https://download1.fbr.gov.pk/Docs/2025881385446623STR-2006-UpdatedUpto06-08-2025(ver-iv).pdf",
        "filename": "sales_tax_rules_2006.pdf",
    },
    {
        "name": "Anti Money Laundering Second Amendment Act 2020",
        "url": "https://download1.fbr.gov.pk/Docs/2020918159228949Final-Anti-MoneyLaundering(SecondAmendment)Act,2020_amendments-1.pdf",
        "filename": "aml_second_amendment_act_2020.pdf",
    },
    {
        "name": "Anti Terrorism 3rd Amendment Act",
        "url": "https://download1.fbr.gov.pk/Docs/20209181495332682Anti_terrorism_3rd_amendment_aj.pdf",
        "filename": "anti_terrorism_3rd_amendment.pdf",
    },
    {
        "name": "Public Finance Management Act 2019",
        "url": "https://download1.fbr.gov.pk/Docs/2019921194439879PublicFinanceManagementAct_2019.pdf",
        "filename": "public_finance_management_act_2019.pdf",
    },
    {
        "name": "Single Window Act",
        "url": "https://download1.fbr.gov.pk/Docs/20214261345351407SingleWindowAct.pdf",
        "filename": "single_window_act.pdf",
    },
    {
        "name": "Foreign Assets Declaration and Repatriation Act 2018",
        "url": "https://download1.fbr.gov.pk/Docs/20186131562020770ForeignAssets(DeclarationandRepatriation)Act,2018.pdf",
        "filename": "foreign_assets_declaration_act_2018.pdf",
    },
    {
        "name": "Voluntary Declaration of Domestic Assets Act 2018",
        "url": "https://download1.fbr.gov.pk/Docs/20186131562119310VoluntaryDeclarationofDomesticAssetsAct,2018.pdf",
        "filename": "voluntary_declaration_domestic_assets_act_2018.pdf",
    },
    {
        "name": "Assets Declaration Ordinance Gazette",
        "url": "https://download1.fbr.gov.pk/Docs/20195251351512475AssetsDeclarationOrdinanceGazettecopy.pdf",
        "filename": "assets_declaration_ordinance_gazette.pdf",
    },
    {
        "name": "Benami Transactions Rules 2019",
        "url": "https://download1.fbr.gov.pk/SROs/2019311153296811SRO326-2019BenamiTransactionsRules2019.pdf",
        "filename": "benami_transactions_rules_2019.pdf",
    },
    {
        "name": "Presidential Ordinance 1 July 2019",
        "url": "https://download1.fbr.gov.pk/Docs/2019721973745979PresidentialOrdinance1July2019.pdf",
        "filename": "presidential_ordinance_1_july_2019.pdf",
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def log(message: str) -> None:
    _log(STAGE, message)


def pdf_to_markdown(pdf_path: Path, md_path: Path) -> None:
    """Convert a PDF file to Markdown, preserving heading structure."""
    from pymupdf4llm import to_markdown

    md_path.parent.mkdir(parents=True, exist_ok=True)
    text = to_markdown(str(pdf_path))
    md_path.write_text(text, encoding="utf-8")


# Regex patterns for detecting headings in Pakistani legal text.
HEADING_PATTERNS = [
    re.compile(r"^(CHAPTER\s+[IVXLC0-9]+[A-Z]?)\b", re.IGNORECASE),
    re.compile(r"^(PART\s+[IVXLC0-9]+[A-Z]?)\b", re.IGNORECASE),
    re.compile(r"^(SCHEDULE\s*[IVXLC0-9A-Z]*)\b", re.IGNORECASE),
    re.compile(r"^Section\s+(\d+[A-Z]*)\.?\s*", re.IGNORECASE),
    re.compile(r"^(\d+[A-Z]*)\.\s+\S"),  # e.g. "111. Unexplained income"
    re.compile(r"^\((\d+[A-Z]*)\)\s+\S"),  # e.g. "(1) Where any amount..."
]


def is_heading(line: str) -> tuple[bool, str]:
    """Return (True, normalized_heading) if the line looks like a legal heading."""
    stripped = line.strip()
    if not stripped:
        return False, ""
    for pattern in HEADING_PATTERNS:
        match = pattern.match(stripped)
        if match:
            return True, stripped
    return False, ""


def build_section_tree(text: str) -> list[dict[str, Any]]:
    """Parse a legal Markdown/text file into a flat list of sections with breadcrumbs."""
    lines = text.splitlines()
    sections: list[dict[str, Any]] = []
    stack: list[tuple[int, str]] = []  # (level, title)

    current_title = "INTRODUCTION"
    current_body: list[str] = []

    def level_from_heading(heading: str) -> int:
        hlower = heading.lower()
        if hlower.startswith("chapter") or hlower.startswith("part") or hlower.startswith("schedule"):
            return 1
        if hlower.startswith("section"):
            return 2
        if re.match(r"^\(\d+[A-Z]*\)", heading):
            return 3
        if re.match(r"^\d+[A-Z]*\.", heading):
            return 2
        return 4

    def flush_section() -> None:
        body_text = "\n".join(current_body).strip()
        if body_text or current_title != "INTRODUCTION":
            breadcrumb = " > ".join(title for _, title in stack) if stack else "INTRODUCTION"
            sections.append(
                {
                    "title": current_title,
                    "body": body_text,
                    "breadcrumb": breadcrumb,
                    "level": stack[-1][0] if stack else 0,
                }
            )

    for line in lines:
        heading_flag, heading_text = is_heading(line)
        if heading_flag:
            flush_section()
            level = level_from_heading(heading_text)
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, heading_text))
            current_title = heading_text
            current_body = []
        else:
            current_body.append(line)

    flush_section()
    return sections


def word_chunks(text: str, chunk_words: int = CHUNK_WORDS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping word chunks."""
    words = text.split()
    if len(words) <= chunk_words:
        return [text]
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_words, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap
    return chunks


def build_chunks_for_act(
    act_name: str, md_text: str
) -> tuple[list[str], list[dict[str, Any]]]:
    """Return (chunks, metadatas) for a single act."""
    sections = build_section_tree(md_text)
    chunks: list[str] = []
    metadatas: list[dict[str, Any]] = []

    for section in sections:
        body = section["body"]
        if not body or len(body.split()) < MIN_SECTION_WORDS:
            if section["title"] and not body:
                enriched = f"[{section['breadcrumb']}]\n{section['title']}"
                chunks.append(enriched)
                metadatas.append(
                    {
                        "act": act_name,
                        "title": section["title"],
                        "breadcrumb": section["breadcrumb"],
                        "level": section["level"],
                        "is_header": True,
                    }
                )
            continue

        section_chunks = word_chunks(body, CHUNK_WORDS, CHUNK_OVERLAP)
        for idx, chunk in enumerate(section_chunks):
            enriched = f"[{section['breadcrumb']}]\n{chunk}"
            chunks.append(enriched)
            metadatas.append(
                {
                    "act": act_name,
                    "title": section["title"],
                    "breadcrumb": section["breadcrumb"],
                    "level": section["level"],
                    "chunk_index": idx,
                    "is_header": False,
                }
            )

    return chunks, metadatas


def build_faiss_index(chunks: list[str], model: Any) -> faiss.IndexFlatIP:
    """Embed chunks and build a FAISS inner-product index."""
    log(f"Embedding {len(chunks)} chunks with {EMBEDDING_MODEL} ...")
    embeddings = model.encode(chunks, batch_size=64, show_progress_bar=True, normalize_embeddings=True)
    embeddings = embeddings.astype("float32")

    index = faiss.IndexFlatIP(VECTOR_DIM)
    index.add(embeddings)
    return index


def validate_retrieval(model: Any, index: faiss.IndexFlatIP, chunks: list[str]) -> None:
    """Run a few test queries and print top-1 results."""
    test_queries = [
        "unexplained income or assets",
        "benami transaction",
        "money laundering",
        "sales tax registration",
        "customs duty",
    ]
    log("Validation queries:")
    for query in test_queries:
        q_emb = model.encode([query], normalize_embeddings=True).astype("float32")
        scores, indices = index.search(q_emb, 1)
        top_idx = int(indices[0][0])
        top_score = float(scores[0][0])
        snippet = chunks[top_idx].replace("\n", " ")[:200]
        print(f"  Q: {query!r}  ->  score={top_score:.3f}  ->  {snippet}...")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a vectorless RAG index for Pakistan tax laws.")
    parser.add_argument("--force-download", action="store_true", help="Re-download all PDFs.")
    parser.add_argument("--force-index", action="store_true", help="Rebuild the index even if it exists.")
    parser.add_argument("--skip-download", action="store_true", help="Use existing PDFs in server_artifacts/law_rag/pdfs/.")
    parser.add_argument("--skip-index", action="store_true", help="Only download PDFs; do not build the index.")
    args = parser.parse_args()

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    PDFS_DIR.mkdir(parents=True, exist_ok=True)
    MD_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Stage 1: download PDFs
    # ------------------------------------------------------------------
    if not args.skip_download:
        if is_checkpoint_complete("file1_downloads") and not args.force_download:
            log("Downloads checkpoint found; skipping. Use --force-download to override.")
        else:
            log(f"Downloading {len(LAW_URLS)} law PDFs to {PDFS_DIR} ...")
            success_count = 0
            for law in tqdm(LAW_URLS, desc="Laws"):
                pdf_path = PDFS_DIR / law["filename"]
                try:
                    download_if_missing(
                        law["url"], pdf_path, force=args.force_download, stage=STAGE
                    )
                    success_count += 1
                except Exception as exc:
                    log(f"  ERROR downloading {law['name']}: {exc}")
            save_checkpoint("file1_downloads", {"success_count": success_count, "total": len(LAW_URLS)})
            log(f"Downloaded or verified {success_count}/{len(LAW_URLS)} PDFs.")
    else:
        log("Skipping downloads (--skip-download).")

    if args.skip_index:
        log("Skipping index build (--skip-index). Done.")
        return 0

    # ------------------------------------------------------------------
    # Stage 2: convert PDFs to Markdown
    # ------------------------------------------------------------------
    if is_checkpoint_complete("file1_markdown") and not args.force_index and not args.force_download:
        log("Markdown conversion checkpoint found; skipping.")
    else:
        log("Converting PDFs to Markdown ...")
        available_pdfs = sorted(PDFS_DIR.glob("*.pdf"))
        if not available_pdfs:
            log(f"ERROR: no PDFs found in {PDFS_DIR}. Run without --skip-download first.")
            return 1

        md_files: list[Path] = []
        for pdf_path in tqdm(available_pdfs, desc="PDF→Markdown"):
            md_path = MD_DIR / (pdf_path.stem + ".md")
            if md_path.exists() and not args.force_index and not args.force_download:
                md_files.append(md_path)
                continue
            try:
                pdf_to_markdown(pdf_path, md_path)
                md_files.append(md_path)
            except Exception as exc:
                log(f"  ERROR converting {pdf_path.name}: {exc}")
        save_checkpoint("file1_markdown", {"converted": len(md_files)})

    # ------------------------------------------------------------------
    # Stage 3: parse sections and build chunks
    # ------------------------------------------------------------------
    if is_checkpoint_complete("file1_chunks") and not args.force_index:
        log("Chunks checkpoint found; loading from disk.")
        cp = load_checkpoint("file1_chunks")
        all_chunks = [r["text"] for r in read_jsonl(CHUNKS_PATH)]
        all_metadata = read_jsonl(META_PATH)
        log(f"Loaded {len(all_chunks)} chunks and {len(all_metadata)} metadata records.")
    else:
        log("Parsing legal sections and building chunks ...")
        md_files = sorted(MD_DIR.glob("*.md"))
        if not md_files:
            log(f"ERROR: no Markdown files found in {MD_DIR}.")
            return 1

        all_chunks: list[str] = []
        all_metadata: list[dict[str, Any]] = []

        for md_path in tqdm(md_files, desc="Parsing"):
            act_name = md_path.stem.replace("_", " ").title()
            md_text = md_path.read_text(encoding="utf-8")
            try:
                chunks, metas = build_chunks_for_act(act_name, md_text)
                all_chunks.extend(chunks)
                all_metadata.extend(metas)
            except Exception as exc:
                log(f"  ERROR parsing {md_path.name}: {exc}")

        if not all_chunks:
            log("ERROR: no chunks produced. Check PDF parsing output.")
            return 1

        log(f"Produced {len(all_chunks)} chunks from {len(md_files)} acts.")
        write_jsonl(CHUNKS_PATH, [{"text": c} for c in all_chunks])
        write_jsonl(META_PATH, all_metadata)
        save_checkpoint("file1_chunks", {"chunk_count": len(all_chunks), "act_count": len(md_files)})

    # ------------------------------------------------------------------
    # Stage 4: embed and build FAISS index
    # ------------------------------------------------------------------
    if INDEX_PATH.exists() and not args.force_index:
        log("Index already exists. Use --force-index to rebuild.")
        return 0

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(EMBEDDING_MODEL)
    index = build_faiss_index(all_chunks, model)

    # ------------------------------------------------------------------
    # Stage 5: save artifacts and validate
    # ------------------------------------------------------------------
    log(f"Saving index to {INDEX_PATH} ...")
    faiss.write_index(index, str(INDEX_PATH))

    validate_retrieval(model, index, all_chunks)
    save_checkpoint("file1_index", {"vector_count": len(all_chunks)})

    log("Done.")
    log(f"Artifacts: {INDEX_PATH}, {CHUNKS_PATH}, {META_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
