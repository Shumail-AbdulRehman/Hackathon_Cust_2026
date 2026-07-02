"""FastAPI backend for TaxNet XAI React frontend."""

import json
import os
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from slm.vectorless_law_rag import LawRetriever
from taxnet.ingestion import profile_datasets
from taxnet.pipeline import compact_result, run_benchmark, run_pipeline

DEFAULT_PROVIDER = "ollama"
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]

ROOT = Path(__file__).parent.resolve()
PROFILES_PATH = ROOT / "server_artifacts" / "ml" / "entity_profiles.jsonl"
LAW_CHUNKS_PATH = ROOT / "server_artifacts" / "law_rag" / "law_chunks.jsonl"
LAW_META_PATH = ROOT / "server_artifacts" / "law_rag" / "law_metadata.jsonl"
LAW_FAISS_PATH = ROOT / "server_artifacts" / "law_rag" / "law_index.faiss"
LIBRARIAN_PATH = ROOT / "slm" / "librarian.py"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _profiles
    _profiles = _load_profiles()
    yield


app = FastAPI(title="TaxNet XAI API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_profiles: Dict[str, Dict] = {}
_retriever: Optional[LawRetriever] = None


class BenchmarkParams(BaseModel):
    citizens: int = 500
    seed: int = 42


class PipelinePayload(BaseModel):
    datasets: Dict[str, List[Dict]]
    mappings: Optional[Dict] = None


class AskRequest(BaseModel):
    question: str
    top_k: int = 5


class AskTaxRequest(BaseModel):
    entity_id: str
    query: str
    top_k: int = 5


def _load_profiles() -> Dict[str, Dict]:
    profiles = {}
    if not PROFILES_PATH.exists():
        return profiles
    with open(PROFILES_PATH, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            profiles[rec.get("entity_id", "")] = rec
    return profiles


def _get_retriever() -> LawRetriever:
    global _retriever
    if _retriever is None:
        _retriever = LawRetriever(LAW_CHUNKS_PATH, LAW_META_PATH, LAW_FAISS_PATH)
    return _retriever


LAW_SYSTEM_PROMPT = (
    "You are a Pakistani tax-law research assistant. Your answers must be based ONLY on the law excerpts provided below. "
    "Cite the exact act, section, and subsection. Quote the relevant sentence from the excerpt when possible. "
    "Explain the answer in plain language that a non-lawyer can understand. "
    "If the provided excerpts do not contain the answer, say so explicitly — do not invent laws. "
    "After your answer, list exactly three brief questions a forensic auditor would ask about this topic, with concise answers."
)

NODE_SYSTEM_PROMPT = (
    "You are a senior Pakistani tax audit analyst assisting the Federal Board of Revenue. "
    "You are given an entity profile, an XGBoost risk score, top risk signals, and relevant Pakistan tax-law excerpts. "
    "Write a concise audit narrative that explains why this entity triggered the risk model, citing specific XGBoost signals and the exact law sections that apply. "
    "Use only the provided context — do not invent facts. "
    "After the narrative, list exactly three brief questions a forensic auditor would ask about this entity, with concise answers."
)


def _run_librarian(entity_id: Optional[str], user_prompt: str, system_prompt: str) -> str:
    cmd = [sys.executable, str(LIBRARIAN_PATH)]
    if entity_id:
        cmd += ["ask-tax", "--entity-id", entity_id, "--prompt", user_prompt, "--system", system_prompt]
    else:
        cmd += ["ask", "--prompt", user_prompt, "--system", system_prompt]

    env = os.environ.copy()
    env["HF_HUB_OFFLINE"] = "1"

    try:
        result = subprocess.run(
            cmd,
            cwd=str(ROOT / "slm"),
            capture_output=True,
            text=True,
            timeout=180,
            env=env,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="SLM request timed out.")
    except (FileNotFoundError, OSError) as exc:
        raise HTTPException(status_code=500, detail=f"Failed to run librarian: {exc}")

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr or "Librarian subprocess failed.")

    return result.stdout.strip()


@app.get("/api/health")
def health():
    return {"status": "ok", "provider": DEFAULT_PROVIDER}


@app.get("/api/slm-provider")
def slm_provider():
    return {"provider": DEFAULT_PROVIDER}


@app.get("/api/demo")
def demo():
    return compact_result(run_pipeline())


@app.get("/api/benchmark")
def benchmark(citizens: int = Query(500, ge=1, le=5000), seed: int = Query(42, ge=0, le=999999)):
    return run_benchmark(citizens=citizens, synthetic_seed=seed)


@app.post("/api/profile")
def profile(payload: PipelinePayload):
    return {"profiles": profile_datasets(payload.datasets, mappings=payload.mappings)}


@app.post("/api/run")
def run(payload: PipelinePayload):
    return compact_result(run_pipeline(datasets=payload.datasets, mappings=payload.mappings))


@app.get("/api/profiles")
def list_profiles(q: Optional[str] = Query(None)) -> List[Dict]:
    items = list(_profiles.values())
    if q:
        qlower = q.lower()
        items = [
            p
            for p in items
            if qlower in p.get("canonical_name", "").lower() or qlower in p.get("entity_id", "").lower()
        ]
    return [
        {
            "entity_id": p.get("entity_id"),
            "name": p.get("canonical_name"),
            "risk_score": p.get("risk_score"),
            "risk_tier": p.get("risk_tier"),
        }
        for p in items[:100]
    ]


@app.get("/api/profiles/{entity_id}")
def get_profile(entity_id: str) -> Dict:
    profile = _profiles.get(entity_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Entity not found")
    return profile


@app.post("/api/ask")
def ask(req: AskRequest):
    retriever = _get_retriever()
    context = retriever.get_context(req.question, top_k=req.top_k)

    user_prompt = (
        f"Use the following Pakistan tax-law excerpts to answer the question.\n\n"
        f"CONTEXT:\n{context}\n\n"
        f"QUESTION: {req.question}\n\n"
        f"ANSWER:"
    )

    answer = _run_librarian(None, user_prompt, LAW_SYSTEM_PROMPT)
    return {"answer": answer, "provider": DEFAULT_PROVIDER}


@app.post("/api/ask-tax")
def ask_tax(req: AskTaxRequest):
    profile = _profiles.get(req.entity_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Entity not found")

    retriever = _get_retriever()
    context = retriever.get_context(req.query, top_k=req.top_k)

    features = profile.get("features", {})
    top_signals = sorted(features.items(), key=lambda kv: abs(kv[1]), reverse=True)[:5]
    signal_lines = "\n".join(f"  - {k}: {v:.3f}" for k, v in top_signals)
    sources = ", ".join(profile.get("record_sources", [])) or "unknown"
    notes = profile.get("source_notes", [])
    notes_text = "\n".join(f"  - {n}" for n in notes[:3]) if notes else "  - none"

    user_prompt = (
        f"Entity: {profile.get('canonical_name', 'Unknown')} ({profile['entity_id']})\n"
        f"ML risk score: {profile.get('risk_score', 0.0):.1f}/100\n"
        f"Proxy label: {profile.get('proxy_label', 0.0):.1f}/100\n"
        f"Record sources: {sources}\n"
        f"Record count: {profile.get('record_count', 0)}\n"
        f"Top risk signals:\n{signal_lines}\n"
        f"Scenario hints:\n{notes_text}\n\n"
        f"Relevant Pakistan tax law context:\n{context}\n\n"
        f"Task: Write a concise audit narrative explaining why this entity triggered the risk model, citing specific XGBoost signals and the exact law sections that apply."
    )

    answer = _run_librarian(req.entity_id, user_prompt, NODE_SYSTEM_PROMPT)
    return {"answer": answer, "provider": DEFAULT_PROVIDER, "entity_id": req.entity_id}
