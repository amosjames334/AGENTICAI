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
    insight_report: str  # Collective insight report
    conversation_history: Annotated[List[Dict], operator.add]  # Now includes multi-agent exchanges
    current_agent: str
    iteration: int
    vector_store_dir: Optional[str]  # Add vector store directory


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
        # Use absolute import to avoid relative import issues
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from ingestion.document_processor import DocumentProcessor
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

When responding to other agents:
- Address their specific concerns directly
- Use phrases like "You raised a good point about...", "Regarding your question on..."
- Provide evidence or reasoning to support your response
- Acknowledge valid criticisms and refine your position

Be thorough but concise. Prioritize clarity and accuracy."""
    
    def respond_to(self, state: AgentState, responding_to: str) -> Dict:
        """Respond to another agent's critique or question"""
        conversation = state.get("conversation_history", [])
        research_summary = state.get("research_summary", "")
        
        # Get the message we're responding to
        target_message = None
        for msg in reversed(conversation):
            if msg["agent"] == responding_to:
                target_message = msg["message"]
                break
        
        if not target_message:
            return {}
        
        prompt = f"""You are in a research discussion. Another agent ({responding_to}) has responded to your analysis.

YOUR ORIGINAL ANALYSIS:
{research_summary[:1500]}

THEIR RESPONSE:
{target_message[:1000]}

Now respond directly to their points. Address their specific concerns, acknowledge valid criticisms, and refine or defend your position as appropriate. Use conversational language like:
- "You raise a valid concern about..."
- "Regarding your point on [X], I'd argue that..."
- "That's fair, but let me clarify..."
- "I agree that [X], however..."

Keep your response focused and conversational (2-3 paragraphs)."""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response = self.llm.invoke(messages)
        
        return {
            "conversation_history": [{
                "agent": self.name,
                "role": self.role,
                "message": response.content,
                "responding_to": responding_to
            }],
            "current_agent": self.name
        }

    def process(self, state: AgentState) -> Dict:
        """Process the research papers and create a summary"""
        query = state["query"]
        papers = state["papers"]
        vector_store_dir = state.get("vector_store_dir")
        
        # DEBUG: Log the query and papers
        logger.info("="*80)
        logger.info("DEBUG: ResearchAgent.process() called")
        logger.info(f"DEBUG: Query: {query}")
        logger.info(f"DEBUG: Number of papers: {len(papers)}")
        logger.info(f"DEBUG: Papers have pdf_path: {any(p.get('pdf_path') for p in papers)}")
        logger.info(f"DEBUG: Vector store dir from state: {vector_store_dir}")
        
        # Try to retrieve evidence from vector store
        logger.info("DEBUG: Attempting to retrieve evidence from vector store...")
        evidence_hits = retrieve_evidence(query, k=10, vector_store_dir=vector_store_dir)
        
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
- Question methodological choices directly to the analyst
- Identify potential biases or limitations
- Suggest what might be missing
- Consider alternative explanations
- Point out inconsistencies
- Use conversational language: "You claim that...", "But have you considered..."

When responding to other agents:
- Acknowledge their points: "I see your point about..."
- Refine your critique based on their response
- Ask follow-up questions
- Be open to revising your assessment

Your goal is to strengthen research through rigorous dialogue, not to dismiss it."""

    def process(self, state: AgentState) -> Dict:
        """Critique the research summary in a conversational way"""
        research_summary = state["research_summary"]
        query = state["query"]
        
        prompt = f"""You're in a research discussion about "{query}". The Analyst just presented their findings:

{research_summary}

Respond directly to the Analyst with your critical assessment. Address them conversationally:
- Start with "I appreciate your analysis, but..."  or "You've made interesting points, however..."
- Use direct questions: "But have you considered...?" "How do you account for...?"
- Challenge specific claims: "You state that X, but isn't it possible that Y?"
- Point out what's missing: "I notice you don't address..."

Be constructive but probing. Make this feel like a real academic discussion.

Provide your response (2-3 paragraphs):"""

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
                "message": response.content,
                "responding_to": "Researcher"
            }],
            "current_agent": self.name
        }
    
    def respond_to(self, state: AgentState, responding_to: str) -> Dict:
        """Respond to another agent's response"""
        conversation = state.get("conversation_history", [])
        critique = state.get("critique", "")
        
        # Get the message we're responding to
        target_message = None
        for msg in reversed(conversation):
            if msg["agent"] == responding_to and msg.get("responding_to") == self.name:
                target_message = msg["message"]
                break
        
        if not target_message:
            return {}
        
        prompt = f"""You're continuing a research discussion. You raised some critiques, and the {responding_to} has responded.

YOUR CRITIQUE:
{critique[:1000]}

THEIR RESPONSE:
{target_message[:1000]}

Now respond to their points. Either:
- Acknowledge if they've addressed your concerns: "That's a fair clarification..."
- Push back if needed: "I'm still not convinced because..."
- Ask follow-up questions: "But what about...?"
- Find middle ground: "So we agree that X, but disagree on Y?"

Keep it conversational (2-3 paragraphs)."""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response = self.llm.invoke(messages)
        
        return {
            "conversation_history": [{
                "agent": self.name,
                "role": self.role,
                "message": response.content,
                "responding_to": responding_to
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
3. Highlight consensus and disagreements reached through dialogue
4. Provide actionable recommendations
5. Explain the reasoning chain clearly

When synthesizing:
- Reference specific points from the agent conversation
- Show how the dialogue led to refined understanding
- Acknowledge tensions and how they were resolved
- Build a coherent story from the collaborative discussion
- Make the reasoning process transparent
- Use phrases like "After the exchange between agents...", "As the discussion revealed..."
- Provide clear, actionable insights
- Ground conclusions in evidence

Your synthesis should reflect the collaborative reasoning process."""

    def process(self, state: AgentState) -> Dict:
        """Synthesize all insights into a final report, referencing the conversation"""
        query = state["query"]
        research_summary = state["research_summary"]
        critique = state["critique"]
        questions = state["follow_up_questions"]
        conversation = state.get("conversation_history", [])
        
        # Extract key conversation points
        conversation_summary = "\n\n".join([
            f"**{msg['agent']}** (responding to {msg.get('responding_to', 'initial')}): {msg['message'][:300]}..."
            for msg in conversation[-4:]  # Last 4 messages (the back-and-forth)
        ])
        
        prompt = f"""You've been observing a research discussion about "{query}". The agents had a back-and-forth conversation:

CONVERSATION HIGHLIGHTS:
{conversation_summary}

INITIAL RESEARCH SUMMARY:
{research_summary[:1000]}

FOLLOW-UP QUESTIONS IDENTIFIED:
{chr(10).join(questions)}

Create a synthesis that:
1. References specific points from the agent conversation
2. Shows how the dialogue refined the initial understanding
3. Highlights what the agents agreed on after discussion
4. Notes remaining tensions or unresolved questions
5. Explains the reasoning chain that emerged from their exchange
6. Provides actionable insights based on the collective reasoning

Use phrases like:
- "Through the exchange, the agents clarified that..."
- "The Critic's challenge led the Analyst to refine..."
- "After discussion, both agents agreed that..."
- "The conversation revealed..."

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


class DialogueModerator:
    """Agent that facilitates conversations between research agents"""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.name = "Moderator"
        self.role = "Dialogue Facilitator"
    
    def facilitate_dialogue(
        self, 
        state: AgentState, 
        topic: str,
        participants: List[str],
        turns: int = 3
    ) -> Dict:
        """
        Facilitate a multi-turn conversation between agents
        
        Args:
            state: Current agent state
            topic: Topic to discuss
            participants: List of agent names/roles
            turns: Number of conversational turns
            
        Returns:
            Updated state with dialogue exchanges
        """
        research_summary = state.get("research_summary", "")
        critique = state.get("critique", "")
        
        # Create dialogue prompt
        prompt = f"""You are facilitating a research dialogue on: "{state['query']}"

RESEARCH SUMMARY:
{research_summary[:1000]}...

CRITIQUE POINTS:
{critique[:800]}...

Generate a {turns}-turn conversation between these research agents:
- Analyst: Presents findings and interpretations
- Critic: Questions methodology and challenges assumptions  
- Moderator: Synthesizes and guides toward resolution

Format each turn as:
**[Agent Name]:** "Their statement or question"

The conversation should show:
1. Direct challenges and responses
2. Building on each other's points
3. Reasoning chains ("If X, then Y")
4. Tension and resolution
5. Cross-referencing earlier points

Topic for this dialogue: {topic}

Generate the conversation:"""

        messages = [
            {"role": "system", "content": "You generate realistic multi-agent research dialogues showing visible reasoning."},
            {"role": "user", "content": prompt}
        ]
        
        response = self.llm.invoke(messages)
        
        return {
            "dialogue_exchanges": [{
                "topic": topic,
                "participants": participants,
                "content": response.content,
                "type": "facilitated_dialogue"
            }],
            "conversation_history": [{
                "agent": self.name,
                "role": self.role,
                "message": f"Facilitated dialogue on: {topic}"
            }],
            "current_agent": self.name
        }
    
    def create_debate(
        self,
        state: AgentState,
        debate_topic: str,
        position_a: str,
        position_b: str
    ) -> Dict:
        """
        Create a debate-style exchange between two positions
        
        Args:
            state: Current agent state
            debate_topic: Topic to debate
            position_a: First position/claim
            position_b: Counter position/claim
            
        Returns:
            Updated state with debate exchange
        """
        prompt = f"""Generate a focused debate on: {debate_topic}

Position A: {position_a}
Position B: {position_b}

Create a 4-turn debate showing:
1. Agent A makes their case with evidence
2. Agent B challenges with counterpoints
3. Agent A responds and refines their position
4. Both agents find synthesis/resolution

Format:
**Agent A:** "Statement"
**Agent B:** "Response"

Make it feel like real reasoning with:
- "But consider..."
- "True, yet..."
- "Building on that point..."
- "Given this evidence, it follows that..."

Generate the debate:"""

        messages = [
            {"role": "system", "content": "You create structured debates showing reasoning dynamics."},
            {"role": "user", "content": prompt}
        ]
        
        response = self.llm.invoke(messages)
        
        return {
            "dialogue_exchanges": [{
                "topic": debate_topic,
                "format": "debate",
                "position_a": position_a,
                "position_b": position_b,
                "content": response.content,
                "type": "debate"
            }],
            "conversation_history": [{
                "agent": self.name,
                "role": self.role,
                "message": f"Moderated debate on: {debate_topic}"
            }],
            "current_agent": self.name
        }
    
    def create_reasoning_chain(
        self,
        state: AgentState,
        claim: str,
        evidence_points: List[str]
    ) -> Dict:
        """
        Create an explicit reasoning chain dialogue
        
        Args:
            state: Current agent state  
            claim: Main claim to reason about
            evidence_points: Supporting evidence
            
        Returns:
            Updated state with reasoning dialogue
        """
        evidence_text = "\n".join([f"- {point}" for point in evidence_points[:5]])
        
        prompt = f"""Create a dialogue showing step-by-step reasoning for this claim:

CLAIM: {claim}

EVIDENCE:
{evidence_text}

Generate a 3-agent conversation showing how they build this reasoning chain:
- Analyst: Presents evidence and initial reasoning
- Critic: Tests the logic, asks "does this follow?"
- Synthesizer: Connects the steps into a coherent chain

Use explicit reasoning connectors:
- "If X, then Y"
- "Given that..., it follows that..."
- "Therefore..."
- "This implies..."

Show agents referencing each other:
- "Building on [Agent]'s point about..."
- "As [Agent] noted..."
- "That challenges my earlier assumption that..."

Format:
**[Agent]:** "Statement"

Generate the reasoning dialogue:"""

        messages = [
            {"role": "system", "content": "You create dialogues that make reasoning chains explicit and visible."},
            {"role": "user", "content": prompt}
        ]
        
        response = self.llm.invoke(messages)
        
        return {
            "dialogue_exchanges": [{
                "topic": "reasoning_chain",
                "claim": claim,
                "content": response.content,
                "type": "reasoning_chain"
            }],
            "conversation_history": [{
                "agent": self.name,
                "role": self.role,
                "message": f"Built reasoning chain for: {claim}"
            }],
            "current_agent": self.name
        }


class InsightGeneratorAgent:
    """Agent that generates collective insights and testable hypotheses"""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.name = "Insight Generator"
        self.role = "Collective Insight Agent"
        
    @property
    def system_prompt(self) -> str:
        return """You are an Insight Generator agent specialized in meta-analysis and hypothesis formation.

Your responsibilities:
1. Distill the collective findings of all agents into a core insight
2. Trace the reasoning by citing specific agent contributions
3. Generate a testable hypothesis based on the converging ideas
4. Assess confidence level based on evidence density and agreement

When generating insights:
- Identify the emergent theme or converging idea across all agents
- Be concise and high-signal (avoid repetition)
- Make hypotheses specific and testable
- Ground confidence assessment in actual evidence quality
- Think meta-level: what do the agents collectively reveal?

Your insight report should be the culmination of the entire discussion."""

    def process(self, state: AgentState) -> Dict:
        """Generate collective insight report"""
        query = state["query"]
        research_summary = state.get("research_summary", "")
        critique = state.get("critique", "")
        synthesis = state.get("synthesis", "")
        questions = state.get("follow_up_questions", [])
        conversation = state.get("conversation_history", [])
        
        # Extract key conversation points for citation
        agent_contributions = {}
        for msg in conversation:
            agent = msg["agent"]
            if agent not in agent_contributions:
                agent_contributions[agent] = []
            agent_contributions[agent].append(msg["message"][:200] + "...")
        
        contributions_text = "\n".join([
            f"**{agent}**: {contrib[0] if contrib else 'N/A'}"
            for agent, contrib in agent_contributions.items()
        ])
        
        prompt = f"""Based on the entire research discussion about "{query}", create a Collective Insight Report.

AGENT CONTRIBUTIONS:
{contributions_text}

SYNTHESIS:
{synthesis[:1000]}

FOLLOW-UP QUESTIONS:
{chr(10).join(questions[:3])}

Generate a structured insight report with these sections:

**Collective Insight Report – {query}**

**Core Insight:**
(2-3 sentences summarizing what all agents collectively revealed—the converging idea or emergent theme)

**Reasoning Trace / Citations:**
(Bullet points citing where that insight came from, e.g., "From Researcher: emphasized hybrid pipelines", "From Critic: noted scalability limits", "From Synthesizer: converged on pragmatic approaches")

**Hypothesis / Next Exploration:**
(A concise, research-style testable statement. Format: "If [condition], then [measurable outcome] for [scope]")

**Confidence Level:**
(Choose: High / Medium / Low, with brief justification based on evidence density and agent agreement)

Generate the complete report:"""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response = self.llm.invoke(messages)
        
        return {
            "insight_report": response.content,
            "conversation_history": [{
                "agent": self.name,
                "role": self.role,
                "message": response.content
            }],
            "current_agent": self.name
        }

