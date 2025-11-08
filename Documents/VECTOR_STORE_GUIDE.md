# Vector Store Integration Guide

## Overview

This guide explains the new PDF→Chunks→Vector Store pipeline that has been integrated into the Research Agent System. This enhancement allows agents to retrieve evidence from full PDF content instead of just abstracts.

## What's New

### 1. **PDF Download & Processing**
- Download PDFs from arXiv for selected papers
- Extract text from PDFs using pypdf
- Clean and chunk text into manageable segments (900 words with 150-word overlap)

### 2. **Vector Store with Sentence Transformers**
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional)
- Vector store: FAISS (Facebook AI Similarity Search)
- Persistent storage in `data/vector_store/`

### 3. **Enhanced Agent Retrieval**
- ResearchAgent now queries the vector store for relevant evidence
- Falls back to abstracts if vector store not available
- Top-k retrieval with similarity scores

---

## Installation

### 1. Install New Dependencies

```bash
pip install -r requirements.txt
```

New packages added:
- `sentence-transformers>=2.2.0`
- `numpy>=1.24.0`

### 2. Directory Structure

The system will create the following structure:
```
data/
├── papers/           # Downloaded PDFs
│   └── manifest.json # Metadata for downloaded papers
└── vector_store/     # FAISS index and embeddings
    ├── index.faiss   # FAISS vector index
    ├── texts.npy     # Text chunks
    └── meta.json     # Chunk metadata
```

---

## Usage

### Option A: Streamlit UI (Recommended)

#### 1. Start the App
```bash
streamlit run app.py
```

#### 2. Workflow

**Step 1: Search for Papers**
- Navigate to the "📝 Research Query" tab
- Enter your research question
- Click "🔍 Search Papers"
- Review found papers

**Step 2: Download PDFs & Build Vector Store**
- Navigate to the "📚 PDF Ingestion" tab
- Click "📥 Download PDFs from arXiv"
- Wait for downloads to complete
- Click "🔧 Build Vector Store"
- Wait for processing (may take a few minutes for 10 papers)

**Step 3: Query the Vector Store (Optional)**
- In the same "📚 PDF Ingestion" tab
- Enter a specific query
- View retrieved chunks with similarity scores

**Step 4: Run Agent Analysis**
- Return to "📝 Research Query" tab
- Click "🚀 Start Agent Analysis"
- Agents will automatically use vector store if available
- View results in "🤖 Agent Collaboration" and "📊 Results" tabs

---

### Option B: Command Line Interface

The CLI now supports three commands:

#### 1. Ingest Command
Download PDFs and build vector store:

```bash
python cli.py ingest "quantum computing applications" --max-papers 10
```

Options:
- `--max-papers`: Number of papers to download (default: 10)
- `--data-dir`: Data directory path (default: data)
- `--verbose`: Enable verbose logging

#### 2. Query Command
Query the vector store:

```bash
python cli.py query "What are the main applications?" --k 5
```

Options:
- `--k`: Number of results to return (default: 5)
- `--data-dir`: Data directory path (default: data)
- `--verbose`: Enable verbose logging

#### 3. Research Command
Run full agent analysis (works with or without vector store):

```bash
python cli.py research "quantum computing applications" --max-papers 10
```

Options:
- `--max-papers`: Number of papers to analyze (default: 10)
- `--model`: OpenAI model (default: gpt-4-turbo-preview)
- `--temperature`: Temperature 0.0-1.0 (default: 0.7)
- `--output`: Output file path (default: print to console)
- `--verbose`: Enable verbose logging

#### Example Workflow

```bash
# Step 1: Download papers and build vector store
python cli.py ingest "AI for drug discovery" --max-papers 8 --verbose

# Step 2: Query the vector store
python cli.py query "What machine learning models are used?" --k 5

# Step 3: Run full research analysis (uses vector store automatically)
python cli.py research "AI for drug discovery" --max-papers 8 --output report.txt
```

---

## How It Works

### 1. PDF Download (`ArxivLoader`)

```python
from ingestion.arxiv_loader import ArxivLoader

loader = ArxivLoader()
papers = loader.search_papers("quantum computing", max_results=5)
enriched_papers = loader.download_selected(papers)
# Each paper now has 'pdf_path' field
```

### 2. Document Processing (`DocumentProcessor`)

```python
from ingestion.document_processor import DocumentProcessor

# Initialize processor
dp = DocumentProcessor(data_dir="data")

# Build vector store from PDFs
pdf_paths = [p['pdf_path'] for p in enriched_papers if p.get('pdf_path')]
n_chunks, embed_dim = dp.build_store_from_pdfs(pdf_paths)

# Query the store
hits = dp.query("What are the main findings?", k=5)
for hit in hits:
    print(f"Score: {hit['score']:.3f}")
    print(f"Text: {hit['text']}")
    print(f"Source: {hit['meta']['pdf_path']}")
```

### 3. Agent Integration

The `ResearchAgent` automatically uses the vector store:

```python
from agents.agent_definitions import retrieve_evidence

# Retrieve evidence from vector store
evidence = retrieve_evidence("quantum algorithms", k=10)

# Falls back to abstracts if vector store not available
```

---

## Configuration

### Chunking Parameters

Edit `src/ingestion/document_processor.py`:

```python
def chunk_text(text: str, size: int = 900, overlap: int = 150):
    # size: number of words per chunk
    # overlap: number of overlapping words between chunks
```

### Embedding Model

Change the model in `DocumentProcessor`:

```python
DEFAULT_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Other options:
# - "sentence-transformers/all-mpnet-base-v2" (768-dim, slower, better)
# - "sentence-transformers/paraphrase-MiniLM-L6-v2" (384-dim, fast)
```

### Vector Store Location

```python
dp = DocumentProcessor(data_dir="custom/path")
```

---

## Performance Considerations

### Storage
- Each paper: ~1-5 MB (PDF)
- Vector store: ~1-2 MB per 1000 chunks
- Example: 10 papers → ~50 MB total

### Processing Time
- PDF download: ~5-10 seconds per paper
- Text extraction: ~1-2 seconds per paper
- Embedding generation: ~2-5 seconds per paper (CPU)
- FAISS indexing: < 1 second

**Total for 10 papers: ~1-2 minutes**

### Query Performance
- Vector store query: < 100ms for k=5
- Fast enough for real-time use

---

## Troubleshooting

### Issue: "Vector store not found"
**Solution**: Run the ingest command or build the vector store in the UI first.

### Issue: PDF download fails
**Possible causes**:
- arXiv rate limiting (wait a few seconds)
- Network issues
- Invalid arXiv ID

**Solution**: The system continues with available PDFs. Re-run to retry failed downloads.

### Issue: Out of memory during embedding
**Solution**: Reduce batch size or process fewer papers at once.

### Issue: Slow embedding generation
**Solution**: 
- Use a GPU if available (install `faiss-gpu`)
- Use a smaller embedding model
- Reduce the number of chunks

---

## API Reference

### ArxivLoader

```python
class ArxivLoader:
    def __init__(self, cache_dir: str = "data/papers")
    def search_papers(self, query: str, max_results: int = 10) -> List[Dict]
    def download_paper(self, arxiv_id: str, title: str = None) -> Optional[Path]
    def download_selected(self, selected_papers: List[Dict]) -> List[Dict]
```

### DocumentProcessor

```python
class DocumentProcessor:
    def __init__(self, data_dir: str = "data", model_name: str = DEFAULT_EMBED_MODEL)
    def extract_text_from_pdf(self, pdf_path: str) -> str
    def build_store_from_pdfs(self, pdf_paths: List[str]) -> Tuple[int, int]
    def load_store(self) -> bool
    def query(self, query: str, k: int = 5) -> List[Dict]
    def store_exists(self) -> bool
```

### Helper Functions

```python
def retrieve_evidence(query: str, k: int = 5, data_dir: str = "data") -> Optional[List[Dict]]
```

---

## Example Use Cases

### 1. Deep Literature Review
```bash
# Download and index 20 papers
python cli.py ingest "transformer architecture improvements" --max-papers 20

# Query specific aspects
python cli.py query "What attention mechanisms are proposed?" --k 10
python cli.py query "What are the computational costs?" --k 10
```

### 2. Comparative Analysis
```bash
# Index papers on competing approaches
python cli.py ingest "GAN vs diffusion models for image generation" --max-papers 15

# Run comprehensive analysis
python cli.py research "GAN vs diffusion models" --max-papers 15
```

### 3. Focused Research Question
```bash
# Narrow search
python cli.py ingest "CRISPR off-target effects" --max-papers 10

# Targeted queries
python cli.py query "What methods detect off-target effects?" --k 5
```

---

## Best Practices

1. **Build vector store once**: After building, you can query it multiple times without rebuilding
2. **Use specific queries**: More specific queries yield better results
3. **Adjust k parameter**: Start with k=5, increase for broader results
4. **Monitor disk space**: Clean up `data/papers/` periodically if needed
5. **Incremental updates**: To add new papers, rebuild the vector store with all PDFs

---

## What's Next?

Potential enhancements:
- [ ] Incremental vector store updates (add papers without rebuilding)
- [ ] Multiple embedding models support
- [ ] Hybrid search (keyword + semantic)
- [ ] Citation extraction and linking
- [ ] Table and figure extraction
- [ ] Multi-modal embeddings (text + images)

---

## Questions?

For issues or feature requests, please check the project documentation or create an issue in the repository.

