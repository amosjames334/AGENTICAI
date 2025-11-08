"""ArXiv paper loader and parser"""
import arxiv
from typing import List, Dict, Optional
from pathlib import Path
import logging
import re
import json
import ssl
import urllib.request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fix SSL certificate verification issues on macOS
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context


def _slugify(text: str, max_len: int = 80) -> str:
    """Create a safe, portable filename from text"""
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_")
    return text[:max_len] if text else "paper"


class ArxivLoader:
    """Load and parse papers from arXiv"""
    
    def __init__(self, cache_dir: str = "data/papers"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def search_papers(
        self, 
        query: str, 
        max_results: int = 10,
        sort_by: arxiv.SortCriterion = arxiv.SortCriterion.Relevance
    ) -> List[Dict]:
        """
        Search for papers on arXiv
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            sort_by: How to sort results
            
        Returns:
            List of paper metadata dictionaries
        """
        logger.info(f"Searching arXiv for: {query}")
        
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=sort_by
        )
        
        papers = []
        for result in search.results():
            paper = {
                "title": result.title,
                "authors": [author.name for author in result.authors],
                "abstract": result.summary,
                "published": result.published.strftime("%Y-%m-%d"),
                "pdf_url": result.pdf_url,
                "arxiv_id": result.entry_id.split("/")[-1],
                "categories": result.categories,
                "primary_category": result.primary_category,
            }
            papers.append(paper)
            logger.info(f"Found: {paper['title']}")
        
        return papers
    
    def download_paper(self, arxiv_id: str, title: str = None) -> Optional[Path]:
        """
        Download a paper PDF from arXiv
        
        Args:
            arxiv_id: arXiv ID of the paper
            title: Optional title for filename generation
            
        Returns:
            Path to the downloaded PDF file
        """
        try:
            paper = next(arxiv.Search(id_list=[arxiv_id]).results())
            
            # Use title-based filename if provided, otherwise use arxiv_id
            if title:
                slug = _slugify(title)
                pdf_path = self.cache_dir / f"{slug}.pdf"
            else:
                pdf_path = self.cache_dir / f"{arxiv_id.replace('/', '_')}.pdf"
            
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                logger.info(f"Paper already cached: {pdf_path}")
                return pdf_path
            
            logger.info(f"Downloading paper: {arxiv_id}")
            paper.download_pdf(filename=str(pdf_path))
            return pdf_path
            
        except Exception as e:
            logger.error(f"Error downloading paper {arxiv_id}: {e}")
            return None
    
    def download_selected(self, selected_papers: List[Dict]) -> List[Dict]:
        """
        Download PDFs for selected papers and augment with pdf_path
        
        Args:
            selected_papers: List of paper metadata dictionaries
            
        Returns:
            List of paper dictionaries augmented with 'pdf_path' field
        """
        enriched = []
        for paper in selected_papers:
            # Download the PDF
            arxiv_id = paper.get('arxiv_id', '')
            title = paper.get('title', '')
            
            pdf_path = self.download_paper(arxiv_id, title)
            
            # Create enriched paper dict
            paper_copy = dict(paper)
            paper_copy['pdf_path'] = str(pdf_path) if pdf_path else None
            enriched.append(paper_copy)
        
        # Save manifest
        manifest_path = self.cache_dir / "manifest.json"
        try:
            with open(manifest_path, 'w') as f:
                json.dump(enriched, f, indent=2)
            logger.info(f"Saved manifest to {manifest_path}")
        except Exception as e:
            logger.warning(f"Could not save manifest: {e}")
        
        return enriched

