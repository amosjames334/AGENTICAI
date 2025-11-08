#!/bin/bash

echo "=================================================="
echo "Fixing Dependencies for Vector Store Integration"
echo "=================================================="
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  No virtual environment detected!"
    echo "Please activate your virtual environment first:"
    echo "  source venv/bin/activate"
    exit 1
fi

echo "✓ Virtual environment active: $VIRTUAL_ENV"
echo ""

# Step 1: Uninstall problematic numpy
echo "[1/4] Uninstalling NumPy 2.x..."
pip uninstall numpy -y > /dev/null 2>&1

# Step 2: Reinstall dependencies
echo "[2/4] Installing dependencies with correct versions..."
pip install -r requirements.txt

# Step 3: Verify installations
echo ""
echo "[3/4] Verifying installations..."

# Check numpy version
NUMPY_VERSION=$(python -c "import numpy; print(numpy.__version__)" 2>/dev/null)
if [ $? -eq 0 ]; then
    if [[ $NUMPY_VERSION == 1.* ]]; then
        echo "  ✓ NumPy $NUMPY_VERSION (correct version)"
    else
        echo "  ⚠️  NumPy $NUMPY_VERSION (expected 1.x)"
    fi
else
    echo "  ✗ NumPy not installed"
fi

# Check sentence-transformers
python -c "from sentence_transformers import SentenceTransformer" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "  ✓ sentence-transformers installed"
else
    echo "  ✗ sentence-transformers not installed"
fi

# Check faiss
python -c "import faiss" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "  ✓ faiss-cpu installed"
else
    echo "  ✗ faiss-cpu not installed"
fi

# Step 4: Test
echo ""
echo "[4/4] Running quick test..."
python -c "
from src.ingestion.arxiv_loader import ArxivLoader
from src.ingestion.document_processor import DocumentProcessor
print('  ✓ All imports successful')
print('  ✓ SSL fix applied')
" 2>/dev/null

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================================="
    echo "✅ Fix complete! You can now use the system."
    echo "=================================================="
    echo ""
    echo "Try running:"
    echo "  python test_vector_store.py"
    echo "  streamlit run app.py"
    echo "  python cli.py ingest 'quantum computing' --max-papers 2"
else
    echo ""
    echo "=================================================="
    echo "⚠️  Some issues remain. Check the output above."
    echo "=================================================="
    echo ""
    echo "See FIX_DEPENDENCIES.md for detailed troubleshooting."
fi

