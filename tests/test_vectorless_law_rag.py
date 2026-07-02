import json
from pathlib import Path

from slm.vectorless_law_rag import LawRetriever


def test_retriever_finds_benami_section(tmp_path: Path):
    chunks = tmp_path / "law_chunks.jsonl"
    meta = tmp_path / "law_metadata.jsonl"
    chunks.write_text(
        json.dumps(
            {
                "text": "Benami transaction means a transaction where property is transferred to one person for consideration paid by another."
            }
        )
        + "\n"
        + json.dumps({"text": "Income tax is payable on taxable income."})
        + "\n",
        encoding="utf-8",
    )
    meta.write_text(
        json.dumps({"act": "Benami Transaction Act", "title": "Section 2", "breadcrumb": "Definitions"})
        + "\n"
        + json.dumps({"act": "Income Tax Ordinance", "title": "Section 4", "breadcrumb": "Charge"})
        + "\n",
        encoding="utf-8",
    )

    retriever = LawRetriever(chunks, meta)
    results = retriever.retrieve("benami transaction definition", top_k=1)
    assert len(results) == 1
    assert "Benami Transaction Act" in results[0]["act"]
    assert "property is transferred" in results[0]["text"]


def test_retrieve_returns_empty_for_no_match(tmp_path: Path):
    chunks = tmp_path / "law_chunks.jsonl"
    meta = tmp_path / "law_metadata.jsonl"
    chunks.write_text(
        json.dumps({"text": "Income tax is payable on taxable income."}) + "\n",
        encoding="utf-8",
    )
    meta.write_text(
        json.dumps({"act": "Income Tax Ordinance", "title": "Section 4", "breadcrumb": "Charge"}) + "\n",
        encoding="utf-8",
    )

    retriever = LawRetriever(chunks, meta)
    results = retriever.retrieve("zzxy_nonexistent_query", top_k=5)
    assert results == []


def test_get_context_returns_expected_format(tmp_path: Path):
    chunks = tmp_path / "law_chunks.jsonl"
    meta = tmp_path / "law_metadata.jsonl"
    chunks.write_text(
        json.dumps(
            {
                "text": "Benami transaction means a transaction where property is transferred to one person for consideration paid by another."
            }
        )
        + "\n"
        + json.dumps({"text": "Income tax is payable on taxable income."})
        + "\n",
        encoding="utf-8",
    )
    meta.write_text(
        json.dumps({"act": "Benami Transaction Act", "title": "Section 2", "breadcrumb": "Definitions"})
        + "\n"
        + json.dumps({"act": "Income Tax Ordinance", "title": "Section 4", "breadcrumb": "Charge"})
        + "\n",
        encoding="utf-8",
    )

    retriever = LawRetriever(chunks, meta)
    context = retriever.get_context("benami transaction definition", top_k=1)
    assert "Benami Transaction Act" in context
    assert "[1]" in context

    context_multi = retriever.get_context("transaction income", top_k=2)
    assert "\n\n---\n\n" in context_multi
