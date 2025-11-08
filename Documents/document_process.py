# src/ingestion/document_processor.py
from __future__ import annotations
import os
import re
import json
import pathlib
from typing import List, Dict, Tuple, Optional

import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import faiss

DEFAULT_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def _ensure_dir(p: pathlib.Path):
    p.mkdir(parents=True, exist_ok=True)

def clean_text(t: str) -> str:
    t = t.replace("\x00", " ")
    t = re.sub(r"\s+", " ", t)
    return t.strip()

def chunk_text(text: str, size: int = 900, overlap: int = 150) -> List[str]:
    words = text.split()
    out = []
    i = 0
    while i < len(words):
        out.append(" ".join(words[i:i+size]))
        i += max(1, size - overlap)
    return [c for c in out if c.strip()]

class DocumentProcessor:
    """
    - Extracts text from PDFs
    - Chunks & embeds
    - Builds / loads / queries FAISS vector store
    """
    def __init__(self, data_dir: str = "data", model_name: str = DEFAULT_EMBED_MODEL):
        self.data_dir = pathlib.Path(data_dir)
        self.vector_dir = self.data_dir / "vector_store"
        _ensure_dir(self.vector_dir)

        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

        # paths
        self.index_path = self.vector_dir / "index.faiss"
        self.texts_path = self.vector_dir / "texts.npy"
        self.meta_path = self.vector_dir / "meta.json"

        self.index = None
        self.texts = None
        self.meta = None

    # ---------- PDF -> text ----------
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        reader = PdfReader(pdf_path)
        raw = " ".join([page.extract_text() or "" for page in reader.pages])
        return clean_text(raw)

    # ---------- Build store ----------
    def build_store_from_pdfs(self, pdf_paths: List[str]) -> Tuple[int, int]:
        """
        Returns (#chunks, embedding_dim)
        """
        texts = []
        meta = []
        for pdf in pdf_paths:
            if not pdf or not os.path.exists(pdf):
                print(f"[DocumentProcessor] Missing pdf: {pdf}")
                continue
            try:
                txt = self.extract_text_from_pdf(pdf)
                chunks = chunk_text(txt, size=900, overlap=150)

                for i, c in enumerate(chunks):
                    texts.append(c)
                    meta.append({"pdf_path": pdf, "chunk_id": i})
            except Exception as e:
                print(f"[DocumentProcessor] Failed to process {pdf}: {e}")

        if not texts:
            raise RuntimeError("No texts extracted; cannot build vector store.")

        emb = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        index = faiss.IndexFlatIP(emb.shape[1])
        index.add(emb.astype(np.float32))

        # persist
        faiss.write_index(index, str(self.index_path))
        np.save(self.texts_path, np.array(texts, dtype=object))
        with open(self.meta_path, "w") as f:
            json.dump(meta, f)

        self.index, self.texts, self.meta = index, texts, meta
        return len(texts), emb.shape[1]

    # ---------- Load store ----------
    def load_store(self) -> bool:
        if not self.index_path.exists() or not self.texts_path.exists() or not self.meta_path.exists():
            return False
        self.index = faiss.read_index(str(self.index_path))
        self.texts = np.load(self.texts_path, allow_pickle=True)
        with open(self.meta_path) as f:
            self.meta = json.load(f)
        return True

    # ---------- Query store ----------
    def query(self, query: str, k: int = 5) -> List[Dict]:
        if self.index is None:
            if not self.load_store():
                raise RuntimeError("Vector store not built yet.")
        q = self.model.encode([query], normalize_embeddings=True)
        D, I = self.index.search(q.astype(np.float32), k)
        hits = []
        for score, idx in zip(D[0], I[0]):
            m = self.meta[int(idx)]
            hits.append({
                "score": float(score),
                "text": str(self.texts[int(idx)]),
                "meta": m
            })
        return hits
