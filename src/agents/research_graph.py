"""Multi-agent research workflow using LangGraph"""
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
import os
import logging
from dotenv import load_dotenv

from .agent_definitions import (
    AgentState,
    ResearchAgent,
    CriticAgent,
    QuestionGeneratorAgent,
    SynthesizerAgent
)

load_dotenv()
logger = logging.getLogger(__name__)


class ResearchWorkflow:
    """Orchestrates multi-agent research workflow"""
    
    def __init__(self, model: str = "gpt-4-turbo-preview", temperature: float = 0.7):
        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Initialize agents
        self.research_agent = ResearchAgent(self.llm)
        self.critic_agent = CriticAgent(self.llm)
        self.question_agent = QuestionGeneratorAgent(self.llm)
        self.synthesizer_agent = SynthesizerAgent(self.llm)
        
        # Build the workflow graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the agent workflow graph"""
        workflow = StateGraph(AgentState)
        
        # Add nodes for each agent
        workflow.add_node("researcher", self._researcher_node)
        workflow.add_node("critic", self._critic_node)
        workflow.add_node("question_generator", self._question_node)
        workflow.add_node("synthesizer", self._synthesizer_node)
        
        # Define the workflow edges
        workflow.set_entry_point("researcher")
        workflow.add_edge("researcher", "critic")
        workflow.add_edge("critic", "question_generator")
        workflow.add_edge("question_generator", "synthesizer")
        workflow.add_edge("synthesizer", END)
        
        return workflow.compile()
    
    def _researcher_node(self, state: AgentState) -> Dict[str, Any]:
        """Research agent node"""
        return self.research_agent.process(state)
    
    def _critic_node(self, state: AgentState) -> Dict[str, Any]:
        """Critic agent node"""
        return self.critic_agent.process(state)
    
    def _question_node(self, state: AgentState) -> Dict[str, Any]:
        """Question generator agent node"""
        return self.question_agent.process(state)
    
    def _synthesizer_node(self, state: AgentState) -> Dict[str, Any]:
        """Synthesizer agent node"""
        return self.synthesizer_agent.process(state)
    
    def run(self, query: str, papers: list, vector_store_dir: str = None) -> Dict[str, Any]:
        """
        Run the research workflow
        
        Args:
            query: Research question
            papers: List of paper metadata
            vector_store_dir: Optional path to vector store directory
            
        Returns:
            Final state after all agents have processed
        """
        # DEBUG: Log workflow inputs
        logger.info("="*80)
        logger.info("DEBUG: ResearchWorkflow.run() called")
        logger.info(f"DEBUG: Query: {query}")
        logger.info(f"DEBUG: Number of papers: {len(papers)}")
        logger.info(f"DEBUG: Vector store dir: {vector_store_dir}")
        if papers:
            logger.info(f"DEBUG: Sample paper keys: {list(papers[0].keys())}")
            logger.info(f"DEBUG: Papers with pdf_path: {sum(1 for p in papers if p.get('pdf_path'))}")
            if papers[0].get('pdf_path'):
                logger.info(f"DEBUG: Sample pdf_path: {papers[0]['pdf_path']}")
        logger.info("="*80)
        
        initial_state: AgentState = {
            "query": query,
            "papers": papers,
            "research_summary": "",
            "critique": "",
            "follow_up_questions": [],
            "synthesis": "",
            "conversation_history": [],
            "current_agent": "",
            "iteration": 0,
            "vector_store_dir": vector_store_dir
        }
        
        # Run the graph
        final_state = self.graph.invoke(initial_state)
        
        return final_state
    
    def get_conversation_flow(self, state: Dict[str, Any]) -> list:
        """Extract the conversation flow from the state"""
        return state.get("conversation_history", [])


class InteractiveResearchWorkflow(ResearchWorkflow):
    """Extended workflow with iterative refinement"""
    
    def _build_graph(self) -> StateGraph:
        """Build an interactive workflow graph with potential loops"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("researcher", self._researcher_node)
        workflow.add_node("critic", self._critic_node)
        workflow.add_node("question_generator", self._question_node)
        workflow.add_node("synthesizer", self._synthesizer_node)
        workflow.add_node("refiner", self._refiner_node)
        
        # Define workflow
        workflow.set_entry_point("researcher")
        workflow.add_edge("researcher", "critic")
        workflow.add_edge("critic", "question_generator")
        workflow.add_edge("question_generator", "synthesizer")
        
        # Add conditional edge for refinement
        workflow.add_conditional_edges(
            "synthesizer",
            self._should_refine,
            {
                "refine": "refiner",
                "end": END
            }
        )
        workflow.add_edge("refiner", END)
        
        return workflow.compile()
    
    def _refiner_node(self, state: AgentState) -> Dict[str, Any]:
        """Refiner agent that can iterate on findings"""
        synthesis = state["synthesis"]
        critique = state["critique"]
        
        prompt = f"""Review this synthesis and critique:

SYNTHESIS:
{synthesis}

ORIGINAL CRITIQUE:
{critique}

Provide a refined final version that:
1. Addresses any concerns from the critique
2. Strengthens weak points
3. Adds clarity where needed
4. Provides actionable recommendations

Refined synthesis:"""
        
        messages = [
            {"role": "system", "content": "You are a Research Refiner agent that improves and polishes research outputs."},
            {"role": "user", "content": prompt}
        ]
        
        response = self.llm.invoke(messages)
        
        return {
            "synthesis": response.content,
            "conversation_history": [{
                "agent": "Refiner",
                "role": "Research Refiner",
                "message": response.content
            }],
            "current_agent": "Refiner",
            "iteration": state["iteration"] + 1
        }
    
    def _should_refine(self, state: AgentState) -> str:
        """Decide whether to refine or end"""
        # For now, only refine once
        if state["iteration"] > 0:
            return "end"
        return "refine"

