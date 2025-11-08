"""ArXiv paper loader and parser"""
import arxiv
from typing import List, Dict, Optional
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    
    def download_paper(self, arxiv_id: str) -> Optional[Path]:
        """
        Download a paper PDF from arXiv
        
        Args:
            arxiv_id: arXiv ID of the paper
            
        Returns:
            Path to the downloaded PDF file
        """
        try:
            paper = next(arxiv.Search(id_list=[arxiv_id]).results())
            pdf_path = self.cache_dir / f"{arxiv_id.replace('/', '_')}.pdf"
            
            if pdf_path.exists():
                logger.info(f"Paper already cached: {pdf_path}")
                return pdf_path
            
            logger.info(f"Downloading paper: {arxiv_id}")
            paper.download_pdf(filename=str(pdf_path))
            return pdf_path
            
        except Exception as e:
            logger.error(f"Error downloading paper {arxiv_id}: {e}")
            return None

