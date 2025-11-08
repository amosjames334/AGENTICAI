"""Test script to verify setup and configuration"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_imports():
    """Test that all required imports work"""
    print("Testing imports...")
    try:
        import langchain
        import langgraph
        import openai
        import streamlit
        import arxiv
        import pypdf
        import faiss
        print("✅ All core packages imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_env_config():
    """Test environment configuration"""
    print("\nTesting environment configuration...")
    try:
        from dotenv import load_dotenv
        import os
        
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            print("⚠️  OPENAI_API_KEY not found in .env file")
            print("   Please add your API key to .env")
            return False
        elif api_key == "your_openai_api_key_here":
            print("⚠️  OPENAI_API_KEY appears to be placeholder")
            print("   Please add your actual API key to .env")
            return False
        else:
            print(f"✅ API key configured (starts with: {api_key[:8]}...)")
            return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False


def test_modules():
    """Test that custom modules can be imported"""
    print("\nTesting custom modules...")
    try:
        from ingestion.arxiv_loader import ArxivLoader
        from ingestion.document_processor import DocumentProcessor
        from agents.agent_definitions import ResearchAgent, CriticAgent
        from agents.research_graph import ResearchWorkflow
        from utils.config import Config
        from utils.logger import setup_logger
        
        print("✅ All custom modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Module import error: {e}")
        return False


def test_directories():
    """Test that required directories exist"""
    print("\nTesting directory structure...")
    required_dirs = [
        "data/papers",
        "data/cache",
        "src/agents",
        "src/ingestion",
        "src/tools",
        "src/utils",
        "examples"
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists():
            print(f"✅ {dir_path}")
        else:
            print(f"❌ {dir_path} - missing")
            all_exist = False
    
    return all_exist


def test_arxiv_connection():
    """Test arXiv API connection"""
    print("\nTesting arXiv API connection...")
    try:
        from ingestion.arxiv_loader import ArxivLoader
        loader = ArxivLoader()
        
        # Try a simple search
        papers = loader.search_papers("machine learning", max_results=1)
        
        if papers and len(papers) > 0:
            print(f"✅ arXiv API working - found test paper: {papers[0]['title'][:50]}...")
            return True
        else:
            print("⚠️  arXiv API returned no results")
            return False
    except Exception as e:
        print(f"❌ arXiv API error: {e}")
        return False


def main():
    """Run all tests"""
    print("="*60)
    print("Research Agent System - Setup Test")
    print("="*60)
    
    results = {
        "Imports": test_imports(),
        "Environment": test_env_config(),
        "Modules": test_modules(),
        "Directories": test_directories(),
    }
    
    # Only test arXiv if other tests pass
    if all(results.values()):
        results["arXiv API"] = test_arxiv_connection()
    
    print("\n" + "="*60)
    print("Test Results Summary")
    print("="*60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20s} {status}")
    
    print("="*60)
    
    if all(results.values()):
        print("\n🎉 All tests passed! System is ready to use.")
        print("\nQuick start:")
        print("  1. Run web UI: streamlit run app.py")
        print("  2. Or CLI: python cli.py \"your research query\"")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  - Run: pip install -r requirements.txt")
        print("  - Add OPENAI_API_KEY to .env file")
        print("  - Run: ./setup.sh")
        return 1


if __name__ == "__main__":
    sys.exit(main())

