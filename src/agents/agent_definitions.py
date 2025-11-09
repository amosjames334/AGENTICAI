"""Agent definitions and prompts"""
from typing import TypedDict, List, Dict, Annotated, Optional
from langchain_openai import ChatOpenAI
import operator
import logging

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State shared across all agents"""
    query: str
    papers: List[Dict]
    research_summary: str
    critique: str
    follow_up_questions: List[str]
    synthesis: str
    conversation_history: Annotated[List[Dict], operator.add]
    current_agent: str
    iteration: int


def retrieve_evidence(
    query: str, 
    k: int = 5, 
    vector_store_dir: Optional[str] = None,
    session_manager=None
) -> Optional[List[Dict]]:
    """
    Retrieve evidence from vector store
    
    Args:
        query: Query string
        k: Number of results to return
        vector_store_dir: Vector store directory path (overridden by session_manager)
        session_manager: Optional SessionManager for session-based retrieval
        
    Returns:
        List of search hits with scores, text, and metadata
    """
    try:
        from ..ingestion.document_processor import DocumentProcessor
        import os
        
        # DEBUG: Log inputs
        logger.info("DEBUG: retrieve_evidence() called")
        logger.info(f"DEBUG:   query: {query[:50]}...")
        logger.info(f"DEBUG:   k: {k}")
        logger.info(f"DEBUG:   vector_store_dir: {vector_store_dir}")
        logger.info(f"DEBUG:   session_manager: {session_manager}")
        
        # Determine vector store directory
        if session_manager:
            vs_dir = session_manager.get_vector_store_dir()
            logger.info(f"DEBUG:   Using session_manager path: {vs_dir}")
        elif vector_store_dir:
            vs_dir = vector_store_dir
            logger.info(f"DEBUG:   Using provided vector_store_dir: {vs_dir}")
        else:
            vs_dir = "data/vector_store"
            logger.info(f"DEBUG:   Using default path: {vs_dir}")
        
        # DEBUG: Check if path exists
        logger.info(f"DEBUG:   Checking path: {vs_dir}")
        logger.info(f"DEBUG:   Path exists: {os.path.exists(vs_dir)}")
        if os.path.exists(vs_dir):
            logger.info(f"DEBUG:   Contents: {os.listdir(vs_dir)}")
        
        dp = DocumentProcessor(vector_store_dir=vs_dir)
        
        # DEBUG: Check store exists
        store_exists = dp.store_exists()
        logger.info(f"DEBUG:   Vector store exists: {store_exists}")
        
        if not store_exists:
            logger.warning("DEBUG:   ❌ Vector store does not exist at this path")
            logger.warning(f"DEBUG:   Looking for:")
            logger.warning(f"DEBUG:     - {vs_dir}/index.faiss")
            logger.warning(f"DEBUG:     - {vs_dir}/chunks.json")
            logger.warning(f"DEBUG:     - {vs_dir}/metadata.json")
            return None
        
        logger.info(f"DEBUG:   ✅ Vector store found, querying...")
        result = dp.query(query, k=k)
        logger.info(f"DEBUG:   Query returned {len(result) if result else 0} results")
        return result
    except Exception as e:
        logger.error(f"DEBUG: ❌ Error retrieving evidence: {e}")
        import traceback
        logger.error(f"DEBUG: Traceback: {traceback.format_exc()}")
        return None


class ResearchAgent:
    """Agent that reads and summarizes research papers"""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.name = "Researcher"
        self.role = "Research Analyst"
        
    @property
    def system_prompt(self) -> str:
        return """You are a Research Analyst agent specialized in reading and summarizing academic papers.

Your responsibilities:
1. Analyze research papers thoroughly
2. Extract key findings, methodologies, and conclusions
3. Identify important concepts and data points
4. Create clear, structured summaries
5. Highlight novel contributions and limitations

When summarizing:
- Focus on the core contributions and findings
- Explain complex concepts in accessible language
- Note the methodology used
- Identify gaps or limitations mentioned
- Connect findings to the broader research question

Be thorough but concise. Prioritize clarity and accuracy."""

    def process(self, state: AgentState) -> Dict:
        """Process the research papers and create a summary"""
        query = state["query"]
        papers = state["papers"]
        
        # DEBUG: Log the query and papers
        logger.info("="*80)
        logger.info("DEBUG: ResearchAgent.process() called")
        logger.info(f"DEBUG: Query: {query}")
        logger.info(f"DEBUG: Number of papers: {len(papers)}")
        logger.info(f"DEBUG: Papers have pdf_path: {any(p.get('pdf_path') for p in papers)}")
        
        # Try to retrieve evidence from vector store
        logger.info("DEBUG: Attempting to retrieve evidence from vector store...")
        evidence_hits = retrieve_evidence(query, k=10)
        
        # DEBUG: Log retrieval results
        if evidence_hits:
            logger.info(f"DEBUG: ✅ Successfully retrieved {len(evidence_hits)} chunks from vector store")
            logger.info(f"DEBUG: Sample chunk score: {evidence_hits[0]['score']:.3f}")
            logger.info(f"DEBUG: Sample chunk preview: {evidence_hits[0]['text'][:100]}...")
        else:
            logger.warning("DEBUG: ❌ No evidence retrieved from vector store - will use abstracts")
        logger.info("="*80)
        
        if evidence_hits:
            # Use vector store evidence
            logger.info(f"Using vector store evidence: {len(evidence_hits)} chunks")
            evidence_snippets = [h["text"] for h in evidence_hits]
            evidence_text = "\n\n---\n\n".join([
                f"Evidence {i+1} (score: {evidence_hits[i]['score']:.3f}):\n{snippet}"
                for i, snippet in enumerate(evidence_snippets[:8])  # Limit to top 8
            ])
            
            prompt = f"""Based on the following evidence from research papers related to "{query}", 
provide a comprehensive research summary:

EVIDENCE FROM PAPERS:
{evidence_text}

Your summary should:
1. Identify the main themes and patterns across the evidence
2. Highlight key findings and methodologies
3. Note any consensus or disagreements
4. Identify novel contributions
5. Point out research gaps or limitations

Provide your analysis:"""
        else:
            # Fallback to abstracts if vector store not available
            logger.info("Vector store not available, using paper abstracts")
            papers_text = "\n\n".join([
                f"Paper {i+1}: {p['title']}\n"
                f"Authors: {', '.join(p['authors'])}\n"
                f"Abstract: {p['abstract']}\n"
                f"Published: {p['published']}"
                for i, p in enumerate(papers[:5])  # Limit to first 5 papers
            ])
            
            prompt = f"""Based on the following research papers related to "{query}", 
provide a comprehensive research summary:

{papers_text}

Your summary should:
1. Identify the main themes and patterns across papers
2. Highlight key findings and methodologies
3. Note any consensus or disagreements
4. Identify novel contributions
5. Point out research gaps or limitations

Provide your analysis:"""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response = self.llm.invoke(messages)
        
        return {
            "research_summary": response.content,
            "conversation_history": [{
                "agent": self.name,
                "role": self.role,
                "message": response.content
            }],
            "current_agent": self.name
        }


class CriticAgent:
    """Agent that critiques and questions research findings"""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.name = "Critic"
        self.role = "Research Critic"
        
    @property
    def system_prompt(self) -> str:
        return """You are a Research Critic agent specialized in critical analysis and questioning.

Your responsibilities:
1. Critically evaluate research summaries and findings
2. Identify potential weaknesses or gaps in reasoning
3. Question assumptions and methodologies
4. Suggest alternative interpretations
5. Highlight areas needing more investigation

When critiquing:
- Be constructive and specific
- Question methodological choices
- Identify potential biases or limitations
- Suggest what might be missing
- Consider alternative explanations
- Point out inconsistencies

Your goal is to strengthen research through rigorous questioning, not to dismiss it."""

    def process(self, state: AgentState) -> Dict:
        """Critique the research summary"""
        research_summary = state["research_summary"]
        query = state["query"]
        
        prompt = f"""Review this research summary about "{query}":

{research_summary}

Provide a critical analysis:
1. What are the strengths of this research?
2. What are the potential weaknesses or limitations?
3. What assumptions might be questionable?
4. What important perspectives or approaches might be missing?
5. What inconsistencies or gaps do you notice?
6. What would make this research more robust?

Provide your critique:"""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response = self.llm.invoke(messages)
        
        return {
            "critique": response.content,
            "conversation_history": [{
                "agent": self.name,
                "role": self.role,
                "message": response.content
            }],
            "current_agent": self.name
        }


class QuestionGeneratorAgent:
    """Agent that generates follow-up research questions"""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.name = "Question Generator"
        self.role = "Research Question Specialist"
        
    @property
    def system_prompt(self) -> str:
        return """You are a Question Generator agent specialized in identifying research directions.

Your responsibilities:
1. Generate insightful follow-up questions based on research findings
2. Identify unexplored areas and research gaps
3. Propose new research directions
4. Connect findings to broader questions
5. Suggest interdisciplinary connections

When generating questions:
- Make them specific and actionable
- Build on identified gaps and limitations
- Consider practical applications
- Think about interdisciplinary connections
- Balance depth and breadth
- Prioritize high-impact questions

Good questions drive discovery forward."""

    def process(self, state: AgentState) -> Dict:
        """Generate follow-up research questions"""
        research_summary = state["research_summary"]
        critique = state["critique"]
        query = state["query"]
        
        prompt = f"""Based on this research about "{query}":

RESEARCH SUMMARY:
{research_summary}

CRITICAL ANALYSIS:
{critique}

Generate 5-7 specific follow-up research questions that would:
1. Address identified gaps and limitations
2. Explore new directions
3. Deepen understanding
4. Have practical impact
5. Connect to related fields

Provide your questions as a numbered list with brief explanations for each."""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response = self.llm.invoke(messages)
        
        # Parse questions (simple parsing)
        questions = [line.strip() for line in response.content.split('\n') 
                    if line.strip() and (line.strip()[0].isdigit() or line.strip().startswith('-'))]
        
        return {
            "follow_up_questions": questions,
            "conversation_history": [{
                "agent": self.name,
                "role": self.role,
                "message": response.content
            }],
            "current_agent": self.name
        }


class SynthesizerAgent:
    """Agent that synthesizes insights from all agents"""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.name = "Synthesizer"
        self.role = "Research Synthesizer"
        
    @property
    def system_prompt(self) -> str:
        return """You are a Synthesizer agent specialized in integrating diverse perspectives.

Your responsibilities:
1. Combine insights from research, critique, and questions
2. Create a coherent narrative that captures the full picture
3. Highlight consensus and disagreements
4. Provide actionable recommendations
5. Explain the reasoning chain clearly

When synthesizing:
- Show how different perspectives connect
- Acknowledge tensions and trade-offs
- Build a coherent story from fragments
- Make the reasoning process transparent
- Provide clear, actionable insights
- Ground conclusions in evidence

Your synthesis should be more valuable than the sum of its parts."""

    def process(self, state: AgentState) -> Dict:
        """Synthesize all insights into a final report"""
        query = state["query"]
        research_summary = state["research_summary"]
        critique = state["critique"]
        questions = state["follow_up_questions"]
        
        prompt = f"""Synthesize the following research analysis about "{query}":

RESEARCH SUMMARY:
{research_summary}

CRITICAL ANALYSIS:
{critique}

FOLLOW-UP QUESTIONS:
{chr(10).join(questions)}

Create a comprehensive synthesis that:
1. Summarizes the current state of knowledge
2. Integrates the critique to provide a balanced view
3. Highlights key insights and their implications
4. Connects findings to practical applications
5. Outlines promising future research directions
6. Makes the reasoning chain transparent

Provide your synthesis:"""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response = self.llm.invoke(messages)
        
        return {
            "synthesis": response.content,
            "conversation_history": [{
                "agent": self.name,
                "role": self.role,
                "message": response.content
            }],
            "current_agent": self.name
        }

