"""Advanced document processing pipeline with metadata enrichment"""
from __future__ import annotations
import os
import re
import json
import pathlib
from typing import List, Dict, Tuple, Optional
import logging
from datetime import datetime
import sys

# Add parent directory to path for DataPipeline imports
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import faiss

# Import new modular components
from DataPipeline.preprocessing import TextCleaner, DocumentChunker, Chunk

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _ensure_dir(p: pathlib.Path):
    """Ensure directory exists"""
    p.mkdir(parents=True, exist_ok=True)


# ============================================================================
# STAGE 1: TEXT CLEANING & NORMALIZATION
# ============================================================================

def clean_text(text: str) -> str:
    """
    Advanced text cleaning and normalization
    
    - Remove null characters and control characters
    - Normalize whitespace
    - Fix common encoding issues
    - Remove page headers/footers patterns
    - Normalize unicode characters
    """
    # Remove null and control characters
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', ' ', text)
    
    # Fix common encoding issues
    replacements = {
        '\u2019': "'",  # Right single quotation mark
        '\u2018': "'",  # Left single quotation mark
        '\u201c': '"',  # Left double quotation mark
        '\u201d': '"',  # Right double quotation mark
        '\u2013': '-',  # En dash
        '\u2014': '--', # Em dash
        '\u2026': '...', # Horizontal ellipsis
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Remove common PDF artifacts
    text = re.sub(r'\f', '\n', text)  # Form feed to newline
    text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)  # Standalone page numbers
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Multiple newlines to double
    
    # Remove very short lines (likely headers/footers)
    lines = text.split('\n')
    cleaned_lines = [line for line in lines if len(line.strip()) > 3 or line.strip() == '']
    text = '\n'.join(cleaned_lines)
    
    return text.strip()


def extract_metadata_from_text(text: str) -> Dict:
    """
    Extract metadata hints from paper text
    
    Returns:
        Dictionary with extracted metadata (keywords, sections, etc.)
    """
    metadata = {
        "has_abstract": False,
        "has_introduction": False,
        "has_conclusion": False,
        "has_references": False,
        "estimated_sections": []
    }
    
    text_lower = text.lower()
    
    # Check for common sections
    if 'abstract' in text_lower[:2000]:
        metadata["has_abstract"] = True
        metadata["estimated_sections"].append("abstract")
    
    if 'introduction' in text_lower[:5000]:
        metadata["has_introduction"] = True
        metadata["estimated_sections"].append("introduction")
    
    if 'conclusion' in text_lower[-5000:]:
        metadata["has_conclusion"] = True
        metadata["estimated_sections"].append("conclusion")
    
    if 'references' in text_lower[-10000:] or 'bibliography' in text_lower[-10000:]:
        metadata["has_references"] = True
        metadata["estimated_sections"].append("references")
    
    return metadata


# ============================================================================
# STAGE 2: SEMANTIC CHUNKING
# ============================================================================

def chunk_text_semantic(text: str, target_size: int = 1000, overlap: int = 200) -> List[Dict]:
    """
    Advanced semantic chunking with overlap and boundary detection
    
    - Splits on paragraph boundaries when possible
    - Maintains context with overlapping windows
    - Respects sentence boundaries
    - Returns chunks with position metadata
    
    Args:
        text: Text to chunk
        target_size: Target number of characters per chunk
        overlap: Number of characters to overlap
        
    Returns:
        List of chunk dictionaries with text and metadata
    """
    # Split into paragraphs first
    paragraphs = re.split(r'\n\s*\n', text)
    
    chunks = []
    current_chunk = ""
    char_position = 0
    chunk_id = 0
    
    for para_idx, paragraph in enumerate(paragraphs):
        para = paragraph.strip()
        if not para:
            continue
        
        # If adding this paragraph exceeds target size, save current chunk
        if len(current_chunk) + len(para) > target_size and current_chunk:
            chunks.append({
                "text": current_chunk.strip(),
                "chunk_id": chunk_id,
                "char_start": char_position,
                "char_end": char_position + len(current_chunk),
                "paragraph_start": max(0, para_idx - 5),
                "paragraph_end": para_idx
            })
            
            # Create overlap by keeping last part of current chunk
            sentences = re.split(r'[.!?]+\s+', current_chunk)
            if len(sentences) > 1:
                # Keep last few sentences for overlap
                overlap_text = '. '.join(sentences[-3:]) + '. '
                current_chunk = overlap_text + para
            else:
                current_chunk = para
            
            char_position += len(current_chunk) - len(overlap_text if len(sentences) > 1 else "")
            chunk_id += 1
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
    
    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append({
            "text": current_chunk.strip(),
            "chunk_id": chunk_id,
            "char_start": char_position,
            "char_end": char_position + len(current_chunk),
            "paragraph_start": max(0, len(paragraphs) - 5),
            "paragraph_end": len(paragraphs)
        })
    
    return chunks


# ============================================================================
# STAGE 3: METADATA ENRICHMENT
# ============================================================================

def enrich_chunk_metadata(chunk: Dict, paper_metadata: Dict, text_metadata: Dict) -> Dict:
    """
    Enrich chunk with comprehensive metadata
    
    Args:
        chunk: Chunk dictionary from chunking stage
        paper_metadata: Paper-level metadata (title, authors, etc.)
        text_metadata: Text-level metadata (sections, keywords, etc.)
        
    Returns:
        Enriched chunk with full metadata
    """
    enriched = {
        # Original chunk data
        "text": chunk["text"],
        "chunk_id": chunk["chunk_id"],
        "char_start": chunk["char_start"],
        "char_end": chunk["char_end"],
        
        # Position metadata
        "relative_position": chunk["chunk_id"] / max(1, chunk.get("total_chunks", 1)),
        "paragraph_range": [chunk["paragraph_start"], chunk["paragraph_end"]],
        
        # Paper metadata
        "paper_title": paper_metadata.get("title", "Unknown"),
        "paper_authors": paper_metadata.get("authors", []),
        "paper_id": paper_metadata.get("arxiv_id", "unknown"),
        "pdf_path": paper_metadata.get("pdf_path", ""),
        "published_date": paper_metadata.get("published", ""),
        
        # Text characteristics
        "word_count": len(chunk["text"].split()),
        "char_count": len(chunk["text"]),
        
        # Content hints
        "has_equations": bool(re.search(r'[∫∑∏∂∇]|\$.*\$', chunk["text"])),
        "has_citations": bool(re.search(r'\[\d+\]|\(\d{4}\)', chunk["text"])),
        "has_figures": 'figure' in chunk["text"].lower() or 'fig.' in chunk["text"].lower(),
        
        # Processing metadata
        "processed_at": datetime.now().isoformat(),
        "embedding_model": DEFAULT_EMBED_MODEL
    }
    
    return enriched


# ============================================================================
# DOCUMENT PROCESSOR CLASS
# ============================================================================

class DocumentProcessor:
    """
    Advanced document processing pipeline with:
    1. Text cleaning and normalization (TextCleaner)
    2. Semantic chunking with overlap (DocumentChunker)
    3. Metadata enrichment
    4. Embedding generation
    5. FAISS indexing and storage
    """
    
    def __init__(
        self, 
        vector_store_dir: str = "data/vector_store",
        model_name: str = DEFAULT_EMBED_MODEL,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        remove_citations: bool = True,
        remove_urls: bool = True,
        remove_references: bool = True
    ):
        """
        Initialize DocumentProcessor with modular components
        
        Args:
            vector_store_dir: Directory for vector store
            model_name: Sentence transformer model name
            chunk_size: Target tokens per chunk (default: 512)
            chunk_overlap: Overlap tokens between chunks (default: 50)
            remove_citations: Remove in-text citations (default: True)
            remove_urls: Remove URLs (default: True)
            remove_references: Remove reference sections (default: True)
        """
        self.vector_store_dir = pathlib.Path(vector_store_dir)
        _ensure_dir(self.vector_store_dir)
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize modular components
        logger.info("Initializing TextCleaner...")
        self.text_cleaner = TextCleaner(
            remove_citations=remove_citations,
            remove_urls=remove_urls,
            remove_references=remove_references,
            remove_emails=True,
            remove_headers_footers=True,
            normalize_whitespace=True
        )
        
        logger.info("Initializing DocumentChunker...")
        self.doc_chunker = DocumentChunker(
            chunk_size=chunk_size,
            overlap=chunk_overlap,
            min_chunk_size=100
        )
        
        self.model_name = model_name
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        
        # Paths for persisted data
        self.index_path = self.vector_store_dir / "index.faiss"
        self.chunks_path = self.vector_store_dir / "chunks.json"
        self.metadata_path = self.vector_store_dir / "metadata.json"
        
        self.index = None
        self.chunks = []
        self.store_metadata = {}
    
    # ========================================================================
    # STAGE 1: PDF TEXT EXTRACTION
    # ========================================================================
    
    def extract_text_from_pdf(self, pdf_path: str) -> Tuple[str, Dict]:
        """
        Extract text from PDF with metadata
        
        Returns:
            Tuple of (text, extraction_metadata)
        """
        try:
            reader = PdfReader(pdf_path)
            raw_text = " ".join([page.extract_text() or "" for page in reader.pages])
            
            extraction_meta = {
                "pdf_path": pdf_path,
                "num_pages": len(reader.pages),
                "raw_length": len(raw_text),
                "extracted_at": datetime.now().isoformat()
            }
            
            return raw_text, extraction_meta
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
            return "", {}
    
    # ========================================================================
    # FULL PIPELINE: BUILD STORE FROM PDFS
    # ========================================================================
    
    def build_store_from_pdfs(
        self, 
        papers: List[Dict],
        progress_callback: Optional[callable] = None
    ) -> Tuple[int, int]:
        """
        Complete pipeline: PDFs → Cleaned Text → Chunks → Embeddings → Index
        
        Args:
            papers: List of paper dictionaries with 'pdf_path' and metadata
            progress_callback: Optional callback(current, total, status)
            
        Returns:
            Tuple of (number of chunks, embedding dimension)
        """
        all_chunks = []
        
        logger.info(f"Processing {len(papers)} papers through pipeline...")
        
        for idx, paper in enumerate(papers):
            pdf_path = paper.get('pdf_path')
            
            if not pdf_path or not os.path.exists(pdf_path):
                logger.warning(f"Missing PDF: {pdf_path}")
                continue
            
            try:
                if progress_callback:
                    progress_callback(idx + 1, len(papers), f"Processing {paper.get('title', 'Unknown')[:50]}...")
                
                logger.info(f"[{idx+1}/{len(papers)}] Processing: {pdf_path}")
                
                # STAGE 1: Extract text
                raw_text, extraction_meta = self.extract_text_from_pdf(pdf_path)
                if not raw_text:
                    continue
                
                # STAGE 2: Clean text using TextCleaner
                cleaned_text = self.text_cleaner.clean(raw_text)
                text_meta = extract_metadata_from_text(cleaned_text)
                cleaning_stats = self.text_cleaner.get_stats(raw_text, cleaned_text)
                logger.info(f"  Cleaned: {len(raw_text)} → {len(cleaned_text)} chars ({cleaning_stats['reduction_percent']:.1f}% reduction)")
                
                # STAGE 3: Semantic chunking using DocumentChunker
                paper_id = paper.get('arxiv_id', f'paper_{idx}').replace('/', '_')
                chunk_objects = self.doc_chunker.chunk_document(
                    text=cleaned_text,
                    paper_id=paper_id,
                    preserve_sentences=True
                )
                logger.info(f"  Created {len(chunk_objects)} chunks")
                
                # Convert Chunk objects to dictionaries for enrichment
                chunks = []
                for chunk_obj in chunk_objects:
                    chunks.append({
                        'text': chunk_obj.text,
                        'chunk_id': chunk_obj.position,
                        'char_start': chunk_obj.start_char,
                        'char_end': chunk_obj.end_char,
                        'paragraph_start': 0,  # Not tracked in new chunker
                        'paragraph_end': 0,    # Not tracked in new chunker
                        'token_count': chunk_obj.token_count
                    })
                logger.info(f"  Tokens: min={min(c['token_count'] for c in chunks)}, max={max(c['token_count'] for c in chunks)}, avg={sum(c['token_count'] for c in chunks)/len(chunks):.0f}")
                
                # STAGE 4: Enrich with metadata
                for chunk in chunks:
                    chunk["total_chunks"] = len(chunks)
                    enriched = enrich_chunk_metadata(chunk, paper, text_meta)
                    all_chunks.append(enriched)
                
            except Exception as e:
                logger.error(f"Failed to process {pdf_path}: {e}")
        
        if not all_chunks:
            raise RuntimeError("No chunks created from papers")
        
        logger.info(f"Total chunks created: {len(all_chunks)}")
        
        # STAGE 5: Generate embeddings
        if progress_callback:
            progress_callback(len(papers), len(papers), "Generating embeddings...")
        
        logger.info("Generating embeddings...")
        texts = [chunk["text"] for chunk in all_chunks]
        embeddings = self.model.encode(
            texts, 
            convert_to_numpy=True, 
            normalize_embeddings=True,
            show_progress_bar=True
        )
        
        # STAGE 6: Build FAISS index
        if progress_callback:
            progress_callback(len(papers), len(papers), "Building search index...")
        
        logger.info(f"Building FAISS index (dimension={embeddings.shape[1]})...")
        self.index = faiss.IndexFlatIP(embeddings.shape[1])
        self.index.add(embeddings.astype(np.float32))
        
        # STAGE 7: Save to disk
        if progress_callback:
            progress_callback(len(papers), len(papers), "Saving to disk...")
        
        logger.info("Saving vector store...")
        self._save_store(all_chunks, embeddings)
        
        self.chunks = all_chunks
        logger.info(f"✅ Pipeline complete: {len(all_chunks)} chunks, {embeddings.shape[1]} dimensions")
        
        return len(all_chunks), embeddings.shape[1]
    
    # ========================================================================
    # STORAGE & RETRIEVAL
    # ========================================================================
    
    def _save_store(self, chunks: List[Dict], embeddings: np.ndarray):
        """Save index, chunks, and metadata"""
        # Save FAISS index
        faiss.write_index(self.index, str(self.index_path))
        
        # Save chunks
        with open(self.chunks_path, 'w') as f:
            json.dump(chunks, f, indent=2)
        
        # Save store metadata
        store_meta = {
            "created_at": datetime.now().isoformat(),
            "model_name": self.model_name,
            "num_chunks": len(chunks),
            "embedding_dim": embeddings.shape[1],
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "papers_processed": len(set(c["paper_id"] for c in chunks))
        }
        with open(self.metadata_path, 'w') as f:
            json.dump(store_meta, f, indent=2)
        
        logger.info(f"Saved to {self.vector_store_dir}")
    
    def load_store(self) -> bool:
        """Load vector store from disk"""
        if not self.store_exists():
            logger.warning("Vector store files not found")
            return False
        
        try:
            logger.info("Loading vector store...")
            self.index = faiss.read_index(str(self.index_path))
            
            with open(self.chunks_path) as f:
                self.chunks = json.load(f)
            
            with open(self.metadata_path) as f:
                self.store_metadata = json.load(f)
            
            logger.info(f"✅ Loaded: {len(self.chunks)} chunks")
            return True
        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            return False
    
    def query(self, query: str, k: int = 5, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Query vector store with optional metadata filters
        
        Args:
            query: Query string
            k: Number of results
            filters: Optional filters (e.g., {"paper_id": "2304.06043v1"})
            
        Returns:
            List of results with scores and metadata
        """
        if self.index is None:
            if not self.load_store():
                raise RuntimeError("Vector store not available")
        
        logger.info(f"Querying: '{query[:50]}...'")
        
        # Generate query embedding
        q_emb = self.model.encode([query], normalize_embeddings=True)
        
        # Search
        D, I = self.index.search(q_emb.astype(np.float32), min(k * 3, len(self.chunks)))
        
        # Collect results
        hits = []
        for score, idx in zip(D[0], I[0]):
            if idx < len(self.chunks):
                chunk = self.chunks[int(idx)]
                
                # Apply filters if provided
                if filters:
                    if not all(chunk.get(k) == v for k, v in filters.items()):
                        continue
                
                hits.append({
                    "score": float(score),
                    "text": chunk["text"],
                    "meta": {
                        "chunk_id": chunk["chunk_id"],
                        "paper_title": chunk["paper_title"],
                        "paper_id": chunk["paper_id"],
                        "pdf_path": chunk["pdf_path"],
                        "position": chunk.get("relative_position", 0),
                        "word_count": chunk["word_count"],
                        "has_equations": chunk.get("has_equations", False),
                        "has_citations": chunk.get("has_citations", False)
                    }
                })
                
                if len(hits) >= k:
                    break
        
        logger.info(f"Retrieved {len(hits)} results")
        return hits
    
    def store_exists(self) -> bool:
        """Check if vector store exists"""
        return (self.index_path.exists() and 
                self.chunks_path.exists() and 
                self.metadata_path.exists())
    
    def get_store_stats(self) -> Dict:
        """Get vector store statistics"""
        if not self.store_exists():
            return {"exists": False}
        
        if not self.store_metadata:
            with open(self.metadata_path) as f:
                self.store_metadata = json.load(f)
        
        return {
            "exists": True,
            **self.store_metadata,
            "location": str(self.vector_store_dir)
        }
