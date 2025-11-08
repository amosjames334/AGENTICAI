"""Command-line interface for Research Agent System"""
import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ingestion.arxiv_loader import ArxivLoader
from agents.research_graph import ResearchWorkflow
from utils.config import Config
from utils.logger import setup_logger

load_dotenv()
logger = setup_logger()


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Research Agent System - AI-powered research analysis"
    )
    
    parser.add_argument(
        "query",
        type=str,
        help="Research query or topic"
    )
    
    parser.add_argument(
        "--max-papers",
        type=int,
        default=10,
        help="Maximum number of papers to analyze (default: 10)"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4-turbo-preview",
        choices=["gpt-4-turbo-preview", "gpt-4", "gpt-3.5-turbo"],
        help="OpenAI model to use (default: gpt-4-turbo-preview)"
    )
    
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Model temperature (0.0-1.0, default: 0.7)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file for the report (default: print to console)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Validate config
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please set OPENAI_API_KEY in your .env file")
        sys.exit(1)
    
    # Set log level
    if args.verbose:
        logger.setLevel("DEBUG")
    
    logger.info("="*60)
    logger.info("Research Agent System - CLI Mode")
    logger.info("="*60)
    logger.info(f"Query: {args.query}")
    logger.info(f"Model: {args.model}")
    logger.info(f"Max papers: {args.max_papers}")
    logger.info("="*60)
    
    try:
        # Step 1: Search for papers
        logger.info("\n[1/3] Searching arXiv for papers...")
        loader = ArxivLoader()
        papers = loader.search_papers(args.query, max_results=args.max_papers)
        logger.info(f"Found {len(papers)} papers")
        
        if not papers:
            logger.warning("No papers found for this query")
            sys.exit(0)
        
        # Display found papers
        logger.info("\nFound papers:")
        for i, paper in enumerate(papers[:5]):
            logger.info(f"  {i+1}. {paper['title']}")
        if len(papers) > 5:
            logger.info(f"  ... and {len(papers) - 5} more")
        
        # Step 2: Run agent analysis
        logger.info("\n[2/3] Running multi-agent analysis...")
        workflow = ResearchWorkflow(
            model=args.model,
            temperature=args.temperature
        )
        
        results = workflow.run(args.query, papers)
        
        # Step 3: Display results
        logger.info("\n[3/3] Analysis complete!")
        logger.info("="*60)
        
        # Format output
        report = format_report(results)
        
        # Output results
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report)
            logger.info(f"\n✅ Report saved to: {args.output}")
        else:
            print("\n" + report)
        
        logger.info("\n" + "="*60)
        logger.info("✨ Research analysis complete!")
        logger.info("="*60)
        
    except KeyboardInterrupt:
        logger.info("\n\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n❌ Error during analysis: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def format_report(results: dict) -> str:
    """Format results into a readable report"""
    report = []
    
    report.append("="*80)
    report.append("RESEARCH ANALYSIS REPORT")
    report.append("="*80)
    
    report.append(f"\n📋 QUERY\n{'-'*80}")
    report.append(results.get('query', 'N/A'))
    
    report.append(f"\n\n🔍 RESEARCH SUMMARY\n{'-'*80}")
    report.append(results.get('research_summary', 'N/A'))
    
    report.append(f"\n\n🎯 CRITICAL ANALYSIS\n{'-'*80}")
    report.append(results.get('critique', 'N/A'))
    
    report.append(f"\n\n❓ FOLLOW-UP QUESTIONS\n{'-'*80}")
    questions = results.get('follow_up_questions', [])
    if questions:
        for q in questions:
            report.append(f"• {q}")
    else:
        report.append("No follow-up questions generated")
    
    report.append(f"\n\n🧩 FINAL SYNTHESIS\n{'-'*80}")
    report.append(results.get('synthesis', 'N/A'))
    
    report.append("\n" + "="*80)
    report.append("Generated by Research Agent System")
    report.append("="*80)
    
    return "\n".join(report)


if __name__ == "__main__":
    main()

