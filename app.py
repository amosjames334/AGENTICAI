"""Streamlit UI for Research Agent System with Session Management"""
import streamlit as st
import os
import queue
import threading
from pathlib import Path
from dotenv import load_dotenv
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ingestion.arxiv_loader import ArxivLoader
from ingestion.document_processor import DocumentProcessor
from agents.research_graph import ResearchWorkflow, InteractiveResearchWorkflow
from utils.session_manager import SessionManager

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Research Agent System",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .agent-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border-left: 5px solid #1f77b4;
    }
    .agent-name {
        font-size: 1.2em;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 10px;
    }
    .agent-role {
        font-size: 0.9em;
        color: #666;
        font-style: italic;
        margin-bottom: 10px;
    }
    .session-card {
        background-color: #e8f4f8;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border-left: 5px solid #2e86ab;
    }
    .stProgress > div > div > div > div {
        background-color: #1f77b4;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables"""
    if 'papers' not in st.session_state:
        st.session_state.papers = []
    if 'workflow_results' not in st.session_state:
        st.session_state.workflow_results = None
    if 'current_session' not in st.session_state:
        st.session_state.current_session = None
    if 'session_manager' not in st.session_state:
        st.session_state.session_manager = None
    if 'arxiv_loader' not in st.session_state:
        st.session_state.arxiv_loader = None
    if 'doc_processor' not in st.session_state:
        st.session_state.doc_processor = None


def display_agent_response(agent_name, agent_role, message, responding_to=None):
    """Display an agent's response in a formatted card"""
    role_lower = (agent_role or "").lower()

    # Tool results: collapsed so they don't dominate the page
    if "tool result" in role_lower:
        with st.expander(f"📎 {agent_name} — Tool Result", expanded=False):
            st.markdown(message)
        return

    # Tool calls: compact, highlight which tool/MCP is being invoked
    if "tool call" in role_lower:
        st.markdown(f"🔧 **{agent_role}**")
        st.code(message, language="markdown")
        return

    # Final synthesis: prominent green-accented card
    if "final synthesis" in role_lower:
        st.markdown(f"""
        <div class="agent-card" style="border-left-color: #28a745;">
            <div class="agent-name">🤖 {agent_name}</div>
            <div class="agent-role" style="color: #28a745;">✅ {agent_role}</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(message)
        st.markdown("---")
        return

    # Thinking / default
    if responding_to:
        st.markdown(f"💬 *{agent_name} responds to {responding_to}:*")

    st.markdown(f"""
    <div class="agent-card">
        <div class="agent-name">🤖 {agent_name}</div>
        <div class="agent-role">🧠 {agent_role}</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(message)
    st.markdown("---")


def display_run_stats(stats):
    """Render end-of-run statistics: duration, tool usage, models."""
    if not stats:
        return

    st.markdown("#### 📈 Run Statistics")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("⏱️ Duration", f"{stats.get('duration_seconds', 0)}s")
    with col2:
        st.metric("🔧 Tool Calls", stats.get("total_tool_calls", 0))
    with col3:
        st.metric("🧠 Reasoning Steps", stats.get("thinking_steps", 0))

    tool_counts = stats.get("tool_counts", {})
    if tool_counts:
        st.markdown("**Tools used:**")
        for name, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
            st.markdown(f"- `{name}` — called **{count}** time(s)")
    else:
        st.markdown("*No tools were called during this run.*")

    brave = stats.get("brave_enabled", False)
    st.markdown(
        f"**Brave Search (MCP):** {'🟢 enabled' if brave else '⚪ disabled'}  \n"
        f"**Reasoning model:** `{stats.get('light_model', 'N/A')}`  \n"
        f"**Synthesis model:** `{stats.get('heavy_model', 'N/A')}`"
    )


def main():
    """Main application"""
    initialize_session_state()
    
    st.title("🔬 Research Agent System")
    st.markdown("### *AI Agents with Advanced Document Processing*")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Key check
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            st.error("⚠️ Anthropic API key not found!")
            st.info("Please set ANTHROPIC_API_KEY in your .env file")
            st.stop()
        else:
            st.success("✅ API Key configured")

        # Brave Search (MCP) status
        if os.getenv("BRAVE_API_KEY"):
            st.success("✅ Brave Search enabled")
        else:
            st.info("ℹ️ Brave Search disabled (set BRAVE_API_KEY to enable web search)")
        
        st.markdown("---")
        
        # Session Management Section
        st.header("📂 Research Sessions")
        
        # List existing sessions
        available_sessions = SessionManager.list_sessions()
        
        session_options = ["Create New Session..."] + [
            f"{s['session_id'][:25]}... - {s.get('topic', 'Unknown')[:30]}"
            for s in available_sessions
        ]
        
        selected_option = st.selectbox(
            "Select or Create Session",
            options=session_options,
            key="session_selector"
        )
        
        if selected_option == "Create New Session...":
            st.session_state.current_session = None
            st.session_state.session_manager = None
            st.session_state.papers = []
            st.session_state.workflow_results = None
        else:
            # Extract session ID from selection
            session_idx = session_options.index(selected_option) - 1
            if session_idx >= 0:
                session_id = available_sessions[session_idx]['session_id']
                
                # Reload whenever the session changed OR when papers are
                # empty (happens after a cold restart — session_state is
                # wiped but the selectbox keeps its previous value).
                needs_load = (
                    st.session_state.current_session != session_id
                    or not st.session_state.papers
                )
                
                if needs_load:
                    try:
                        st.session_state.session_manager = SessionManager.load_session(session_id)
                        st.session_state.current_session = session_id
                        
                        # Reinitialize components with session
                        st.session_state.arxiv_loader = ArxivLoader(
                            session_manager=st.session_state.session_manager
                        )
                        st.session_state.doc_processor = DocumentProcessor(
                            vector_store_dir=st.session_state.session_manager.get_vector_store_dir()
                        )
                        
                        # Load papers from manifest
                        import json
                        manifest_path = Path(st.session_state.session_manager.get_papers_dir()) / "manifest.json"
                        if manifest_path.exists():
                            with open(manifest_path) as f:
                                st.session_state.papers = json.load(f)
                        else:
                            st.session_state.papers = []

                        # Restore this session's previous run (if any)
                        st.session_state.workflow_results = \
                            st.session_state.session_manager.load_results()

                        st.success(f"✅ Loaded session ({len(st.session_state.papers)} papers)")
                        
                    except Exception as e:
                        st.error(f"Error loading session: {e}")
                        st.session_state.papers = []
                        st.session_state.workflow_results = None
        
        # Display current session info
        if st.session_state.session_manager:
            meta = st.session_state.session_manager.metadata
            st.markdown("---")
            st.markdown("**Current Session:**")
            st.info(f"""
            **Topic:** {meta.get('topic', 'Unknown')}
            
            **Stats:**
            - Papers: {meta.get('papers_count', 0)}
            - Chunks: {meta.get('chunks_count', 0)}
            """)
            
            if st.button("🗑️ Delete Session", key="delete_session_btn"):
                st.session_state.session_manager.delete_session()
                st.session_state.current_session = None
                st.session_state.session_manager = None
                st.session_state.papers = []
                st.session_state.workflow_results = None
                st.rerun()
        
        st.markdown("---")
        
        # Model selection (for the final synthesis pass; the reasoning loop
        # always uses Haiku to stay within rate limits)
        model_option = st.selectbox(
            "Synthesis Model",
            [
                "claude-sonnet-4-5-20250929",
                "claude-haiku-4-5-20251001",
            ],
            index=0,
            help="Haiku handles the reasoning loop. This model produces the "
                 "final synthesis. Use Haiku everywhere to stay under rate limits."
        )
        
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.1
        )
        
        workflow_type = st.radio(
            "Workflow Type",
            ["Standard", "Interactive (with refinement)"],
            index=0
        )
    
    # Main content area
    tab1, tab2, tab3, tab4 = st.tabs([
        "📝 New Research", 
        "📚 PDF Processing", 
        "🤖 Agent Analysis", 
        "📊 Results"
    ])
    
    with tab1:
        st.header("Start New Research or Continue Session")
        
        if st.session_state.current_session:
            st.success(f"✅ Using session: {st.session_state.session_manager.metadata.get('topic', 'Unknown')}")
        else:
            st.info("Create a new research session or select an existing one from the sidebar")
        
        # Research query input
        col1, col2 = st.columns([3, 1])
        
        with col1:
            query = st.text_input(
                "Enter your research question/topic",
                placeholder="e.g., Quantum computing for drug discovery",
                help="Enter a specific research topic or question",
                key="research_query"
            )
        
        with col2:
            max_papers = st.number_input(
                "Papers",
                min_value=2,
                max_value=20,
                value=10,
                step=1,
                key="max_papers_input"
            )
        
        search_clicked = st.button("🔍 Search Papers", type="primary", use_container_width=True)
        
        # Search for papers
        if search_clicked and query:
            with st.spinner("Searching arXiv..."):
                try:
                    # Create new session if needed
                    if not st.session_state.session_manager:
                        st.session_state.session_manager = SessionManager()
                        session_id = st.session_state.session_manager.create_session(query)
                        st.session_state.current_session = session_id
                        st.session_state.arxiv_loader = ArxivLoader(
                            session_manager=st.session_state.session_manager
                        )
                        st.session_state.doc_processor = DocumentProcessor(
                            vector_store_dir=st.session_state.session_manager.get_vector_store_dir()
                        )
                        st.success(f"✅ Created new session: {session_id}")
                    
                    # Search papers
                    papers = st.session_state.arxiv_loader.search_papers(
                        query=query,
                        max_results=max_papers
                    )
                    st.session_state.papers = papers
                    st.success(f"✅ Found {len(papers)} papers!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error searching papers: {e}")
        
        # Display found papers
        if st.session_state.papers:
            st.subheader(f"📚 Found Papers ({len(st.session_state.papers)})")
            
            for i, paper in enumerate(st.session_state.papers[:5]):
                with st.expander(f"{i+1}. {paper['title']}"):
                    st.markdown(f"**Authors:** {', '.join(paper['authors'][:3])}{'...' if len(paper['authors']) > 3 else ''}")
                    st.markdown(f"**Published:** {paper['published']}")
                    st.markdown(f"**Category:** {paper['primary_category']}")
                    st.markdown(f"**Abstract:** {paper['abstract'][:300]}...")
                    st.markdown(f"[View on arXiv]({paper['pdf_url']})")
            
            if len(st.session_state.papers) > 5:
                st.info(f"Showing 5 of {len(st.session_state.papers)} papers. All will be processed.")
    
    with tab2:
        st.header("📚 PDF Processing & Vector Store")
        
        if not st.session_state.session_manager:
            st.warning("⚠️ No active session. Create one in the 'New Research' tab.")
        else:
            # Vector store status
            col1, col2 = st.columns(2)
            with col1:
                if st.session_state.doc_processor and st.session_state.doc_processor.store_exists():
                    stats = st.session_state.doc_processor.get_store_stats()
                    st.success(f"✅ Vector Store Ready")
                    st.info(f"Chunks: {stats.get('num_chunks', 0)}")
                else:
                    st.warning("⚠️ Vector Store Not Built")
            
            with col2:
                if st.button("🔄 Refresh Status"):
                    st.rerun()
            
            st.markdown("---")
            
            # PDF Processing Section
            st.subheader("📥 Download PDFs & Build Vector Store")
            
            if not st.session_state.papers:
                st.info("👈 First, search for papers in the 'New Research' tab")
            else:
                st.success(f"Found {len(st.session_state.papers)} papers ready to process")
                
                # Download PDFs button
                if st.button("📥 Download PDFs", type="primary", use_container_width=True):
                    with st.spinner("Downloading PDFs..."):
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        try:
                            enriched_papers = []
                            for idx, paper in enumerate(st.session_state.papers):
                                status_text.text(f"Downloading {idx+1}/{len(st.session_state.papers)}: {paper['title'][:40]}...")
                                progress_bar.progress((idx + 1) / len(st.session_state.papers))
                                
                                # Download individual paper
                                pdf_path = st.session_state.arxiv_loader.download_paper(
                                    paper.get('arxiv_id', ''),
                                    paper.get('title', '')
                                )
                                paper_copy = dict(paper)
                                paper_copy['pdf_path'] = str(pdf_path) if pdf_path else None
                                enriched_papers.append(paper_copy)
                            
                            st.session_state.papers = enriched_papers
                            downloaded = sum(1 for p in enriched_papers if p.get('pdf_path'))
                            
                            # Update session
                            st.session_state.session_manager.update_metadata(
                                papers_count=len(enriched_papers),
                                papers_downloaded=downloaded
                            )
                            
                            st.success(f"✅ Downloaded {downloaded} of {len(enriched_papers)} PDFs")
                            
                        except Exception as e:
                            st.error(f"Error downloading PDFs: {e}")
                
                st.markdown("---")
                
                # Build vector store
                st.subheader("🔧 Build Enhanced Vector Store")
                
                papers_with_pdfs = [p for p in st.session_state.papers if p.get('pdf_path')]
                
                if not papers_with_pdfs:
                    st.info("📥 Download PDFs first")
                else:
                    st.success(f"Ready to process {len(papers_with_pdfs)} PDFs")
                    
                    st.markdown("""
                    **Enhanced Processing Pipeline:**
                    1. ✨ Advanced text cleaning & normalization
                    2. 🔪 Semantic chunking with overlap
                    3. 📊 Comprehensive metadata enrichment
                    4. 🧠 384-dim embedding generation
                    5. ⚡ Fast FAISS indexing
                    """)
                    
                    if st.button("🔧 Build Vector Store", type="primary", use_container_width=True):
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        try:
                            def progress_callback(current, total, status):
                                progress_bar.progress(current / total)
                                status_text.text(status)
                            
                            n_chunks, embed_dim = st.session_state.doc_processor.build_store_from_pdfs(
                                papers_with_pdfs,
                                progress_callback=progress_callback
                            )
                            
                            # Update session
                            st.session_state.session_manager.update_metadata(
                                chunks_count=n_chunks,
                                embedding_dim=embed_dim
                            )
                            
                            st.success(f"✅ Vector store built!")
                            st.info(f"📊 {n_chunks} chunks with {embed_dim}-dimensional embeddings")
                            st.balloons()
                            
                        except Exception as e:
                            st.error(f"Error building vector store: {e}")
                            st.exception(e)
            
            st.markdown("---")
            
            # Query vector store
            st.subheader("🔍 Query Vector Store")
            
            if not st.session_state.doc_processor or not st.session_state.doc_processor.store_exists():
                st.info("Build the vector store first")
            else:
                query_text = st.text_input(
                    "Enter your query",
                    placeholder="e.g., What are the main findings about...",
                    key="vector_query"
                )
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    num_results = st.slider("Results", 1, 20, 5)
                with col2:
                    search_btn = st.button("🔍 Search")
                
                if search_btn and query_text:
                    with st.spinner("Searching..."):
                        try:
                            hits = st.session_state.doc_processor.query(query_text, k=num_results)
                            st.success(f"Found {len(hits)} results")
                            
                            for i, hit in enumerate(hits):
                                with st.expander(f"Result {i+1} - Score: {hit['score']:.3f}"):
                                    st.markdown(f"**Paper:** {hit['meta']['paper_title']}")
                                    st.markdown(f"**Position:** {hit['meta']['position']:.1%} through paper")
                                    st.markdown(f"**Word Count:** {hit['meta']['word_count']}")
                                    if hit['meta'].get('has_equations'):
                                        st.badge("Has Equations", icon="🔢")
                                    if hit['meta'].get('has_citations'):
                                        st.badge("Has Citations", icon="📚")
                                    st.markdown("---")
                                    st.markdown(hit['text'])
                        except Exception as e:
                            st.error(f"Error: {e}")
    
    with tab3:
        st.header("🤖 Run Agent Analysis")

        streamed_this_run = False

        if not st.session_state.session_manager:
            st.warning("⚠️ No active session")
        elif not st.session_state.papers:
            st.warning("⚠️ No papers loaded")
        else:
            st.success(f"Ready to analyze {len(st.session_state.papers)} papers")

            has_previous_run = bool(st.session_state.workflow_results)
            if has_previous_run:
                run_at = st.session_state.workflow_results.get("run_at", "")
                when = f" (from {run_at[:19].replace('T', ' ')})" if run_at else ""
                st.info(f"💡 A previous run exists for this session{when} — "
                        f"shown below. Re-run to refresh it.")
                button_label = "🔁 Re-run Agent Analysis"
            else:
                button_label = "🚀 Start Agent Analysis"

            if st.button(button_label, type="primary", use_container_width=True):
                if workflow_type == "Interactive (with refinement)":
                    workflow = InteractiveResearchWorkflow(
                        model=model_option, temperature=temperature
                    )
                else:
                    workflow = ResearchWorkflow(
                        model=model_option, temperature=temperature
                    )

                query = st.session_state.session_manager.metadata.get('topic', 'Research Analysis')
                vector_store_dir = st.session_state.session_manager.get_vector_store_dir()
                # Capture session_state values in the main thread; the worker
                # thread has no Streamlit context and cannot read st.session_state.
                papers_for_run = st.session_state.papers

                st.markdown("---")
                st.subheader("📊 Agent Reasoning Flow (live)")

                # Bridge: worker thread pushes events; main thread renders them.
                event_q: "queue.Queue" = queue.Queue()

                def _worker():
                    try:
                        workflow.run_streaming(
                            query,
                            papers_for_run,
                            vector_store_dir=vector_store_dir,
                            on_event=event_q.put,
                        )
                    except Exception as e:  # surfaced to UI via the queue
                        event_q.put({"type": "error", "message": str(e)})
                    finally:
                        event_q.put({"type": "__end__"})

                thread = threading.Thread(target=_worker, daemon=True)
                thread.start()
                streamed_this_run = True

                live_area = st.container()
                status = st.status("🤖 Agent is reasoning...", expanded=True)
                final_results = None
                run_error = None

                while True:
                    ev = event_q.get()
                    etype = ev.get("type")

                    if etype == "__end__":
                        break
                    elif etype == "phase":
                        status.update(label=f"🤖 {ev.get('label', 'Working...')}")
                        with live_area:
                            tools = ev.get("tools")
                            if tools:
                                brave = "🟢 on" if ev.get("brave_enabled") else "⚪ off"
                                st.caption(
                                    f"Tools available: {', '.join(f'`{t}`' for t in tools)} "
                                    f"· Brave MCP: {brave}"
                                )
                    elif etype == "thinking":
                        with live_area:
                            display_agent_response(
                                "Reasoning Agent",
                                f"Thinking (step {ev.get('step')})",
                                ev.get("text", ""),
                            )
                    elif etype == "tool_call":
                        with live_area:
                            display_agent_response(
                                "Reasoning Agent",
                                "Tool Call",
                                f"Calling `{ev.get('name')}` with: {ev.get('args')}",
                            )
                    elif etype == "tool_result":
                        with live_area:
                            display_agent_response(
                                ev.get("name", "tool"),
                                "Tool Result",
                                ev.get("result", ""),
                                responding_to="Reasoning Agent",
                            )
                    elif etype == "synthesis":
                        with live_area:
                            display_agent_response(
                                "Reasoning Agent",
                                "Final Synthesis",
                                ev.get("text", ""),
                            )
                    elif etype == "final":
                        final_results = ev.get("results")
                    elif etype == "error":
                        run_error = ev.get("message")

                thread.join(timeout=1)

                if run_error:
                    status.update(label="❌ Analysis failed", state="error")
                    st.error(f"Error: {run_error}")
                elif final_results:
                    st.session_state.workflow_results = final_results
                    # Persist this run so it can be viewed after switching/restart
                    st.session_state.session_manager.save_results(final_results)
                    status.update(label="✅ Analysis complete!", state="complete")
                    with live_area:
                        display_run_stats(final_results.get("stats"))
                    st.balloons()

        # Persisted replay (after reruns / tab switches) — skip right after a
        # live run to avoid rendering the conversation twice on the same pass.
        if st.session_state.workflow_results and not streamed_this_run:
            st.markdown("---")
            st.subheader("📊 Agent Reasoning Flow")

            results = st.session_state.workflow_results
            conversation = results.get("conversation_history", [])

            if not conversation:
                st.info("No reasoning steps were captured for this run.")
            else:
                for step in conversation:
                    display_agent_response(
                        step["agent"],
                        step["role"],
                        step["message"],
                        step.get("responding_to", None),
                    )

            display_run_stats(results.get("stats"))
    
    with tab4:
        st.header("📊 Research Results")
        
        if st.session_state.workflow_results:
            results = st.session_state.workflow_results
            
            # Collective Insight Report - Highlighted at the top
            insight_report = results.get("insight_report", "")
            if insight_report:
                st.markdown("### 🎯 Collective Insight Report")
                st.info("**Meta-Analysis**: This report distills what all agents collectively revealed")
                st.markdown(insight_report)
                st.markdown("---")
            
            # Final synthesis
            st.subheader("📝 Synthesis")
            st.markdown(results.get("synthesis", "No synthesis available"))
            
            st.markdown("---")
            
            # Follow-up questions
            st.subheader("❓ Follow-up Research Questions")
            questions = results.get("follow_up_questions", [])
            if questions:
                for q in questions:
                    st.markdown(f"- {q}")
            
            st.markdown("---")
            
            # Download report
            col1, col2 = st.columns(2)
            
            with col1:
                # Build conversation section from conversation_history
                conversation_section = ""
                conversation = results.get('conversation_history', [])
                if conversation:
                    conversation_section = "\n## Agent Conversation\n\n"
                    for msg in conversation:
                        responding_to = msg.get('responding_to', None)
                        if responding_to:
                            conversation_section += f"### {msg['agent']} (responding to {responding_to}):\n\n"
                        else:
                            conversation_section += f"### {msg['agent']}:\n\n"
                        conversation_section += f"{msg['message']}\n\n---\n\n"
                
                # Build insight section
                insight_section = ""
                insight_report = results.get('insight_report', '')
                if insight_report:
                    insight_section = f"\n## 🎯 Collective Insight Report\n\n{insight_report}\n\n---\n"
                
                report = f"""# Research Analysis Report

## Query
{results.get('query', 'N/A')}

## Session
{st.session_state.session_manager.metadata.get('topic', 'N/A') if st.session_state.session_manager else 'N/A'}

{insight_section}

{conversation_section}

## Follow-up Questions
{chr(10).join(['- ' + q for q in results.get('follow_up_questions', [])])}

## Synthesis
{results.get('synthesis', 'N/A')}

---
Generated by Research Agent System
Session: {st.session_state.current_session or 'N/A'}
"""
                st.download_button(
                    label="📥 Download Report",
                    data=report,
                    file_name="research_report.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            
            with col2:
                if st.button("🔄 Start New Analysis", use_container_width=True):
                    st.session_state.workflow_results = None
                    st.rerun()
        else:
            st.info("👈 Run agent analysis in the 'Agent Analysis' tab")


if __name__ == "__main__":
    main()
