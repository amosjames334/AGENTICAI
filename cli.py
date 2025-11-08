"""Command-line interface for Research Agent System"""
import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ingestion.arxiv_loader import ArxivLoader
from ingestion.document_processor import DocumentProcessor
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
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Research command (default behavior)
    research_parser = subparsers.add_parser('research', help='Run research analysis')
    research_parser.add_argument(
        "query",
        type=str,
        help="Research query or topic"
    )
    research_parser.add_argument(
        "--max-papers",
        type=int,
        default=10,
        help="Maximum number of papers to analyze (default: 10)"
    )
    research_parser.add_argument(
        "--model",
        type=str,
        default="gpt-4-turbo-preview",
        choices=["gpt-4-turbo-preview", "gpt-4", "gpt-3.5-turbo"],
        help="OpenAI model to use (default: gpt-4-turbo-preview)"
    )
    research_parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Model temperature (0.0-1.0, default: 0.7)"
    )
    research_parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file for the report (default: print to console)"
    )
    research_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    # Ingest command
    ingest_parser = subparsers.add_parser('ingest', help='Download PDFs and build vector store')
    ingest_parser.add_argument(
        "query",
        type=str,
        help="Search query for papers"
    )
    ingest_parser.add_argument(
        "--max-papers",
        type=int,
        default=10,
        help="Maximum number of papers to download (default: 10)"
    )
    ingest_parser.add_argument(
        "--data-dir",
        type=str,
        default="data",
        help="Data directory (default: data)"
    )
    ingest_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    # Query command
    query_parser = subparsers.add_parser('query', help='Query the vector store')
    query_parser.add_argument(
        "query",
        type=str,
        help="Query text"
    )
    query_parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Number of results to return (default: 5)"
    )
    query_parser.add_argument(
        "--data-dir",
        type=str,
        default="data",
        help="Data directory (default: data)"
    )
    query_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # If no command specified, show help
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Route to appropriate command handler
    if args.command == 'research':
        run_research(args)
    elif args.command == 'ingest':
        run_ingest(args)
    elif args.command == 'query':
        run_query(args)


def run_research(args):
    """Run research analysis"""
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


def run_ingest(args):
    """Download PDFs and build vector store"""
    if args.verbose:
        logger.setLevel("DEBUG")
    
    logger.info("="*60)
    logger.info("Research Agent System - Ingest Mode")
    logger.info("="*60)
    logger.info(f"Query: {args.query}")
    logger.info(f"Max papers: {args.max_papers}")
    logger.info(f"Data directory: {args.data_dir}")
    logger.info("="*60)
    
    try:
        # Step 1: Search for papers
        logger.info("\n[1/3] Searching arXiv for papers...")
        loader = ArxivLoader(cache_dir=f"{args.data_dir}/papers")
        papers = loader.search_papers(args.query, max_results=args.max_papers)
        logger.info(f"Found {len(papers)} papers")
        
        if not papers:
            logger.warning("No papers found for this query")
            sys.exit(0)
        
        # Step 2: Download PDFs
        logger.info("\n[2/3] Downloading PDFs...")
        enriched_papers = loader.download_selected(papers)
        downloaded = sum(1 for p in enriched_papers if p.get('pdf_path'))
        logger.info(f"✅ Downloaded {downloaded} of {len(enriched_papers)} PDFs")
        
        # Step 3: Build vector store
        logger.info("\n[3/3] Building vector store...")
        pdf_paths = [p['pdf_path'] for p in enriched_papers if p.get('pdf_path')]
        
        if not pdf_paths:
            logger.error("No PDFs downloaded successfully")
            sys.exit(1)
        
        processor = DocumentProcessor(data_dir=args.data_dir)
        n_chunks, embed_dim = processor.build_store_from_pdfs(pdf_paths)
        
        logger.info("\n" + "="*60)
        logger.info(f"✨ Vector store built successfully!")
        logger.info(f"   Chunks: {n_chunks}")
        logger.info(f"   Embedding dimension: {embed_dim}")
        logger.info(f"   Location: {args.data_dir}/vector_store/")
        logger.info("="*60)
        
    except KeyboardInterrupt:
        logger.info("\n\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n❌ Error during ingestion: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def run_query(args):
    """Query the vector store"""
    if args.verbose:
        logger.setLevel("DEBUG")
    
    logger.info("="*60)
    logger.info("Research Agent System - Query Mode")
    logger.info("="*60)
    logger.info(f"Query: {args.query}")
    logger.info(f"Results: {args.k}")
    logger.info(f"Data directory: {args.data_dir}")
    logger.info("="*60)
    
    try:
        processor = DocumentProcessor(data_dir=args.data_dir)
        
        if not processor.store_exists():
            logger.error("Vector store not found. Run 'ingest' command first.")
            sys.exit(1)
        
        logger.info("\nQuerying vector store...")
        hits = processor.query(args.query, k=args.k)
        
        logger.info(f"\n✅ Found {len(hits)} results")
        logger.info("="*60)
        
        for i, hit in enumerate(hits):
            print(f"\n{'='*60}")
            print(f"Result {i+1} - Score: {hit['score']:.3f}")
            print(f"{'='*60}")
            print(f"Source: {hit['meta']['pdf_path']}")
            print(f"Chunk ID: {hit['meta']['chunk_id']}")
            print(f"\n{hit['text']}\n")
        
        logger.info("="*60)
        
    except KeyboardInterrupt:
        logger.info("\n\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n❌ Error during query: {e}")
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

