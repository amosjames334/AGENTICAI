# Quick Start: Vector Store Pipeline

## 🚀 Getting Started in 3 Steps

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Ingest Papers
```bash
python cli.py ingest "your research topic" --max-papers 10
```

### Step 3: Run Analysis
```bash
python cli.py research "your research topic"
```

---

## 📋 Common Commands

### Download PDFs & Build Vector Store
```bash
python cli.py ingest "quantum computing" --max-papers 10
```

### Query Vector Store
```bash
python cli.py query "What are the main findings?" --k 5
```

### Full Research Analysis (with Vector Store)
```bash
python cli.py research "quantum computing" --max-papers 10
```

---

## 🎨 Streamlit UI

```bash
streamlit run app.py
```

Then:
1. **Search Papers** (Research Query tab)
2. **Download PDFs** (PDF Ingestion tab)
3. **Build Vector Store** (PDF Ingestion tab)
4. **Run Agent Analysis** (Research Query tab)

---

## 📂 File Structure

```
data/
├── papers/           # Downloaded PDFs
│   └── manifest.json
└── vector_store/     # FAISS index
    ├── index.faiss
    ├── texts.npy
    └── meta.json
```

---

## 🔧 Key Features

✅ **Automatic PDF Download** from arXiv  
✅ **Full-text Search** using FAISS  
✅ **Smart Chunking** (900 words, 150 overlap)  
✅ **Fast Retrieval** (<100ms queries)  
✅ **Agent Integration** (automatic fallback)  

---

## 💡 Pro Tips

- **First time?** Start with 5-8 papers
- **Specific query?** Use `--k 10` for more results
- **Save time?** Vector store persists across runs
- **Multiple topics?** Use `--data-dir custom_folder`

---

## 🆘 Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| "Vector store not found" | Run `ingest` command first |
| PDF download fails | Check internet, retry after a few seconds |
| Slow processing | Reduce `--max-papers` to 5 |
| Out of memory | Process fewer papers at once |

---

## 📚 Full Documentation

See [VECTOR_STORE_GUIDE.md](VECTOR_STORE_GUIDE.md) for complete documentation.

---

## 🎯 Example Workflow

```bash
# 1. Ingest papers on a topic
python cli.py ingest "CRISPR gene editing" --max-papers 8 --verbose

# 2. Explore the content
python cli.py query "What are the main applications?" --k 5
python cli.py query "What are the safety concerns?" --k 5

# 3. Run full agent analysis
python cli.py research "CRISPR gene editing" --output report.md

# 4. Read your report
cat report.md
```

Done! 🎉

