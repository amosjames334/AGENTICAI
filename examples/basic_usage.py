"""Basic usage example for Research Agent System"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
from ingestion.arxiv_loader import ArxivLoader
from agents.research_graph import ResearchWorkflow

load_dotenv()


def main():
    """Run a basic research analysis"""
    
    # Define research query
    query = "AI for climate change modeling"
    print(f"Research Query: {query}")
    print("="*60)
    
    # Step 1: Search for papers
    print("\n1. Searching arXiv for papers...")
    loader = ArxivLoader()
    papers = loader.search_papers(query, max_results=5)
    print(f"   Found {len(papers)} papers")
    
    for i, paper in enumerate(papers):
        print(f"\n   Paper {i+1}:")
        print(f"   Title: {paper['title']}")
        print(f"   Authors: {', '.join(paper['authors'][:2])}...")
    
    # Step 2: Run agent analysis
    print("\n2. Running multi-agent analysis...")
    print("   This may take a few minutes...")
    
    workflow = ResearchWorkflow(
        model="gpt-4-turbo-preview",
        temperature=0.7
    )
    
    results = workflow.run(query, papers)
    
    # Step 3: Display results
    print("\n3. Analysis complete!")
    print("="*60)
    
    print("\n🔍 RESEARCH SUMMARY")
    print("-"*60)
    print(results['research_summary'][:500] + "...\n")
    
    print("\n🎯 CRITIQUE")
    print("-"*60)
    print(results['critique'][:500] + "...\n")
    
    print("\n❓ FOLLOW-UP QUESTIONS")
    print("-"*60)
    for q in results['follow_up_questions'][:3]:
        print(f"• {q}")
    
    print("\n🧩 SYNTHESIS")
    print("-"*60)
    print(results['synthesis'][:500] + "...\n")
    
    print("\n" + "="*60)
    print("✅ Analysis complete! Check the full output for details.")
    print("="*60)


if __name__ == "__main__":
    main()

