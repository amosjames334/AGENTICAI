"""Command-line interface with session management"""
import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv
from tabulate import tabulate

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ingestion.arxiv_loader import ArxivLoader
from ingestion.document_processor import DocumentProcessor
from agents.research_graph import ResearchWorkflow
from utils.config import Config
from utils.logger import setup_logger
from utils.session_manager import SessionManager

load_dotenv()
logger = setup_logger()


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Research Agent System - AI-powered research with session management"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # New Session command
    session_parser = subparsers.add_parser('new', help='Create new research session')
    session_parser.add_argument("topic", type=str, help="Research topic")
    session_parser.add_argument("--description", type=str, default="", help="Session description")
    session_parser.add_argument("--max-papers", type=int, default=10, help="Number of papers")
    session_parser.add_argument("--verbose", action="store_true")
    
    # List Sessions command
    list_parser = subparsers.add_parser('list', help='List all research sessions')
    list_parser.add_argument("--verbose", action="store_true")
    
    # Load Session command
    load_parser = subparsers.add_parser('load', help='Load and continue existing session')
    load_parser.add_argument("session_id", type=str, help="Session ID to load")
    load_parser.add_argument("--info", action="store_true", help="Show session info only")
    
    # Delete Session command
    delete_parser = subparsers.add_parser('delete', help='Delete a research session')
    delete_parser.add_argument("session_id", type=str, help="Session ID to delete")
    delete_parser.add_argument("--force", action="store_true", help="Skip confirmation")
    
    # Ingest command (now session-aware)
    ingest_parser = subparsers.add_parser('ingest', help='Download PDFs and build vector store')
    ingest_parser.add_argument("topic", type=str, help="Search topic")
    ingest_parser.add_argument("--session-id", type=str, help="Use existing session")
    ingest_parser.add_argument("--max-papers", type=int, default=10)
    ingest_parser.add_argument("--verbose", action="store_true")
    
    # Query command (now session-aware)
    query_parser = subparsers.add_parser('query', help='Query the vector store')
    query_parser.add_argument("query", type=str, help="Query text")
    query_parser.add_argument("--session-id", type=str, required=True, help="Session ID")
    query_parser.add_argument("--k", type=int, default=5)
    query_parser.add_argument("--verbose", action="store_true")
    
    # Research command (now session-aware)
    research_parser = subparsers.add_parser('research', help='Run full agent analysis')
    research_parser.add_argument("topic", type=str, help="Research topic")
    research_parser.add_argument("--session-id", type=str, help="Use existing session")
    research_parser.add_argument("--max-papers", type=int, default=10)
    research_parser.add_argument("--model", type=str, default="gpt-4-turbo-preview")
    research_parser.add_argument("--temperature", type=float, default=0.7)
    research_parser.add_argument("--output", type=str, help="Output file")
    research_parser.add_argument("--verbose", action="store_true")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Route to handlers
    if args.command == 'new':
        cmd_new_session(args)
    elif args.command == 'list':
        cmd_list_sessions(args)
    elif args.command == 'load':
        cmd_load_session(args)
    elif args.command == 'delete':
        cmd_delete_session(args)
    elif args.command == 'ingest':
        cmd_ingest(args)
    elif args.command == 'query':
        cmd_query(args)
    elif args.command == 'research':
        cmd_research(args)


def cmd_new_session(args):
    """Create new research session and ingest papers"""
    if args.verbose:
        logger.setLevel("DEBUG")
    
    logger.info("="*60)
    logger.info("Creating New Research Session")
    logger.info("="*60)
    logger.info(f"Topic: {args.topic}")
    logger.info(f"Max papers: {args.max_papers}")
    logger.info("="*60)
    
    try:
        # Create session
        session = SessionManager()
        session_id = session.create_session(args.topic, args.description)
        logger.info(f"\n✅ Session created: {session_id}")
        logger.info(f"   Location: {session.session_dir}")
        
        # Download and process papers
        logger.info(f"\n[1/3] Searching arXiv for '{args.topic}'...")
        loader = ArxivLoader(session_manager=session)
        papers = loader.search_papers(args.topic, max_results=args.max_papers)
        logger.info(f"Found {len(papers)} papers")
        
        if not papers:
            logger.warning("No papers found")
            sys.exit(0)
        
        # Download PDFs
        logger.info(f"\n[2/3] Downloading PDFs...")
        enriched_papers = loader.download_selected(papers)
        downloaded = sum(1 for p in enriched_papers if p.get('pdf_path'))
        logger.info(f"✅ Downloaded {downloaded} of {len(enriched_papers)} PDFs")
        
        # Build vector store
        if downloaded > 0:
            logger.info(f"\n[3/3] Building vector store with enhanced pipeline...")
            processor = DocumentProcessor(
                vector_store_dir=session.get_vector_store_dir(),
                chunk_size=1000,
                chunk_overlap=200
            )
            
            def progress_callback(current, total, status):
                logger.info(f"  [{current}/{total}] {status}")
            
            n_chunks, embed_dim = processor.build_store_from_pdfs(
                enriched_papers,
                progress_callback=progress_callback
            )
            
            # Update session metadata
            session.update_metadata(chunks_count=n_chunks, embedding_dim=embed_dim)
            
            logger.info("\n" + "="*60)
            logger.info(f"✅ Session ready: {session_id}")
            logger.info(f"   Papers: {downloaded}")
            logger.info(f"   Chunks: {n_chunks}")
            logger.info(f"   Embeddings: {embed_dim}-dimensional")
            logger.info(f"\nQuery this session:")
            logger.info(f"  python cli.py query 'your question' --session-id {session_id}")
            logger.info("="*60)
        else:
            logger.error("No PDFs downloaded successfully")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("\n\nCancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def cmd_list_sessions(args):
    """List all available sessions"""
    sessions = SessionManager.list_sessions()
    
    if not sessions:
        print("\nNo sessions found.")
        print("Create one with: python cli.py new 'your topic'")
        return
    
    print(f"\n📚 Found {len(sessions)} research session(s):\n")
    
    table_data = []
    for s in sessions:
        table_data.append([
            s['session_id'][:30] + '...' if len(s['session_id']) > 30 else s['session_id'],
            s.get('topic', 'Unknown')[:40],
            s.get('papers_count', 0),
            s.get('chunks_count', 0),
            s.get('created_at', '')[:10]
        ])
    
    print(tabulate(
        table_data,
        headers=['Session ID', 'Topic', 'Papers', 'Chunks', 'Created'],
        tablefmt='simple'
    ))
    
    print(f"\nLoad a session:")
    print(f"  python cli.py load <session_id> --info")


def cmd_load_session(args):
    """Load and display session info"""
    try:
        session = SessionManager.load_session(args.session_id)
        info = session.get_session_info()
        
        print("\n" + "="*60)
        print(f"Session: {session.session_id}")
        print("="*60)
        print(f"Topic: {info['metadata'].get('topic', 'Unknown')}")
        print(f"Description: {info['metadata'].get('description', 'N/A')}")
        print(f"Created: {info['metadata'].get('created_at', 'Unknown')}")
        print(f"Updated: {info['metadata'].get('updated_at', 'Unknown')}")
        print(f"\nStatistics:")
        print(f"  Papers: {info['metadata'].get('papers_count', 0)}")
        print(f"  Chunks: {info['metadata'].get('chunks_count', 0)}")
        print(f"  Embedding dim: {info['metadata'].get('embedding_dim', 'N/A')}")
        print(f"\nDirectories:")
        print(f"  Papers: {info['papers_dir']}")
        print(f"  Vector store: {info['vector_store_dir']}")
        print(f"  Cache: {info['cache_dir']}")
        print("="*60)
        
        if not args.info:
            print(f"\nQuery this session:")
            print(f"  python cli.py query 'your question' --session-id {args.session_id}")
        
    except Exception as e:
        logger.error(f"Error loading session: {e}")
        sys.exit(1)


def cmd_delete_session(args):
    """Delete a session"""
    try:
        session = SessionManager.load_session(args.session_id)
        info = session.get_session_info()
        
        if not args.force:
            print(f"\n⚠️  Delete session '{info['metadata'].get('topic', 'Unknown')}'?")
            print(f"   Session ID: {args.session_id}")
            print(f"   This will delete {info['metadata'].get('papers_count', 0)} papers and all data.")
            response = input("\nType 'yes' to confirm: ")
            if response.lower() != 'yes':
                print("Cancelled.")
                return
        
        session.delete_session()
        print(f"✅ Session {args.session_id} deleted.")
        
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        sys.exit(1)


def cmd_ingest(args):
    """Ingest papers (create or use existing session)"""
    if args.verbose:
        logger.setLevel("DEBUG")
    
    try:
        # Use existing session or create new
        if args.session_id:
            session = SessionManager.load_session(args.session_id)
            logger.info(f"Using existing session: {args.session_id}")
        else:
            session = SessionManager()
            session_id = session.create_session(args.topic)
            logger.info(f"Created new session: {session_id}")
        
        # Download papers
        logger.info(f"\nSearching arXiv for '{args.topic}'...")
        loader = ArxivLoader(session_manager=session)
        papers = loader.search_papers(args.topic, max_results=args.max_papers)
        
        if not papers:
            logger.warning("No papers found")
            return
        
        enriched_papers = loader.download_selected(papers)
        downloaded = sum(1 for p in enriched_papers if p.get('pdf_path'))
        logger.info(f"Downloaded {downloaded} PDFs")
        
        # Build vector store
        if downloaded > 0:
            processor = DocumentProcessor(vector_store_dir=session.get_vector_store_dir())
            n_chunks, embed_dim = processor.build_store_from_pdfs(enriched_papers)
            session.update_metadata(chunks_count=n_chunks)
            logger.info(f"✅ Vector store built: {n_chunks} chunks")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


def cmd_query(args):
    """Query a session's vector store"""
    if args.verbose:
        logger.setLevel("DEBUG")
    
    try:
        session = SessionManager.load_session(args.session_id)
        processor = DocumentProcessor(vector_store_dir=session.get_vector_store_dir())
        
        if not processor.store_exists():
            logger.error("Vector store not found in this session")
            sys.exit(1)
        
        logger.info(f"Querying session: {session.metadata.get('topic', 'Unknown')}")
        hits = processor.query(args.query, k=args.k)
        
        print(f"\n✅ Found {len(hits)} results\n")
        print("="*60)
        
        for i, hit in enumerate(hits):
            print(f"\n[Result {i+1}] Score: {hit['score']:.3f}")
            print(f"Paper: {hit['meta']['paper_title'][:60]}")
            print(f"Position: {hit['meta']['position']:.1%}")
            print("-"*60)
            print(hit['text'][:400] + "..." if len(hit['text']) > 400 else hit['text'])
            print()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


def cmd_research(args):
    """Run full research analysis"""
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    if args.verbose:
        logger.setLevel("DEBUG")
    
    try:
        # Use or create session
        if args.session_id:
            session = SessionManager.load_session(args.session_id)
            logger.info(f"Using session: {args.session_id}")
            # Load papers from manifest
            import json
            manifest_path = Path(session.get_papers_dir()) / "manifest.json"
            with open(manifest_path) as f:
                papers = json.load(f)
        else:
            # Create new session and ingest
            session = SessionManager()
            session_id = session.create_session(args.topic)
            logger.info(f"Created session: {session_id}")
            
            loader = ArxivLoader(session_manager=session)
            papers = loader.search_papers(args.topic, max_results=args.max_papers)
            papers = loader.download_selected(papers)
            
            # Build vector store
            processor = DocumentProcessor(vector_store_dir=session.get_vector_store_dir())
            processor.build_store_from_pdfs(papers)
        
        # Run agent workflow
        logger.info("\nRunning multi-agent analysis...")
        workflow = ResearchWorkflow(model=args.model, temperature=args.temperature)
        results = workflow.run(args.topic, papers)
        
        # Format and output report
        report = format_report(results)
        
        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            Path(args.output).write_text(report)
            logger.info(f"\n✅ Report saved to: {args.output}")
        else:
            print("\n" + report)
        
        logger.info(f"\n✅ Analysis complete for session: {session.session_id}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def format_report(results: dict) -> str:
    """Format results into readable report"""
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
