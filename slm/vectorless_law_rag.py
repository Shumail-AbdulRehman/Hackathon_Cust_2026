"""Vectorless / Proxy-Pointer style law retrieval.

Builds a hierarchical index from law_metadata.jsonl and law_chunks.jsonl.
Retrieves by keyword + structural search with breadcrumb injection.
"""

import json
import re
import warnings
from pathlib import Path
from typing import Any, List, Dict, Optional, Tuple

import numpy as np


DEFAULT_EMBEDDER_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
KEYWORD_WEIGHT = 0.7
SEMANTIC_WEIGHT = 0.3


class LawRetriever:
    def __init__(
        self,
        chunks_path: Path,
        metadata_path: Path,
        faiss_index_path: Optional[Path] = None,
    ):
        self.chunks_path = Path(chunks_path)
        self.metadata_path = Path(metadata_path)
        self.faiss_index_path = faiss_index_path
        self.chunks: List[Dict] = []
        self.metadata: List[Dict] = []
        self.embeddings: Optional[np.ndarray] = None
        self._doc_norm: Optional[np.ndarray] = None
        self._sentence_transformer: Optional[Any] = None
        self._load()

    def _get_sentence_transformer(self) -> Any:
        if self._sentence_transformer is None:
            from sentence_transformers import SentenceTransformer

            self._sentence_transformer = SentenceTransformer(DEFAULT_EMBEDDER_MODEL)
        return self._sentence_transformer

    def _load(self):
        if not self.chunks_path.exists():
            raise FileNotFoundError(f"Chunks file not found: {self.chunks_path}")

        with open(self.chunks_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as exc:
                    print(f"WARNING: skipping malformed JSONL line in {self.chunks_path}: {exc}")
                    continue
                if isinstance(obj, str):
                    text = obj
                elif isinstance(obj, dict):
                    text = obj.get("text", obj.get("chunk", ""))
                else:
                    text = ""
                self.chunks.append({"text": text})

        if self.metadata_path.exists():
            with open(self.metadata_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        self.metadata.append(json.loads(line))
                    except json.JSONDecodeError as exc:
                        print(f"WARNING: skipping malformed JSONL line in {self.metadata_path}: {exc}")

        # Pad metadata if shorter than chunks
        while len(self.metadata) < len(self.chunks):
            self.metadata.append({})

        # Build hierarchical groupings
        self.groups: Dict[str, List[int]] = {}
        for i, meta in enumerate(self.metadata):
            key = self._group_key(meta)
            self.groups.setdefault(key, []).append(i)

        # Load embeddings if pre-built FAISS index exists
        if self.faiss_index_path and self.faiss_index_path.exists():
            try:
                import faiss

                index = faiss.read_index(str(self.faiss_index_path))
                if index.ntotal == len(self.chunks):
                    self.embeddings = index.reconstruct_n(0, index.ntotal)
                else:
                    print(
                        f"WARNING: FAISS index size ({index.ntotal}) does not match "
                        f"chunks ({len(self.chunks)}); falling back to keyword-only retrieval."
                    )
            except (ImportError, RuntimeError, ValueError) as exc:
                warnings.warn(f"Could not load FAISS index from {self.faiss_index_path}: {exc}")
                self.embeddings = None

        if self.embeddings is not None:
            self._doc_norm = self.embeddings / (np.linalg.norm(self.embeddings, axis=1, keepdims=True) + 1e-9)

    def _group_key(self, meta: Dict) -> str:
        act = meta.get("act", "Unknown Act")
        crumb = meta.get("breadcrumb", "")
        title = meta.get("title", "")
        section = crumb or title
        return f"{act}::{section}"

    def _tokenize(self, text: str) -> set:
        return set(re.findall(r"[a-zA-Z0-9_]+", text.lower()))

    def _keyword_score(self, query: str, text: str) -> float:
        q_tokens = self._tokenize(query)
        t_tokens = self._tokenize(text)
        if not q_tokens:
            return 0.0
        matches = len(q_tokens & t_tokens)
        return matches / len(q_tokens)

    def _semantic_score(self, query: str) -> Optional[np.ndarray]:
        if self.embeddings is None or self._doc_norm is None:
            return None
        try:
            model = self._get_sentence_transformer()
            query_emb = model.encode([query], show_progress_bar=False)
            query_norm = query_emb / (np.linalg.norm(query_emb) + 1e-9)
            return np.dot(self._doc_norm, query_norm.T).flatten()
        except ImportError:
            return None
        except RuntimeError:
            return None

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        # 1. Keyword scores on text + breadcrumb + title + act
        text_scores = []
        for i, chunk in enumerate(self.chunks):
            meta = self.metadata[i]
            combined = "\n".join(
                [
                    meta.get("act", ""),
                    meta.get("title", ""),
                    meta.get("breadcrumb", ""),
                    chunk["text"],
                ]
            )
            text_scores.append(self._keyword_score(query, combined))
        text_scores = np.array(text_scores)

        # 2. Optional semantic reranking
        sem_scores = self._semantic_score(query)
        if sem_scores is not None:
            combined = KEYWORD_WEIGHT * text_scores + SEMANTIC_WEIGHT * sem_scores
        else:
            combined = text_scores

        # 3. Deduplicate by group and return top sections (ignore zero-score groups)
        group_best: Dict[str, Tuple[int, float]] = {}
        for i, score in enumerate(combined):
            if score <= 0:
                continue
            key = self._group_key(self.metadata[i])
            if key not in group_best or score > group_best[key][1]:
                group_best[key] = (i, score)

        ranked = sorted(group_best.values(), key=lambda x: x[1], reverse=True)[:top_k]

        results = []
        for start_idx, score in ranked:
            key = self._group_key(self.metadata[start_idx])
            indices = self.groups.get(key, [start_idx])
            texts = [self.chunks[i]["text"] for i in sorted(indices)]
            meta = self.metadata[start_idx]
            breadcrumb = meta.get("breadcrumb", meta.get("act", ""))
            full_text = "\n".join(texts)
            if breadcrumb:
                full_text = f"[{breadcrumb}]\n{full_text}"
            results.append(
                {
                    "act": meta.get("act", "Unknown Act"),
                    "title": meta.get("title", ""),
                    "breadcrumb": breadcrumb,
                    "text": full_text,
                    "score": float(score),
                }
            )

        return results

    def get_context(self, query: str, top_k: int = 5) -> str:
        results = self.retrieve(query, top_k=top_k)
        if not results:
            return "No relevant law excerpts found."
        parts = []
        for i, r in enumerate(results, 1):
            header = f"[{i}] {r['act']}"
            if r["breadcrumb"]:
                header += f" — {r['breadcrumb']}"
            parts.append(f"{header}\n{r['text']}")
        return "\n\n---\n\n".join(parts)
