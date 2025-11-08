# src/ingestion/arxiv_loader.py
from __future__ import annotations
import re
import os
import json
import pathlib
from typing import List, Dict, Optional
import arxiv

# Safe, portable filename
def _slugify(text: str, max_len: int = 80) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_")
    return text[:max_len] if text else "paper"

class ArxivLoader:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = pathlib.Path(data_dir)
        self.papers_dir = self.data_dir / "papers"
        self.papers_dir.mkdir(parents=True, exist_ok=True)

    def search(self, query: str, max_results: int = 5, sort_by=arxiv.SortCriterion.Relevance) -> List[Dict]:
        results = arxiv.Search(query=query, max_results=max_results, sort_by=sort_by)
        out = []
        for r in results.results():
            out.append({
                "title": r.title,
                "authors": [a.name for a in r.authors],
                "abstract": r.summary,
                "published": r.published.strftime("%Y-%m-%d") if r.published else None,
                "arxiv_id": r.entry_id,   # full url-like id
                "pdf_url": r.pdf_url
            })
        return out

    def _filename_for(self, title: str) -> pathlib.Path:
        slug = _slugify(title)
        return self.papers_dir / f"{slug}.pdf"

    def download_pdf(self, paper: Dict) -> Optional[pathlib.Path]:
        """Downloads PDF for a single paper dict (from self.search) -> returns path or None."""
        try:
            # arxiv lib needs an arxiv id; we can re-search by title to get a Result object:
            query = f'ti:"{paper["title"]}"'
            results = arxiv.Search(query=query, max_results=1, sort_by=arxiv.SortCriterion.Relevance)
            res = next(results.results())
            fn = self._filename_for(res.title)
            if fn.exists() and fn.stat().st_size > 0:
                return fn
            res.download_pdf(filename=str(fn))
            return fn
        except Exception as e:
            print(f"[ArxivLoader] Failed to download PDF for: {paper.get('title')} -> {e}")
            return None

    def download_selected(self, selected_papers: List[Dict]) -> List[Dict]:
        """Takes list of paper dicts; augments with local pdf_path if downloaded."""
        enriched = []
        for p in selected_papers:
            path = self.download_pdf(p)
            p2 = dict(p)
            p2["pdf_path"] = str(path) if path else None
            enriched.append(p2)
        # cache a small manifest (optional)
        manifest = self.papers_dir / "manifest.json"
        manifest.write_text(json.dumps(enriched, indent=2))
        return enriched
