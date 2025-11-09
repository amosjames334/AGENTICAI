"""Text cleaning module for academic papers"""
import re
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class TextCleaner:
    """
    Normalize and clean academic paper text for optimal embedding quality.
    
    Features:
    - Remove reference sections
    - Remove headers and footers
    - Remove emails and URLs
    - Remove citations
    - Normalize whitespace
    - Remove PDF extraction artifacts
    """
    
    def __init__(
        self,
        remove_citations: bool = False,
        remove_urls: bool = True,
        remove_emails: bool = True,
        remove_references: bool = True,
        remove_headers_footers: bool = True,
        normalize_whitespace: bool = True
    ):
        """
        Initialize TextCleaner
        
        Args:
            remove_citations: Remove in-text citations like [1,2,3] or (Author, 2023)
            remove_urls: Remove URLs
            remove_emails: Remove email addresses
            remove_references: Remove reference/bibliography sections
            remove_headers_footers: Remove common headers/footers
            normalize_whitespace: Normalize whitespace and newlines
        """
        self.remove_citations = remove_citations
        self.remove_urls = remove_urls
        self.remove_emails = remove_emails
        self.remove_references = remove_references
        self.remove_headers_footers = remove_headers_footers
        self.normalize_whitespace = normalize_whitespace
        
        # Precompile regex patterns for efficiency
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for text cleaning"""
        # URL patterns
        self.url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        
        # Email patterns
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )
        
        # Citation patterns
        self.bracket_citation_pattern = re.compile(r'\[\d+(?:,\s*\d+)*\]')  # [1], [1,2,3]
        self.paren_citation_pattern = re.compile(r'\([A-Z][a-z]+(?:\s+et\s+al\.)?,?\s+\d{4}\)')  # (Author, 2023)
        self.paren_year_pattern = re.compile(r'\(\d{4}[a-z]?\)')  # (2023), (2023a)
        
        # Reference section patterns
        self.reference_headers = [
            r'\n\s*REFERENCES\s*\n',
            r'\n\s*References\s*\n',
            r'\n\s*BIBLIOGRAPHY\s*\n',
            r'\n\s*Bibliography\s*\n',
            r'\n\s*WORKS\s+CITED\s*\n',
            r'\n\s*Works\s+Cited\s*\n'
        ]
        
        # Header/footer patterns (page numbers, etc.)
        self.page_number_pattern = re.compile(r'^\s*\d+\s*$', re.MULTILINE)
        self.short_line_pattern = re.compile(r'^\s*.{1,20}\s*$', re.MULTILINE)
        
        # PDF artifacts
        self.control_chars_pattern = re.compile(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]')
        self.form_feed_pattern = re.compile(r'\f')
        
        # Unicode normalization
        self.unicode_replacements = {
            '\u2019': "'",  # Right single quotation mark
            '\u2018': "'",  # Left single quotation mark
            '\u201c': '"',  # Left double quotation mark
            '\u201d': '"',  # Right double quotation mark
            '\u2013': '-',  # En dash
            '\u2014': '--', # Em dash
            '\u2026': '...', # Horizontal ellipsis
            '\u00a0': ' ',  # Non-breaking space
            '\u2022': '*',  # Bullet point
        }
    
    def clean(self, text: str) -> str:
        """
        Clean a single text document
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        if not text or not isinstance(text, str):
            return ""
        
        # Step 1: Remove control characters and PDF artifacts
        text = self._remove_pdf_artifacts(text)
        
        # Step 2: Normalize unicode characters
        text = self._normalize_unicode(text)
        
        # Step 3: Remove reference sections
        if self.remove_references:
            text = self._remove_references(text)
        
        # Step 4: Remove URLs
        if self.remove_urls:
            text = self._remove_urls(text)
        
        # Step 5: Remove emails
        if self.remove_emails:
            text = self._remove_emails(text)
        
        # Step 6: Remove citations
        if self.remove_citations:
            text = self._remove_citations(text)
        
        # Step 7: Remove headers and footers
        if self.remove_headers_footers:
            text = self._remove_headers_footers(text)
        
        # Step 8: Normalize whitespace
        if self.normalize_whitespace:
            text = self._normalize_whitespace(text)
        
        return text.strip()
    
    def clean_batch(self, texts: List[str]) -> List[str]:
        """
        Clean multiple text documents
        
        Args:
            texts: List of raw texts to clean
            
        Returns:
            List of cleaned texts
        """
        return [self.clean(text) for text in texts]
    
    def _remove_pdf_artifacts(self, text: str) -> str:
        """Remove PDF extraction artifacts"""
        # Remove control characters
        text = self.control_chars_pattern.sub(' ', text)
        
        # Replace form feeds with newlines
        text = self.form_feed_pattern.sub('\n', text)
        
        return text
    
    def _normalize_unicode(self, text: str) -> str:
        """Normalize unicode characters"""
        for old, new in self.unicode_replacements.items():
            text = text.replace(old, new)
        return text
    
    def _remove_references(self, text: str) -> str:
        """Remove reference/bibliography sections"""
        # Find the first match of any reference header
        earliest_pos = len(text)
        for pattern in self.reference_headers:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                earliest_pos = min(earliest_pos, match.start())
        
        # Remove everything from the reference section onwards
        if earliest_pos < len(text):
            text = text[:earliest_pos]
        
        return text
    
    def _remove_urls(self, text: str) -> str:
        """Remove URLs"""
        return self.url_pattern.sub('', text)
    
    def _remove_emails(self, text: str) -> str:
        """Remove email addresses"""
        return self.email_pattern.sub('', text)
    
    def _remove_citations(self, text: str) -> str:
        """Remove in-text citations"""
        # Remove bracket citations [1,2,3]
        text = self.bracket_citation_pattern.sub('', text)
        
        # Remove parenthetical citations (Author, 2023)
        text = self.paren_citation_pattern.sub('', text)
        
        # Remove year-only citations (2023)
        text = self.paren_year_pattern.sub('', text)
        
        return text
    
    def _remove_headers_footers(self, text: str) -> str:
        """Remove common headers and footers (page numbers, short lines)"""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip very short lines (likely headers/footers)
            if len(line.strip()) <= 3:
                continue
            
            # Skip lines that are just page numbers
            if re.match(r'^\s*\d+\s*$', line):
                continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace"""
        # Multiple spaces to single space
        text = re.sub(r' +', ' ', text)
        
        # Multiple newlines to double newline (paragraph breaks)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Remove spaces at start/end of lines
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text
    
    def get_stats(self, original: str, cleaned: str) -> dict:
        """
        Get cleaning statistics
        
        Args:
            original: Original text
            cleaned: Cleaned text
            
        Returns:
            Dictionary with statistics
        """
        return {
            'original_length': len(original),
            'cleaned_length': len(cleaned),
            'chars_removed': len(original) - len(cleaned),
            'reduction_percent': (len(original) - len(cleaned)) / len(original) * 100 if original else 0,
            'original_lines': original.count('\n') + 1,
            'cleaned_lines': cleaned.count('\n') + 1
        }


# Convenience function for quick cleaning
def clean_text(
    text: str,
    remove_citations: bool = False,
    remove_urls: bool = True,
    remove_emails: bool = True,
    remove_references: bool = True
) -> str:
    """
    Quick text cleaning function
    
    Args:
        text: Text to clean
        remove_citations: Remove citations
        remove_urls: Remove URLs
        remove_emails: Remove emails
        remove_references: Remove reference sections
        
    Returns:
        Cleaned text
    """
    cleaner = TextCleaner(
        remove_citations=remove_citations,
        remove_urls=remove_urls,
        remove_emails=remove_emails,
        remove_references=remove_references
    )
    return cleaner.clean(text)

