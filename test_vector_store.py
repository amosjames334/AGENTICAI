"""Test script for vector store integration"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ingestion.arxiv_loader import ArxivLoader
from ingestion.document_processor import DocumentProcessor


def test_arxiv_loader():
    """Test ArxivLoader functionality"""
    print("="*60)
    print("Testing ArxivLoader")
    print("="*60)
    
    loader = ArxivLoader(cache_dir="data/papers")
    
    # Test search
    print("\n1. Testing search_papers...")
    papers = loader.search_papers("quantum computing", max_results=2)
    print(f"   ✓ Found {len(papers)} papers")
    
    if papers:
        print(f"   ✓ First paper: {papers[0]['title'][:50]}...")
        
        # Test download_selected
        print("\n2. Testing download_selected...")
        enriched = loader.download_selected(papers[:1])  # Download just 1 for testing
        print(f"   ✓ Processed {len(enriched)} papers")
        
        if enriched[0].get('pdf_path'):
            print(f"   ✓ PDF downloaded: {enriched[0]['pdf_path']}")
            return enriched[0]['pdf_path']
        else:
            print("   ✗ PDF download failed")
            return None
    else:
        print("   ✗ No papers found")
        return None


def test_document_processor(pdf_path=None):
    """Test DocumentProcessor functionality"""
    print("\n" + "="*60)
    print("Testing DocumentProcessor")
    print("="*60)
    
    dp = DocumentProcessor(data_dir="data")
    
    if pdf_path and Path(pdf_path).exists():
        print("\n1. Testing extract_text_from_pdf...")
        text = dp.extract_text_from_pdf(pdf_path)
        print(f"   ✓ Extracted {len(text)} characters")
        print(f"   ✓ First 100 chars: {text[:100]}...")
        
        print("\n2. Testing build_store_from_pdfs...")
        n_chunks, embed_dim = dp.build_store_from_pdfs([pdf_path])
        print(f"   ✓ Created {n_chunks} chunks")
        print(f"   ✓ Embedding dimension: {embed_dim}")
        
        print("\n3. Testing store_exists...")
        exists = dp.store_exists()
        print(f"   ✓ Vector store exists: {exists}")
        
        print("\n4. Testing query...")
        hits = dp.query("quantum algorithms", k=3)
        print(f"   ✓ Retrieved {len(hits)} results")
        if hits:
            print(f"   ✓ Top result score: {hits[0]['score']:.3f}")
            print(f"   ✓ Top result preview: {hits[0]['text'][:100]}...")
    else:
        print("   ⚠ No PDF available for testing")
        
        # Test with empty store
        print("\n1. Testing store_exists (should be False)...")
        exists = dp.store_exists()
        print(f"   ✓ Vector store exists: {exists}")


def test_agent_integration():
    """Test agent integration"""
    print("\n" + "="*60)
    print("Testing Agent Integration")
    print("="*60)
    
    from agents.agent_definitions import retrieve_evidence
    
    print("\n1. Testing retrieve_evidence...")
    evidence = retrieve_evidence("quantum computing", k=3, data_dir="data")
    
    if evidence:
        print(f"   ✓ Retrieved {len(evidence)} evidence chunks")
        print(f"   ✓ First chunk score: {evidence[0]['score']:.3f}")
    else:
        print("   ⚠ No evidence retrieved (vector store may not be built)")


def main():
    """Run all tests"""
    print("\n" + "🧪 " + "="*58)
    print("Vector Store Integration Test Suite")
    print("="*60 + "\n")
    
    try:
        # Test 1: ArxivLoader
        pdf_path = test_arxiv_loader()
        
        # Test 2: DocumentProcessor
        test_document_processor(pdf_path)
        
        # Test 3: Agent Integration
        test_agent_integration()
        
        print("\n" + "="*60)
        print("✅ All tests completed!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

