"""Text cleaning module for academic papers"""
import re
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class TextCleaner:
    """
    Normalize and clean academic paper text for optimal embedding quality.
    
    Features:
    - Keep only paper body (trim front matter and references)
    - Remove author/affiliation block
    - Remove headers and footers
    - Remove emails and URLs
    - Remove citations (configurable)
    - Normalize whitespace
    - Remove PDF extraction artifacts
    - Fix hyphenation and unwrap soft line breaks
    - (Optional) Remove figure/table callouts
    """
    
    def __init__(
        self,
        remove_citations: bool = False,
        remove_urls: bool = True,
        remove_emails: bool = True,
        remove_references: bool = True,
        remove_headers_footers: bool = True,
        normalize_whitespace: bool = True,
        keep_only_body: bool = True,
        remove_figure_table_callouts: bool = True,
        body_start_markers: Optional[List[str]] = None,
        body_end_markers: Optional[List[str]] = None,
        remove_non_english: bool = False
    ):
        """
        Initialize TextCleaner
        
        Args:
            remove_citations: Remove in-text citations like [1,2,3] or (Author, 2023)
            remove_urls: Remove URLs
            remove_emails: Remove email addresses
            remove_references: Remove reference/bibliography sections (also covered by body_end_markers)
            remove_headers_footers: Remove common headers/footers
            normalize_whitespace: Normalize whitespace and newlines
            keep_only_body: Trim everything before Abstract/Introduction and after References/etc.
            remove_figure_table_callouts: Remove 'Fig. 2', 'Figure 3a', 'Table S1' mentions
            body_start_markers: Custom list of section headers to start body from
            body_end_markers: Custom list of section headers to end body at
        """
        self.remove_citations = remove_citations
        self.remove_urls = remove_urls
        self.remove_emails = remove_emails
        self.remove_references = remove_references
        self.remove_headers_footers = remove_headers_footers
        self.normalize_whitespace = normalize_whitespace
        self.keep_only_body = keep_only_body
        self.remove_figure_table_callouts = remove_figure_table_callouts

        self.body_start_markers = body_start_markers or [
            r'\bAbstract\b',
            r'\bSummary\b',
            r'\bIntroduction\b',
        ]
        self.body_end_markers = body_end_markers or [
            r'\bReferences\b',
            r'\bBibliography\b',
            r'\bWorks\s+Cited\b',
            r'\bAcknowledg(e)?ments?\b',
            r'\bAppendix\b',
            r'\bSupplementary\s+Material(s)?\b',
            r'\bFunding\b',
            r'\bConflict(s)?\s+of\s+Interest\b',
        ]

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
        
        # Citation patterns (improved)
        # [1], [1,2,3], [3–11], [12;14;18], [12, 14–16, 18]
        self.bracket_citation_pattern = re.compile(
            r'\[\s*\d+(?:\s*[,;–-]\s*\d+|\s*–\s*\d+)*\s*\]'
        )
        # (Author, 2023), (Smith & Jones, 2019), (Zhou et al., 2023)
        self.paren_citation_pattern = re.compile(
            r'\((?:[A-Z][A-Za-z\-]+(?:\s*&\s*[A-Z][A-Za-z\-]+)?(?:\s+et\s+al\.)?,?\s*\d{4}[a-z]?)\)'
        )
        # (2023), (2023a)
        self.paren_year_pattern = re.compile(r'\(\s*\d{4}[a-z]?\s*\)')

        # Figure/Table callouts
        self.figure_table_pattern = re.compile(
            r'\b(Fig(?:ure)?\.?\s*\w+|Table\s*\w+)\b'
        )
        
        # Reference section patterns (legacy support)
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
            '\u2020': '',   # dagger
            '\u2021': '',   # double dagger
        }

        # Author/affiliation heuristics
        self.affil_words = re.compile(
            r'\b(University|Institute|Laborator(y|ies)|Dept\.?|Department|School|College|Center|Centre|Hospital|Clinic|Research|R&D|AI Lab|Cambridge|Chicago|Harvard|Pittsburgh|Denmark|USA|UK|China|IL|MA|PA|NY)\b',
            re.IGNORECASE
        )
        self.superscript_markers = re.compile(r'[\*\u2020\u2021]|\b\d+\b')

        # Section heading in ALL CAPS to drop if needed
        self.allcaps_heading = re.compile(r'^\s*[A-Z][A-Z \-]{3,}\s*$', re.MULTILINE)

        # Hyphenation at line breaks: "thera-\n peutic" -> "therapeutic"
        self.hyphen_linebreak = re.compile(r'(\w)-\n(\w)')

        # Soft line breaks inside paragraphs (unwrap single newlines)
        self.single_newline = re.compile(r'([^\n])\n(?!\n)')

    def clean(self, text: str) -> str:
        """
        Clean a single text document
        """
        if not text or not isinstance(text, str):
            return ""
        
        # 1) Remove control characters and PDF artifacts
        text = self._remove_pdf_artifacts(text)
        
        # 2) Normalize unicode characters
        text = self._normalize_unicode(text)

        # 3) Keep only the body window (trim front matter/tail)
        if self.keep_only_body:
            text = self._keep_only_body(text)
            text = self._remove_author_block(text)
            text = self._remove_boilerplate_lines(text)

        # 4) Remove URLs / emails
        if self.remove_urls:
            text = self._remove_urls(text)
        if self.remove_emails:
            text = self._remove_emails(text)
        
        # 5) Remove citations
        if self.remove_citations:
            text = self._remove_citations(text)

        # 6) Optional: remove figure/table callouts
        if self.remove_figure_table_callouts:
            text = self.figure_table_pattern.sub(' ', text)

        # 7) Remove headers and footers
        if self.remove_headers_footers:
            text = self._remove_headers_footers(text)

        # 8) Fix hyphenation & unwrap soft line breaks (preserve paragraph breaks)
        text = self._fix_hyphenation_and_unwrap(text)

        # 9) Fix intra-word spacing artifacts & stray hyphens
        text = self._fix_intra_word_spacing(text)

        # 10) Remove reference section (fallback)
        if self.remove_references:
            text = self._remove_references(text)

        if getattr(self, 'remove_non_english', False):
            text = self._drop_non_english_lines(text)

        
        # 10) Normalize whitespace
        if self.normalize_whitespace:
            text = self._normalize_whitespace(text)
        
        # 11) Drop stray ALL-CAPS headings that slipped through
        text = self.allcaps_heading.sub('', text)

        return text.strip()
    
    def clean_batch(self, texts: List[str]) -> List[str]:
        return [self.clean(text) for text in texts]
    
    # ---------- internals ----------

    def _keep_only_body(self, text: str) -> str:
        """Trim everything before first body start marker and after first end marker."""
        start_idx = 0
        for pat in self.body_start_markers:
            m = re.search(pat, text, flags=re.IGNORECASE)
            if m:
                start_idx = m.start()
                # remove the heading word itself
                heading = re.compile(pat, re.IGNORECASE)
                text = text[start_idx:]
                text = heading.sub('', text, count=1)
                break

        # Cut tail at first end marker
        earliest_end = None
        for pat in self.body_end_markers:
            m = re.search(pat, text, flags=re.IGNORECASE)
            if m:
                earliest_end = m.start() if earliest_end is None else min(earliest_end, m.start())
        if earliest_end is not None:
            text = text[:earliest_end]

        return text.strip()

    def _remove_author_block(self, text: str) -> str:
        """
        Remove early paragraphs likely to be author/affiliation lines.
        Heuristics: high comma density + affiliation words or superscripts within first ~3 paragraphs.
        """
        paras = re.split(r'\n{2,}', text.strip())
        cleaned = []
        skipped = 0
        for i, p in enumerate(paras):
            p_stripped = p.strip()
            if i <= 3:  # only check the first few paragraphs
                comma_dense = p_stripped.count(',') >= 3
                has_affil = bool(self.affil_words.search(p_stripped))
                has_sup = bool(self.superscript_markers.search(p_stripped))
                looks_author = comma_dense and (has_affil or has_sup)
                # also drop a short title block if it’s just 1–2 lines and mostly uppercase
                short_lines = len(p_stripped.splitlines()) <= 3
                mostly_upper = sum(c.isupper() for c in p_stripped if c.isalpha()) >= 0.6 * max(1, sum(c.isalpha() for c in p_stripped))
                if looks_author or (short_lines and mostly_upper and 'abstract' not in p_stripped.lower()):
                    skipped += 1
                    continue
            cleaned.append(p_stripped)
        if skipped and cleaned:
            return '\n\n'.join(cleaned)
        return text

    def _fix_hyphenation_and_unwrap(self, text: str) -> str:
        # de-hyphenate across line breaks
        text = self.hyphen_linebreak.sub(r'\1\2', text)
        # unwrap single newlines (keep paragraph breaks)
        text = self.single_newline.sub(r'\1 ', text)
        return text

    def _fix_intra_word_spacing(self, text: str) -> str:
        text = re.sub(r'(?<=\w)\s*-\s*(?=\w)', '-', text)
        text = re.sub(r'\b([A-Z])\s+([a-z])', r'\1\2', text)
        text = re.sub(r'(?<=\b[A-Za-z])\s+(?=[a-z])', '', text)
        text = re.sub(r'^\s*[-–—]{2,}\s*', '', text, flags=re.MULTILINE)
        return text

    def _remove_pdf_artifacts(self, text: str) -> str:
        text = self.control_chars_pattern.sub(' ', text)
        text = self.form_feed_pattern.sub('\n', text)
        return text
    
    def _normalize_unicode(self, text: str) -> str:
        for old, new in self.unicode_replacements.items():
            text = text.replace(old, new)
        return text
    
    def _remove_references(self, text: str) -> str:
        # Legacy fallback—body_end_markers already handle this earlier
        earliest_pos = len(text)
        for pattern in self.reference_headers:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                earliest_pos = min(earliest_pos, match.start())
        if earliest_pos < len(text):
            text = text[:earliest_pos]
        return text
    
    def _remove_urls(self, text: str) -> str:
        return self.url_pattern.sub('', text)
    
    def _remove_emails(self, text: str) -> str:
        return self.email_pattern.sub('', text)
    
    def _remove_citations(self, text: str) -> str:
        text = self.bracket_citation_pattern.sub('', text)
        text = self.paren_citation_pattern.sub('', text)
        text = self.paren_year_pattern.sub('', text)
        return text
    
    def _remove_headers_footers(self, text: str) -> str:
        """
        Light heuristic for headers/footers in flat text:
        - Drop standalone page numbers
        - Drop very short isolated lines at page boundaries
        """
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            s = line.strip()
            if not s:
                cleaned_lines.append(line)
                continue
            if re.fullmatch(r'\d+', s):
                continue
            # discard super-short isolated lines that look like running heads
            if len(s) <= 3:
                continue
            cleaned_lines.append(line)
        return '\n'.join(cleaned_lines)

    def _remove_boilerplate_lines(self, text: str) -> str:
        text = re.sub(r'\bIndex\s+Terms\s*[-–—]\s*.*?(?:\n\n|$)', '\n', text, flags=re.IGNORECASE|re.DOTALL)
        text = re.sub(r'\bPreprint\.\s*Under\s*Review\.?:?\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^\s*[IVXLC]+\.\s+[A-Z][A-Z \-]{2,}\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'(^|\n)\s*:\s*An\s+illustration.*?(?=\n\n|$)', r'\1', text, flags=re.IGNORECASE|re.DOTALL)
        return text

    def _drop_non_english_lines(self, text: str, ascii_ratio: float = 0.9) -> str:
        lines, kept = text.splitlines(), []
        for ln in lines:
            raw = ln.strip()
            raw = re.sub(r'\s*\((en|fr|ar|ja|zh|de|es|it|pt|ru)\)\s*', ' ', raw, flags=re.IGNORECASE)
            if not raw:
                kept.append('')
                continue
            ascii_chars = sum(ord(c) < 128 for c in raw)
            if ascii_chars / max(1, len(raw)) >= ascii_ratio:
                kept.append(raw)
        return '\n'.join(kept)

    
    
    def _normalize_whitespace(self, text: str) -> str:
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        return text
    
    def get_stats(self, original: str, cleaned: str) -> dict:
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
    remove_references: bool = True,
    keep_only_body: bool = True
) -> str:
    cleaner = TextCleaner(
        remove_citations=remove_citations,
        remove_urls=remove_urls,
        remove_emails=remove_emails,
        remove_references=remove_references,
        keep_only_body=keep_only_body
    )
    return cleaner.clean(text)
