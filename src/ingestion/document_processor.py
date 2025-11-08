"""Document processing and vector store management"""
from __future__ import annotations
import os
import re
import json
import pathlib
from typing import List, Dict, Tuple, Optional
import logging

import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import faiss

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _ensure_dir(p: pathlib.Path):
    """Ensure directory exists"""
    p.mkdir(parents=True, exist_ok=True)


def clean_text(t: str) -> str:
    """Clean text by removing null characters and extra whitespace"""
    t = t.replace("\x00", " ")
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def chunk_text(text: str, size: int = 900, overlap: int = 150) -> List[str]:
    """
    Chunk text into overlapping segments
    
    Args:
        text: Text to chunk
        size: Number of words per chunk
        overlap: Number of words to overlap between chunks
        
    Returns:
        List of text chunks
    """
    words = text.split()
    out = []
    i = 0
    while i < len(words):
        out.append(" ".join(words[i:i+size]))
        i += max(1, size - overlap)
    return [c for c in out if c.strip()]


class DocumentProcessor:
    """
    Process documents into vector embeddings and manage FAISS index
    
    - Extracts text from PDFs
    - Chunks text into manageable pieces
    - Creates embeddings using sentence-transformers
    - Builds and manages FAISS vector store
    """
    
    def __init__(self, data_dir: str = "data", model_name: str = DEFAULT_EMBED_MODEL):
        self.data_dir = pathlib.Path(data_dir)
        self.vector_dir = self.data_dir / "vector_store"
        _ensure_dir(self.vector_dir)

        self.model_name = model_name
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)

        # Paths for persisted data
        self.index_path = self.vector_dir / "index.faiss"
        self.texts_path = self.vector_dir / "texts.npy"
        self.meta_path = self.vector_dir / "meta.json"

        self.index = None
        self.texts = None
        self.meta = None

    # ---------- PDF -> text ----------
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from a PDF file
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted and cleaned text
        """
        try:
            reader = PdfReader(pdf_path)
            raw = " ".join([page.extract_text() or "" for page in reader.pages])
            return clean_text(raw)
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
            return ""

    # ---------- Build store ----------
    def build_store_from_pdfs(self, pdf_paths: List[str]) -> Tuple[int, int]:
        """
        Build vector store from list of PDF files
        
        Args:
            pdf_paths: List of paths to PDF files
            
        Returns:
            Tuple of (number of chunks, embedding dimension)
        """
        texts = []
        meta = []
        
        for pdf in pdf_paths:
            if not pdf or not os.path.exists(pdf):
                logger.warning(f"Missing PDF: {pdf}")
                continue
            
            try:
                logger.info(f"Processing: {pdf}")
                txt = self.extract_text_from_pdf(pdf)
                
                if not txt:
                    logger.warning(f"No text extracted from {pdf}")
                    continue
                
                chunks = chunk_text(txt, size=900, overlap=150)
                logger.info(f"  Created {len(chunks)} chunks from {pdf}")

                for i, c in enumerate(chunks):
                    texts.append(c)
                    meta.append({"pdf_path": pdf, "chunk_id": i})
            except Exception as e:
                logger.error(f"Failed to process {pdf}: {e}")

        if not texts:
            raise RuntimeError("No texts extracted; cannot build vector store.")

        logger.info(f"Creating embeddings for {len(texts)} chunks...")
        emb = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        
        logger.info(f"Building FAISS index (dimension={emb.shape[1]})...")
        index = faiss.IndexFlatIP(emb.shape[1])
        index.add(emb.astype(np.float32))

        # Persist to disk
        logger.info("Saving vector store to disk...")
        faiss.write_index(index, str(self.index_path))
        np.save(self.texts_path, np.array(texts, dtype=object))
        with open(self.meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        self.index, self.texts, self.meta = index, texts, meta
        logger.info(f"✅ Vector store built: {len(texts)} chunks, {emb.shape[1]} dimensions")
        return len(texts), emb.shape[1]

    # ---------- Load store ----------
    def load_store(self) -> bool:
        """
        Load vector store from disk
        
        Returns:
            True if successfully loaded, False otherwise
        """
        if not self.index_path.exists() or not self.texts_path.exists() or not self.meta_path.exists():
            logger.warning("Vector store files not found")
            return False
        
        try:
            logger.info("Loading vector store from disk...")
            self.index = faiss.read_index(str(self.index_path))
            self.texts = np.load(self.texts_path, allow_pickle=True)
            with open(self.meta_path) as f:
                self.meta = json.load(f)
            logger.info(f"✅ Vector store loaded: {len(self.texts)} chunks")
            return True
        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            return False

    # ---------- Query store ----------
    def query(self, query: str, k: int = 5) -> List[Dict]:
        """
        Query the vector store for similar text chunks
        
        Args:
            query: Query string
            k: Number of results to return
            
        Returns:
            List of dictionaries containing score, text, and metadata
        """
        if self.index is None:
            if not self.load_store():
                raise RuntimeError("Vector store not built yet. Run build_store_from_pdfs first.")
        
        logger.info(f"Querying vector store: '{query[:50]}...'")
        q = self.model.encode([query], normalize_embeddings=True)
        D, I = self.index.search(q.astype(np.float32), k)
        
        hits = []
        for score, idx in zip(D[0], I[0]):
            if idx < len(self.texts):
                m = self.meta[int(idx)]
                hits.append({
                    "score": float(score),
                    "text": str(self.texts[int(idx)]),
                    "meta": m
                })
        
        logger.info(f"Retrieved {len(hits)} results")
        return hits
    
    def store_exists(self) -> bool:
        """Check if a vector store exists on disk"""
        return (self.index_path.exists() and 
                self.texts_path.exists() and 
                self.meta_path.exists())
