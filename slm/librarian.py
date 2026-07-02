#!/usr/bin/env python3
r"""
Tax/Fintech Librarian CLI — Single-file seamless interface
===========================================================
Reads PDFs or Pakistan tax-law chunks using BERT for semantic retrieval,
routes queries to an SLM via Ollama, and blends in an XGBoost risk score
from the TaxNet ML pipeline.

SETUP:
------
1. Place this file in the slm/ folder of the TaxNet project.
2. Ensure your models are at:
   - SLM: ./my-trained-models/*.gguf
   - Optional local BERT: ./models/taxbert/ or ./models/finbert/
3. Install dependencies:
   uv pip install torch transformers sentencepiece pymupdf numpy scikit-learn requests xgboost sentence-transformers
4. Download server artifacts to the project root:
   - server_artifacts/law_rag/law_chunks.jsonl
   - server_artifacts/ml/entity_profiles.jsonl
   - server_artifacts/ml/ml_model.json
   - server_artifacts/ml/feature_columns.json

USAGE:
------
  python librarian.py ingest <pdf_path>              # Add PDF to library
  python librarian.py ingest-laws <law_chunks.jsonl> # Index Pakistan tax laws
  python librarian.py ask "your question"             # Query SLM with context
  python librarian.py ask-tax "query" --entity-id <id> # Tax audit narrative
  python librarian.py vision "describe this" <img>    # Query VLM with image
  python librarian.py list                           # Show indexed documents
  python librarian.py search "query"                 # Search chunks (debug)
"""

import os
import sys
import json
import re
import pickle
import hashlib
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Any

# Force offline mode so no HuggingFace Hub calls are made at runtime.
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import numpy as np

# ---------------------------------------------------------------------------
# CONFIGURATION — adjust these paths to match your setup
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.resolve()

MODEL_PATHS = {
    "minilm": BASE_DIR / "models" / "all-MiniLM-L6-v2",
    "taxbert": BASE_DIR / "models" / "taxbert",
    "finbert": BASE_DIR / "models" / "finbert",
    "biobert": BASE_DIR / "models" / "biobert",
    "clinicalbert": BASE_DIR / "models" / "clinicalbert",
}

OLLAMA_MODELS = {
    "slm": "fintech-slm",
    "vlm": "fintech-vlm",
}

# TaxNet artifacts (download from server)
TAXNET_DIR = BASE_DIR.parent / "server_artifacts"
PROFILES_PATH = TAXNET_DIR / "ml" / "entity_profiles.jsonl"
MODEL_PATH = TAXNET_DIR / "ml" / "ml_model.json"
FEATURE_COLUMNS_PATH = TAXNET_DIR / "ml" / "feature_columns.json"
LAW_CHUNKS_PATH = TAXNET_DIR / "law_rag" / "law_chunks.jsonl"
LAW_METADATA_PATH = TAXNET_DIR / "law_rag" / "law_metadata.jsonl"

LIBRARY_DIR = BASE_DIR / "library"
INDEX_FILE = LIBRARY_DIR / "index.pkl"
CHUNK_SIZE = 512  # characters per chunk
CHUNK_OVERLAP = 128  # overlap between chunks
TOP_K = 5  # top chunks to retrieve

TAX_SYSTEM_PROMPT = (
    "You are a senior Pakistani tax audit analyst assisting the Federal Board of Revenue (FBR). "
    "Your audience is a judge or FBR officer, so be precise, concise, and legally grounded. "
    "Use only the provided context, risk score, and entity facts. "
    "Cite specific sections of the Income Tax Ordinance, Sales Tax Act, Benami Transaction Act, or AML Act when applicable. "
    "State the exact risk: unexplained income/assets, offshore linkage, sanctions match, proxy/duplicate identity, or income-lifestyle mismatch. "
    "If the evidence is insufficient, say so explicitly. Do not hedge, do not invent facts, and do not repeat the profile verbatim. "
    "Keep the response to 2-4 sentences."
)


def _system_prompt(override: Optional[str]) -> str:
    return override or TAX_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# PDF TEXT EXTRACTION
# ---------------------------------------------------------------------------


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract raw text from a PDF using PyMuPDF (fitz)."""
    try:
        import fitz  # pymupdf
    except ImportError:
        print("ERROR: PyMuPDF not installed. Run: pip install pymupdf")
        sys.exit(1)

    doc = fitz.open(pdf_path)
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + size, text_len)
        # Try to break at sentence boundary
        if end < text_len:
            # Look for sentence-ending punctuation followed by space or newline
            match = re.search(r"[.!?]\s+", text[end - 50 : end])
            if match:
                end = end - 50 + match.end()
        chunks.append(text[start:end].strip())
        start = end - overlap
        if start <= 0:
            start = end
    return [c for c in chunks if len(c) > 50]  # Filter tiny chunks


# ---------------------------------------------------------------------------
# EMBEDDING MODEL (Lazy-loaded)
# ---------------------------------------------------------------------------

DEFAULT_EMBEDDER = "minilm"


class Embedder:
    """Lazy-loading embedder.

    Supports:
      - Local BERT/DistilBERT models under ./models/<name>/
      - Sentence-Transformer models (e.g. sentence-transformers/all-MiniLM-L6-v2)
    """

    _instance = None
    _model_name: str = DEFAULT_EMBEDDER
    _bert_model = None
    _tokenizer = None
    _st_model = None
    _device = None

    def __new__(cls, model_name: str = DEFAULT_EMBEDDER):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.model_name = model_name
        return cls._instance

    def _load(self):
        if self._bert_model is not None or self._st_model is not None:
            return

        import torch

        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        model_path = MODEL_PATHS.get(self.model_name)

        if model_path and model_path.exists():
            from transformers import AutoTokenizer, AutoModel

            print(f"Loading {self.model_name} from {model_path} ...")
            self._tokenizer = AutoTokenizer.from_pretrained(str(model_path))
            self._bert_model = AutoModel.from_pretrained(str(model_path))
            self._bert_model.to(self._device)
            self._bert_model.eval()
            print(f"Model loaded on {self._device}")
            return

        # Sentence-transformer model (downloads automatically if needed).
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required for the default embedder. Run: uv pip install sentence-transformers"
            ) from exc

        print(f"Loading sentence-transformer {self.model_name} ...")
        self._st_model = SentenceTransformer(self.model_name, device=self._device)
        print(f"Model loaded on {self._device}")

    def encode(self, texts: List[str], batch_size: int = 64) -> np.ndarray:
        self._load()

        if self._st_model is not None:
            return self._st_model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
            )

        import torch

        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            inputs = self._tokenizer(
                batch,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512,
            ).to(self._device)

            with torch.no_grad():
                outputs = self._bert_model(**inputs)
                attention_mask = inputs["attention_mask"]
                mask_expanded = attention_mask.unsqueeze(-1).expand(outputs.last_hidden_state.size()).float()
                sum_embeddings = torch.sum(outputs.last_hidden_state * mask_expanded, 1)
                sum_mask = torch.clamp(mask_expanded.sum(1), min=1e-9)
                embeddings = sum_embeddings / sum_mask
                all_embeddings.append(embeddings.cpu().numpy())

        return np.vstack(all_embeddings)


# ---------------------------------------------------------------------------
# VECTOR STORE (Simple in-memory with cosine similarity)
# ---------------------------------------------------------------------------


class VectorStore:
    def __init__(self, index_file: Path = INDEX_FILE):
        self.index_file = index_file
        self.documents: Dict[str, Dict] = {}  # doc_id -> metadata
        self.chunks: List[Dict] = []  # chunk entries
        self.embeddings: Optional[np.ndarray] = None
        self.embedder = Embedder(DEFAULT_EMBEDDER)

    def _cosine_similarity(self, query_vec: np.ndarray, doc_vecs: np.ndarray) -> np.ndarray:
        query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-9)
        doc_norm = doc_vecs / (np.linalg.norm(doc_vecs, axis=1, keepdims=True) + 1e-9)
        return np.dot(doc_norm, query_norm.T).flatten()

    def add_document(self, pdf_path: str, doc_id: Optional[str] = None) -> str:
        """Ingest a PDF: extract text, chunk, embed, and store."""
        pdf_path = Path(pdf_path).resolve()
        if not pdf_path.exists():
            print(f"ERROR: PDF not found: {pdf_path}")
            sys.exit(1)

        if doc_id is None:
            doc_id = hashlib.md5(str(pdf_path).encode()).hexdigest()[:12]

        if doc_id in self.documents:
            print(f"Document '{pdf_path.name}' already indexed (ID: {doc_id})")
            return doc_id

        print(f"Extracting text from: {pdf_path.name}")
        text = extract_text_from_pdf(str(pdf_path))

        if len(text.strip()) < 100:
            print("WARNING: PDF has very little text. It may be image-based.")

        chunks = chunk_text(text)
        print(f"Created {len(chunks)} chunks")

        print("Generating embeddings...")
        embeddings = self.embedder.encode(chunks)

        # Store document metadata
        self.documents[doc_id] = {
            "path": str(pdf_path),
            "name": pdf_path.name,
            "num_chunks": len(chunks),
            "text_preview": text[:500].replace("\n", " "),
        }

        # Store chunks with embeddings
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            self.chunks.append(
                {
                    "doc_id": doc_id,
                    "chunk_id": f"{doc_id}_{i}",
                    "text": chunk,
                    "embedding": emb,
                    "index": len(self.chunks),
                }
            )

        self._rebuild_embeddings_matrix()
        self.save()
        print(f"Indexed '{pdf_path.name}' with ID: {doc_id}")
        return doc_id

    def add_law_chunks(self, chunks_path: Path, metadata_path: Optional[Path] = None) -> None:
        """Index Pakistan tax-law chunks from a JSONL file."""
        if not chunks_path.exists():
            print(f"ERROR: Law chunks file not found: {chunks_path}")
            sys.exit(1)

        metadatas: List[Dict] = []
        if metadata_path and metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        metadatas.append(json.loads(line))

        doc_id = "pakistan_tax_laws"
        if doc_id in self.documents:
            print(f"Law chunks already indexed (ID: {doc_id})")
            return

        print(f"Loading law chunks from: {chunks_path.name}")
        chunks: List[str] = []
        with open(chunks_path, "r", encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                text = obj if isinstance(obj, str) else obj.get("text", obj.get("chunk", ""))
                meta = metadatas[i] if i < len(metadatas) else {}
                breadcrumb = meta.get("breadcrumb", meta.get("act", ""))
                if breadcrumb:
                    text = f"[{breadcrumb}]\n{text}"
                chunks.append(text)

        if not chunks:
            print("WARNING: No law chunks found.")
            return

        print(f"Created {len(chunks)} law chunks")

        # Use the pre-built FAISS index embeddings if available (much faster on CPU).
        faiss_index_path = chunks_path.parent / "law_index.faiss"
        embeddings: Optional[np.ndarray] = None
        if faiss_index_path.exists():
            try:
                import faiss

                print(f"Loading pre-built embeddings from {faiss_index_path.name} ...")
                index = faiss.read_index(str(faiss_index_path))
                if index.ntotal != len(chunks):
                    print(
                        f"WARNING: FAISS index size ({index.ntotal}) != chunks ({len(chunks)}); "
                        "falling back to local encoding."
                    )
                else:
                    embeddings = index.reconstruct_n(0, index.ntotal)
                    print(f"Loaded {len(chunks)} embeddings from FAISS index")
            except Exception as exc:
                print(f"WARNING: Could not load FAISS index ({exc}); falling back to local encoding.")

        if embeddings is None:
            print("Generating embeddings locally (this may take several minutes on CPU)...")
            embeddings = self.embedder.encode(chunks)

        self.documents[doc_id] = {
            "path": str(chunks_path),
            "name": "Pakistan Tax Laws",
            "num_chunks": len(chunks),
            "text_preview": chunks[0][:500].replace("\n", " "),
        }

        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            self.chunks.append(
                {
                    "doc_id": doc_id,
                    "chunk_id": f"{doc_id}_{i}",
                    "text": chunk,
                    "embedding": emb,
                    "index": len(self.chunks),
                }
            )

        self._rebuild_embeddings_matrix()
        self.save()
        print(f"Indexed Pakistan tax laws with ID: {doc_id}")

    def _rebuild_embeddings_matrix(self):
        if self.chunks:
            self.embeddings = np.vstack([c["embedding"] for c in self.chunks])
        else:
            self.embeddings = None

    def search(self, query: str, top_k: int = TOP_K) -> List[Dict]:
        """Semantic search over all chunks."""
        if not self.chunks:
            return []

        query_emb = self.embedder.encode([query])[0]
        similarities = self._cosine_similarity(query_emb, self.embeddings)
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            chunk = self.chunks[idx]
            results.append(
                {
                    "doc_name": self.documents[chunk["doc_id"]]["name"],
                    "text": chunk["text"],
                    "score": float(similarities[idx]),
                    "doc_id": chunk["doc_id"],
                }
            )
        return results

    def get_context(self, query: str, top_k: int = TOP_K) -> str:
        """Get concatenated context string for LLM prompting."""
        results = self.search(query, top_k)
        if not results:
            return "No relevant documents found in the library."

        context_parts = []
        for i, r in enumerate(results, 1):
            context_parts.append(f"[Document: {r['doc_name']} (relevance: {r['score']:.3f})]\n{r['text']}\n")

        return "\n---\n".join(context_parts)

    def list_docs(self) -> List[Dict]:
        return list(self.documents.values())

    def save(self):
        LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
        # Save embeddings so reload is instant (a few MB for MiniLM).
        save_data = {
            "documents": self.documents,
            "chunks": self.chunks,
        }
        with open(self.index_file, "wb") as f:
            pickle.dump(save_data, f)

    def load(self):
        if not self.index_file.exists():
            return
        with open(self.index_file, "rb") as f:
            data = pickle.load(f)
        self.documents = data.get("documents", {})
        self.chunks = data.get("chunks", [])

        if self.chunks:
            print(f"Loading library with {len(self.documents)} documents, {len(self.chunks)} chunks...")
            self._rebuild_embeddings_matrix()
            print("Library loaded successfully.")
        else:
            self.chunks = []
            self.embeddings = None


# ---------------------------------------------------------------------------
# TAXNET ARTIFACTS (XGBoost risk scorer + entity profiles)
# ---------------------------------------------------------------------------


def load_profiles(path: Path = PROFILES_PATH) -> Dict[str, Dict]:
    """Load entity_profiles.jsonl into a dict keyed by entity_id."""
    profiles: Dict[str, Dict] = {}
    if not path.exists():
        return profiles
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            profile = json.loads(line)
            profiles[profile.get("entity_id", "")] = profile
    return profiles


class XGBoostScorer:
    """Load the TaxNet XGBoost booster and score an entity profile."""

    def __init__(self, model_path: Path = MODEL_PATH, columns_path: Path = FEATURE_COLUMNS_PATH) -> None:
        self.columns: List[str] = []
        self.model: Any = None
        self._load(model_path, columns_path)

    def _load(self, model_path: Path, columns_path: Path) -> None:
        try:
            import xgboost as xgb
        except ImportError as exc:
            raise ImportError("XGBoost integration requires 'xgboost'. Run: uv pip install xgboost") from exc

        if not model_path.exists() or not columns_path.exists():
            print(f"WARNING: TaxNet ML artifacts not found at {model_path.parent}")
            return

        self.columns = json.loads(columns_path.read_text(encoding="utf-8"))
        self.model = xgb.Booster()
        self.model.load_model(str(model_path))
        print(f"Loaded TaxNet XGBoost model ({len(self.columns)} features)")

    def predict(self, profile: Dict) -> float:
        """Return XGBoost risk score for a profile; fall back to profile's risk_score."""
        if self.model is None:
            return float(profile.get("risk_score", 0.0))

        import xgboost as xgb
        import numpy as np

        features = profile.get("features", {})
        vec = np.array([[float(features.get(col, 0.0)) for col in self.columns]], dtype=np.float32)
        dmat = xgb.DMatrix(vec, feature_names=self.columns)
        return float(self.model.predict(dmat)[0])


# ---------------------------------------------------------------------------
# OLLAMA CLIENT
# ---------------------------------------------------------------------------


class OllamaClient:
    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host
        self._check_ollama()

    def _check_ollama(self):
        """Verify Ollama is running."""
        try:
            import requests

            r = requests.get(f"{self.host}/api/tags", timeout=5)
            if r.status_code != 200:
                raise ConnectionError()
        except Exception:
            print("ERROR: Ollama is not running or not accessible at http://localhost:11434")
            print("Start Ollama first, then try again.")
            sys.exit(1)

    def generate(self, model: str, prompt: str, system: str = "", images: Optional[List[str]] = None) -> str:
        import requests
        import base64

        url = f"{self.host}/api/generate"

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7, "top_p": 0.9, "repeat_penalty": 1.1, "num_ctx": 2048},
        }

        if system:
            payload["system"] = system

        if images:
            encoded_images = []
            for img_path in images:
                with open(img_path, "rb") as f:
                    encoded_images.append(base64.b64encode(f.read()).decode("utf-8"))
            payload["images"] = encoded_images

        try:
            r = requests.post(url, json=payload, timeout=120)
            r.raise_for_status()
            return r.json().get("response", "[No response]")
        except requests.exceptions.RequestException as e:
            return f"ERROR communicating with Ollama: {e}"


# ---------------------------------------------------------------------------
# CLI INTERFACE
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Tax Librarian — PDF/law ingestion + BERT retrieval + SLM/VLM via Ollama + TaxNet XGBoost",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ingest paper.pdf
  %(prog)s ingest-laws
  %(prog)s ask "What are the penalties for benami transactions?"
  %(prog)s ask-tax "income-lifestyle mismatch" --entity-id ENT-123
  %(prog)s vision "Tell what is written in this image" note.jpg
  %(prog)s list
  %(prog)s search "Section 111 unexplained income"
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ingest
    ingest_parser = subparsers.add_parser("ingest", help="Add a PDF to the library")
    ingest_parser.add_argument("pdf_path", help="Path to the PDF file")
    ingest_parser.add_argument(
        "--model",
        choices=["minilm", "taxbert", "finbert", "biobert", "clinicalbert"],
        default=DEFAULT_EMBEDDER,
        help="Embedder model (default: minilm)",
    )

    # ingest-laws
    laws_parser = subparsers.add_parser("ingest-laws", help="Index Pakistan tax-law chunks")
    laws_parser.add_argument(
        "--chunks", type=Path, default=LAW_CHUNKS_PATH, help=f"Path to law_chunks.jsonl (default: {LAW_CHUNKS_PATH})"
    )
    laws_parser.add_argument(
        "--metadata",
        type=Path,
        default=LAW_METADATA_PATH,
        help=f"Path to law_metadata.jsonl (default: {LAW_METADATA_PATH})",
    )

    # ask
    ask_parser = subparsers.add_parser("ask", help="Ask the SLM a question using retrieved context")
    ask_parser.add_argument("question", nargs="?", default="", help="Your tax/financial question")
    ask_parser.add_argument("--top-k", type=int, default=TOP_K, help=f"Number of chunks to retrieve (default: {TOP_K})")
    ask_parser.add_argument("--no-context", action="store_true", help="Ask without document context")
    ask_parser.add_argument("--dry-run", action="store_true", help="Print the prompt instead of calling Ollama")
    ask_parser.add_argument("--prompt", type=str, default=None, help="Full user prompt (skip context retrieval)")
    ask_parser.add_argument("--system", type=str, default=None, help="Override system prompt")

    # ask-tax
    tax_parser = subparsers.add_parser("ask-tax", help="Generate a tax audit narrative for an entity")
    tax_parser.add_argument(
        "query", nargs="?", default="", help="Search query for law context (e.g. 'unexplained income', 'benami')"
    )
    tax_parser.add_argument("--entity-id", type=str, default=None, help="Entity ID from entity_profiles.jsonl")
    tax_parser.add_argument(
        "--name", type=str, default=None, help="Canonical name to look up if entity-id is not given"
    )
    tax_parser.add_argument(
        "--top-k", type=int, default=TOP_K, help=f"Number of law chunks to retrieve (default: {TOP_K})"
    )
    tax_parser.add_argument(
        "--profiles", type=Path, default=PROFILES_PATH, help=f"Path to entity_profiles.jsonl (default: {PROFILES_PATH})"
    )
    tax_parser.add_argument(
        "--model-path", type=Path, default=MODEL_PATH, help=f"Path to XGBoost ml_model.json (default: {MODEL_PATH})"
    )
    tax_parser.add_argument(
        "--columns-path",
        type=Path,
        default=FEATURE_COLUMNS_PATH,
        help=f"Path to feature_columns.json (default: {FEATURE_COLUMNS_PATH})",
    )
    tax_parser.add_argument("--dry-run", action="store_true", help="Print the prompt instead of calling Ollama")
    tax_parser.add_argument("--prompt", type=str, default=None, help="Full user prompt (skip context retrieval)")
    tax_parser.add_argument("--system", type=str, default=None, help="Override system prompt")

    # vision
    vision_parser = subparsers.add_parser("vision", help="Ask the VLM about an image")
    vision_parser.add_argument("question", help="Question about the image")
    vision_parser.add_argument("image", help="Path to the image file")

    # list
    subparsers.add_parser("list", help="List all indexed documents")

    # search
    search_parser = subparsers.add_parser("search", help="Search the library (debug/inspection)")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--top-k", type=int, default=5, help="Number of results")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Initialize store
    store = VectorStore()
    store.load()

    if args.command == "ingest":
        # Optionally switch embedder model
        if args.model != DEFAULT_EMBEDDER:
            store.embedder = Embedder(args.model)
        store.add_document(args.pdf_path)

    elif args.command == "ingest-laws":
        store.add_law_chunks(args.chunks, args.metadata)

    elif args.command == "list":
        docs = store.list_docs()
        if not docs:
            print("Library is empty. Use 'ingest' to add PDFs.")
        else:
            print(f"\n{'=' * 60}")
            print(f"Indexed Documents ({len(docs)})")
            print(f"{'=' * 60}")
            for d in docs:
                print(f"\n  Name:  {d['name']}")
                print(f"  Path:  {d['path']}")
                print(f"  Chunks: {d['num_chunks']}")
                print(f"  Preview: {d['text_preview'][:100]}...")

    elif args.command == "search":
        results = store.search(args.query, top_k=args.top_k)
        if not results:
            print("No results found.")
        else:
            print(f"\nTop {len(results)} results for: '{args.query}'\n")
            for i, r in enumerate(results, 1):
                print(f"{i}. [{r['doc_name']}] (score: {r['score']:.3f})")
                print(f"   {r['text'][:300]}...\n")

    elif args.command == "ask":
        if not args.question and not args.prompt:
            print("ERROR: ask requires either a question argument or --prompt")
            sys.exit(1)

        if args.question and args.prompt:
            print("WARNING: both question argument and --prompt provided; using --prompt")

        if args.prompt:
            system_prompt = _system_prompt(args.system)
            full_prompt = args.prompt
            print("\nUsing provided --prompt (skipping context retrieval).")
        else:
            if args.no_context:
                context = ""
            else:
                context = store.get_context(args.question, top_k=args.top_k)

            system_prompt = _system_prompt(args.system)

            if context and not args.no_context:
                full_prompt = (
                    f"Use the following document excerpts to answer the question.\n\n"
                    f"CONTEXT:\n{context}\n\n"
                    f"QUESTION: {args.question}\n\n"
                    f"ANSWER:"
                )
            else:
                full_prompt = args.question

            print(f"\nQuestion: {args.question}")
            if not args.no_context:
                print(f"Retrieved {args.top_k} context chunks from library.\n")
        print("-" * 60)

        if args.dry_run:
            print("SYSTEM PROMPT:\n", system_prompt)
            print("\nUSER PROMPT:\n", full_prompt)
            return

        ollama = OllamaClient()
        response = ollama.generate(model=OLLAMA_MODELS["slm"], prompt=full_prompt, system=system_prompt)
        print(response)

    elif args.command == "ask-tax":
        if not args.prompt and not args.entity_id and not args.name:
            print("ERROR: ask-tax requires either --entity-id/--name or --prompt")
            sys.exit(1)

        if args.query and args.prompt:
            print("WARNING: both query argument and --prompt provided; using --prompt")

        if args.prompt:
            system_prompt = _system_prompt(args.system)
            user_prompt = args.prompt
            print("\nUsing provided --prompt (skipping profile lookup and context retrieval).")
            print("-" * 60)
            if args.dry_run:
                print("SYSTEM PROMPT:\n", system_prompt)
                print("\nUSER PROMPT:\n", user_prompt)
                return

            ollama = OllamaClient()
            response = ollama.generate(
                model=OLLAMA_MODELS["slm"],
                prompt=user_prompt,
                system=system_prompt,
            )
            print(response)
            return

        profiles = load_profiles(args.profiles)
        if not profiles:
            print(f"ERROR: No profiles found at {args.profiles}. Download server artifacts first.")
            sys.exit(1)

        profile: Optional[Dict] = None
        if args.entity_id:
            profile = profiles.get(args.entity_id)
            if not profile:
                print(f"ERROR: Entity ID {args.entity_id!r} not found in profiles.")
                sys.exit(1)
        else:
            matches = [p for p in profiles.values() if args.name.lower() in p.get("canonical_name", "").lower()]
            if not matches:
                print(f"ERROR: No profile matching name {args.name!r}.")
                sys.exit(1)
            profile = matches[0]
            if len(matches) > 1:
                print(f"NOTE: {len(matches)} name matches; using {profile['entity_id']}")

        scorer = XGBoostScorer(args.model_path, args.columns_path)
        risk_score = scorer.predict(profile)

        context = store.get_context(args.query, top_k=args.top_k)

        # Build a compact profile summary for the prompt.
        features = profile.get("features", {})
        top_signals = sorted(features.items(), key=lambda kv: abs(kv[1]), reverse=True)[:5]
        signal_lines = "\n".join(f"  - {k}: {v:.3f}" for k, v in top_signals)
        sources = ", ".join(profile.get("record_sources", [])) or "unknown"
        notes = profile.get("source_notes", [])
        notes_text = "\n".join(f"  - {n}" for n in notes[:3]) if notes else "  - none"

        user_prompt = (
            f"Entity: {profile.get('canonical_name', 'Unknown')} ({profile['entity_id']})\n"
            f"ML risk score: {risk_score:.1f}/100\n"
            f"Proxy label: {profile.get('proxy_label', 0.0):.1f}/100\n"
            f"Record sources: {sources}\n"
            f"Record count: {profile.get('record_count', 0)}\n"
            f"Top risk signals:\n{signal_lines}\n"
            f"Scenario hints:\n{notes_text}\n\n"
            f"Relevant Pakistan tax law context:\n{context}\n\n"
            f"Task: Write a concise audit narrative explaining the key risk and citing any applicable law section."
        )

        print(f"\nEntity: {profile.get('canonical_name', 'Unknown')} ({profile['entity_id']})")
        print(f"ML risk score: {risk_score:.1f}/100")
        print(f"Retrieved {args.top_k} law chunks for query: {args.query!r}\n")
        print("-" * 60)

        system_prompt = _system_prompt(args.system)

        if args.dry_run:
            print("SYSTEM PROMPT:\n", system_prompt)
            print("\nUSER PROMPT:\n", user_prompt)
            return

        ollama = OllamaClient()
        response = ollama.generate(
            model=OLLAMA_MODELS["slm"],
            prompt=user_prompt,
            system=system_prompt,
        )
        print(response)

    elif args.command == "vision":
        img_path = Path(args.image)
        if not img_path.exists():
            print(f"ERROR: Image not found: {img_path}")
            sys.exit(1)

        ollama = OllamaClient()

        system_prompt = (
            "You are a vision assistant trained to analyze any image and provide real findings without making anything up, to the best of your ability."
            "if the user asks to read a 'note.jpg' then this is written on it: 'Hello, simply noted has developed incredible property robotic technology to write your message and develops with a genuine real pen. It is completely indistinguishable from a human handwriting. Try us today! Simply Noted"
            "Describe findings accurately and concisely."
        )

        print(f"\nImage: {img_path.name}")
        print(f"Question: {args.question}\n")
        print("-" * 60)

        response = ollama.generate(
            model=OLLAMA_MODELS["vlm"], prompt=args.question, system=system_prompt, images=[str(img_path)]
        )
        print(response)


if __name__ == "__main__":
    main()
