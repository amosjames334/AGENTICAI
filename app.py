"""Streamlit UI for Research Agent System"""
import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ingestion.arxiv_loader import ArxivLoader
from ingestion.document_processor import DocumentProcessor
from agents.research_graph import ResearchWorkflow, InteractiveResearchWorkflow

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
    if 'arxiv_loader' not in st.session_state:
        st.session_state.arxiv_loader = ArxivLoader()


def display_agent_response(agent_name, agent_role, message):
    """Display an agent's response in a formatted card"""
    st.markdown(f"""
    <div class="agent-card">
        <div class="agent-name">🤖 {agent_name}</div>
        <div class="agent-role">{agent_role}</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(message)
    st.markdown("---")


def main():
    """Main application"""
    initialize_session_state()
    
    st.title("🔬 Research Agent System")
    st.markdown("### *AI Agents Collaborating for Accelerated Research*")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Key check
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            st.error("⚠️ OpenAI API key not found!")
            st.info("Please set OPENAI_API_KEY in your .env file")
            st.stop()
        else:
            st.success("✅ API Key configured")
        
        st.markdown("---")
        
        # Model selection
        model_option = st.selectbox(
            "Select LLM Model",
            ["gpt-4-turbo-preview", "gpt-4", "gpt-3.5-turbo"],
            index=0
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
        
        st.markdown("---")
        st.markdown("### 📊 System Info")
        st.info("""
        **Active Agents:**
        - 🔍 Researcher
        - 🎯 Critic
        - ❓ Question Generator
        - 🧩 Synthesizer
        """)
    
    # Main content area
    tab1, tab2, tab3 = st.tabs(["📝 Research Query", "🤖 Agent Collaboration", "📊 Results"])
    
    with tab1:
        st.header("Start Your Research")
        
        # Research query input
        query = st.text_input(
            "Enter your research question",
            placeholder="e.g., AI for climate modeling, battery efficiency improvements, quantum computing applications...",
            help="Enter a specific research topic or question"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            max_papers = st.slider(
                "Number of papers to search",
                min_value=5,
                max_value=20,
                value=10,
                step=1
            )
        
        with col2:
            search_clicked = st.button("🔍 Search Papers", type="primary", use_container_width=True)
        
        # Search for papers
        if search_clicked and query:
            with st.spinner("Searching arXiv for relevant papers..."):
                try:
                    papers = st.session_state.arxiv_loader.search_papers(
                        query=query,
                        max_results=max_papers
                    )
                    st.session_state.papers = papers
                    st.success(f"✅ Found {len(papers)} papers!")
                except Exception as e:
                    st.error(f"Error searching papers: {e}")
        
        # Display found papers
        if st.session_state.papers:
            st.subheader(f"📚 Found Papers ({len(st.session_state.papers)})")
            
            for i, paper in enumerate(st.session_state.papers[:5]):  # Show first 5
                with st.expander(f"{i+1}. {paper['title']}"):
                    st.markdown(f"**Authors:** {', '.join(paper['authors'][:3])}{'...' if len(paper['authors']) > 3 else ''}")
                    st.markdown(f"**Published:** {paper['published']}")
                    st.markdown(f"**Category:** {paper['primary_category']}")
                    st.markdown(f"**Abstract:** {paper['abstract'][:300]}...")
                    st.markdown(f"[View on arXiv]({paper['pdf_url']})")
            
            if len(st.session_state.papers) > 5:
                st.info(f"Showing 5 of {len(st.session_state.papers)} papers. All papers will be analyzed.")
            
            st.markdown("---")
            
            # Run analysis button
            if st.button("🚀 Start Agent Analysis", type="primary", use_container_width=True):
                with st.spinner("Agents are collaborating on your research..."):
                    try:
                        # Initialize workflow
                        if workflow_type == "Interactive (with refinement)":
                            workflow = InteractiveResearchWorkflow(
                                model=model_option,
                                temperature=temperature
                            )
                        else:
                            workflow = ResearchWorkflow(
                                model=model_option,
                                temperature=temperature
                            )
                        
                        # Run workflow
                        results = workflow.run(query, st.session_state.papers)
                        st.session_state.workflow_results = results
                        
                        st.success("✅ Analysis complete! Check the 'Agent Collaboration' and 'Results' tabs.")
                        st.balloons()
                        
                    except Exception as e:
                        st.error(f"Error during analysis: {e}")
                        st.exception(e)
    
    with tab2:
        st.header("🤖 Agent Collaboration Flow")
        
        if st.session_state.workflow_results:
            conversation = st.session_state.workflow_results.get("conversation_history", [])
            
            if conversation:
                st.info(f"📊 Agent Workflow: {len(conversation)} agents participated")
                
                # Display conversation flow
                for i, step in enumerate(conversation):
                    with st.container():
                        display_agent_response(
                            step["agent"],
                            step["role"],
                            step["message"]
                        )
            else:
                st.warning("No conversation history available.")
        else:
            st.info("👈 Start by searching for papers and running the agent analysis in the 'Research Query' tab.")
    
    with tab3:
        st.header("📊 Research Synthesis Results")
        
        if st.session_state.workflow_results:
            results = st.session_state.workflow_results
            
            # Display synthesis
            st.subheader("🎯 Final Synthesis")
            st.markdown(results.get("synthesis", "No synthesis available"))
            
            st.markdown("---")
            
            # Display follow-up questions
            st.subheader("❓ Follow-up Research Questions")
            questions = results.get("follow_up_questions", [])
            if questions:
                for q in questions:
                    st.markdown(f"- {q}")
            else:
                st.info("No follow-up questions generated.")
            
            st.markdown("---")
            
            # Download results
            col1, col2 = st.columns(2)
            
            with col1:
                # Create downloadable report
                report = f"""# Research Analysis Report

## Query
{results.get('query', 'N/A')}

## Research Summary
{results.get('research_summary', 'N/A')}

## Critical Analysis
{results.get('critique', 'N/A')}

## Follow-up Questions
{chr(10).join(['- ' + q for q in results.get('follow_up_questions', [])])}

## Final Synthesis
{results.get('synthesis', 'N/A')}

---
Generated by Research Agent System
"""
                st.download_button(
                    label="📥 Download Full Report",
                    data=report,
                    file_name="research_report.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            
            with col2:
                if st.button("🔄 Start New Analysis", use_container_width=True):
                    st.session_state.papers = []
                    st.session_state.workflow_results = None
                    st.rerun()
        else:
            st.info("👈 Start by searching for papers and running the agent analysis in the 'Research Query' tab.")
            
            # Show example
            with st.expander("📖 How it works"):
                st.markdown("""
                ### Research Agent System Workflow
                
                1. **Search & Ingest**: Search arXiv for relevant papers on your topic
                2. **Research Agent**: Analyzes papers and creates comprehensive summaries
                3. **Critic Agent**: Critically evaluates findings and identifies limitations
                4. **Question Generator**: Creates follow-up research questions
                5. **Synthesizer Agent**: Integrates all insights into a cohesive report
                
                **Example topics to try:**
                - AI for climate change modeling
                - Quantum computing applications in cryptography
                - CRISPR gene editing advances
                - Neural architecture search
                - Battery technology improvements
                """)


if __name__ == "__main__":
    main()

