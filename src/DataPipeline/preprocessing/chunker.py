"""Document chunking module for splitting text into semantic chunks"""
import re
from dataclasses import dataclass
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """
    Represents a text chunk with metadata
    
    Attributes:
        chunk_id: Unique identifier (e.g., "paper1_chunk_0")
        paper_id: Parent paper identifier
        text: Chunk content
        position: Position in paper (0-indexed)
        token_count: Estimated token count
        start_char: Start character position in original text
        end_char: End character position in original text
    """
    chunk_id: str
    paper_id: str
    text: str
    position: int
    token_count: int
    start_char: int
    end_char: int
    
    def __repr__(self) -> str:
        preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"Chunk(id='{self.chunk_id}', tokens={self.token_count}, text='{preview}')"


class DocumentChunker:
    """
    Split long documents into semantic chunks with overlap for context preservation.
    
    Features:
    - Token-based chunking (not character-based)
    - Configurable overlap for context preservation
    - Sentence boundary preservation
    - Minimum chunk size enforcement
    - Position tracking
    """
    
    def __init__(
        self,
        chunk_size: int = 512,
        overlap: int = 50,
        min_chunk_size: int = 100,
        tokens_per_word: float = 1.3
    ):
        """
        Initialize DocumentChunker
        
        Args:
            chunk_size: Target number of tokens per chunk (default: 512)
            overlap: Number of overlapping tokens between chunks (default: 50)
            min_chunk_size: Minimum tokens for a valid chunk (default: 100)
            tokens_per_word: Estimated tokens per word for approximation (default: 1.3)
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size
        self.tokens_per_word = tokens_per_word
        
        # Calculate word-based sizes for approximation
        self.words_per_chunk = int(chunk_size / tokens_per_word)
        self.words_overlap = int(overlap / tokens_per_word)
        self.min_words = int(min_chunk_size / tokens_per_word)
    
    def chunk_document(
        self,
        text: str,
        paper_id: str,
        preserve_sentences: bool = True,
        preserve_paragraphs: bool = False
    ) -> List[Chunk]:
        """
        Chunk a document into semantic chunks
        
        Args:
            text: Document text to chunk
            paper_id: Identifier for the paper
            preserve_sentences: Try to preserve sentence boundaries (default: True)
            preserve_paragraphs: Try to preserve paragraph boundaries (default: False)
            
        Returns:
            List of Chunk objects
        """
        if not text or not text.strip():
            return []
        
        # Choose chunking strategy based on preferences
        if preserve_paragraphs:
            chunks = self._chunk_by_paragraphs(text, paper_id)
        elif preserve_sentences:
            chunks = self._chunk_by_sentences(text, paper_id)
        else:
            chunks = self._chunk_by_words(text, paper_id)
        
        # Filter out chunks that are too small
        chunks = [c for c in chunks if c.token_count >= self.min_chunk_size]
        
        return chunks
    
    def _chunk_by_paragraphs(self, text: str, paper_id: str) -> List[Chunk]:
        """Chunk text by paragraph boundaries"""
        paragraphs = re.split(r'\n\s*\n', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        chunks = []
        current_chunk = []
        current_words = 0
        char_position = 0
        
        for para in paragraphs:
            para_words = len(para.split())
            
            # If adding this paragraph exceeds chunk size
            if current_words + para_words > self.words_per_chunk and current_chunk:
                # Save current chunk
                chunk_text = '\n\n'.join(current_chunk)
                chunks.append(self._create_chunk(
                    chunk_text, paper_id, len(chunks), char_position
                ))
                
                # Start new chunk with overlap
                if self.words_overlap > 0:
                    # Keep last few sentences for overlap
                    overlap_text = self._get_overlap_text(current_chunk, self.words_overlap)
                    current_chunk = [overlap_text, para]
                    current_words = len(overlap_text.split()) + para_words
                else:
                    current_chunk = [para]
                    current_words = para_words
                
                char_position += len(chunk_text)
            else:
                current_chunk.append(para)
                current_words += para_words
        
        # Don't forget the last chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            chunks.append(self._create_chunk(
                chunk_text, paper_id, len(chunks), char_position
            ))
        
        return chunks
    
    def _chunk_by_sentences(self, text: str, paper_id: str) -> List[Chunk]:
        """Chunk text by sentence boundaries"""
        # Split into sentences (simple approach)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk = []
        current_words = 0
        char_position = 0
        
        for sentence in sentences:
            sentence_words = len(sentence.split())
            
            # If adding this sentence exceeds chunk size
            if current_words + sentence_words > self.words_per_chunk and current_chunk:
                # Save current chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append(self._create_chunk(
                    chunk_text, paper_id, len(chunks), char_position
                ))
                
                # Start new chunk with overlap
                if self.words_overlap > 0 and len(current_chunk) > 1:
                    # Keep last few sentences for overlap
                    overlap_sentences = self._get_last_n_words_sentences(
                        current_chunk, self.words_overlap
                    )
                    current_chunk = overlap_sentences + [sentence]
                    current_words = sum(len(s.split()) for s in current_chunk)
                else:
                    current_chunk = [sentence]
                    current_words = sentence_words
                
                char_position += len(chunk_text) + 1
            else:
                current_chunk.append(sentence)
                current_words += sentence_words
        
        # Don't forget the last chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(self._create_chunk(
                chunk_text, paper_id, len(chunks), char_position
            ))
        
        return chunks
    
    def _chunk_by_words(self, text: str, paper_id: str) -> List[Chunk]:
        """Chunk text by word count (no boundary preservation)"""
        words = text.split()
        chunks = []
        char_position = 0
        
        step = self.words_per_chunk - self.words_overlap
        
        for i in range(0, len(words), step):
            chunk_words = words[i:i + self.words_per_chunk]
            chunk_text = ' '.join(chunk_words)
            
            chunks.append(self._create_chunk(
                chunk_text, paper_id, len(chunks), char_position
            ))
            
            char_position += len(chunk_text) + 1
        
        return chunks
    
    def _create_chunk(
        self, 
        text: str, 
        paper_id: str, 
        position: int,
        start_char: int
    ) -> Chunk:
        """Create a Chunk object with metadata"""
        word_count = len(text.split())
        token_count = int(word_count * self.tokens_per_word)
        
        return Chunk(
            chunk_id=f"{paper_id}_chunk_{position}",
            paper_id=paper_id,
            text=text,
            position=position,
            token_count=token_count,
            start_char=start_char,
            end_char=start_char + len(text)
        )
    
    def _get_overlap_text(self, chunks: List[str], target_words: int) -> str:
        """Get overlap text from the end of current chunks"""
        # Join all chunks and split into words
        all_text = ' '.join(chunks)
        words = all_text.split()
        
        # Get last N words
        overlap_words = words[-target_words:] if len(words) > target_words else words
        return ' '.join(overlap_words)
    
    def _get_last_n_words_sentences(
        self, 
        sentences: List[str], 
        target_words: int
    ) -> List[str]:
        """Get the last few sentences that total approximately target_words"""
        result = []
        word_count = 0
        
        for sentence in reversed(sentences):
            sentence_words = len(sentence.split())
            if word_count + sentence_words <= target_words:
                result.insert(0, sentence)
                word_count += sentence_words
            else:
                break
        
        return result if result else [sentences[-1]]
    
    def estimate_chunk_count(self, text: str) -> int:
        """
        Estimate the number of chunks that will be produced
        
        Args:
            text: Text to estimate
            
        Returns:
            Estimated number of chunks
        """
        word_count = len(text.split())
        step = self.words_per_chunk - self.words_overlap
        return max(1, (word_count + step - 1) // step)
    
    def get_stats(self, chunks: List[Chunk]) -> dict:
        """
        Get chunking statistics
        
        Args:
            chunks: List of chunks
            
        Returns:
            Dictionary with statistics
        """
        if not chunks:
            return {
                'total_chunks': 0,
                'total_tokens': 0,
                'avg_tokens_per_chunk': 0,
                'min_tokens': 0,
                'max_tokens': 0
            }
        
        token_counts = [c.token_count for c in chunks]
        
        return {
            'total_chunks': len(chunks),
            'total_tokens': sum(token_counts),
            'avg_tokens_per_chunk': sum(token_counts) / len(token_counts),
            'min_tokens': min(token_counts),
            'max_tokens': max(token_counts),
            'total_characters': sum(len(c.text) for c in chunks)
        }


# Convenience function for quick chunking
def chunk_text(
    text: str,
    paper_id: str = "paper",
    chunk_size: int = 512,
    overlap: int = 50,
    preserve_sentences: bool = True
) -> List[Chunk]:
    """
    Quick text chunking function
    
    Args:
        text: Text to chunk
        paper_id: Paper identifier
        chunk_size: Target tokens per chunk
        overlap: Overlap tokens
        preserve_sentences: Preserve sentence boundaries
        
    Returns:
        List of Chunk objects
    """
    chunker = DocumentChunker(chunk_size=chunk_size, overlap=overlap)
    return chunker.chunk_document(text, paper_id, preserve_sentences=preserve_sentences)

