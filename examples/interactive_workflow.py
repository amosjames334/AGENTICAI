"""Example using interactive workflow with refinement"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
from ingestion.arxiv_loader import ArxivLoader
from agents.research_graph import InteractiveResearchWorkflow

load_dotenv()


def main():
    """Run an interactive research analysis with refinement"""
    
    query = "Quantum computing applications in drug discovery"
    print(f"Research Query: {query}")
    print("="*60)
    
    # Search for papers
    print("\nSearching for papers...")
    loader = ArxivLoader()
    papers = loader.search_papers(query, max_results=8)
    print(f"Found {len(papers)} papers")
    
    # Run interactive workflow (includes refinement)
    print("\nRunning interactive multi-agent analysis...")
    print("This workflow includes iterative refinement...\n")
    
    workflow = InteractiveResearchWorkflow(
        model="gpt-4-turbo-preview",
        temperature=0.7
    )
    
    results = workflow.run(query, papers)
    
    # Display conversation flow
    print("\n📊 AGENT CONVERSATION FLOW")
    print("="*60)
    
    for step in results['conversation_history']:
        print(f"\n🤖 {step['agent']} ({step['role']})")
        print("-"*60)
        print(step['message'][:300] + "...\n")
    
    # Display final synthesis
    print("\n🎯 FINAL SYNTHESIS")
    print("="*60)
    print(results['synthesis'])
    
    print("\n" + "="*60)
    print(f"✅ Interactive analysis complete!")
    print(f"   Agents participated: {len(results['conversation_history'])}")
    print(f"   Refinement iterations: {results['iteration']}")
    print("="*60)


if __name__ == "__main__":
    main()

