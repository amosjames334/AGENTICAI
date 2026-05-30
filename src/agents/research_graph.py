"""Research workflow orchestration.

This module preserves the original public API (`ResearchWorkflow`,
`InteractiveResearchWorkflow`) used by `app.py` and `cli.py`, but the
implementation now delegates to a single Claude-powered ReAct reasoning agent
(see `reasoning_agent.py`) instead of a fixed multi-agent chain. The agent
decides its own steps and calls tools (local vector store + Brave Search MCP).
"""
from typing import Dict, Any
import logging
from dotenv import load_dotenv

from .reasoning_agent import ReasoningAgent

load_dotenv()
logger = logging.getLogger(__name__)


class ResearchWorkflow:
    """Orchestrates the reasoning-agent research workflow.

    Keeps the same constructor and `run()` signature/return shape as before so
    the Streamlit UI and CLI continue to work unchanged.
    """

    def __init__(self, model: str = "claude-sonnet-4-5-20250929",
                 temperature: float = 0.7):
        # `model` controls the final synthesis pass; the reasoning loop always
        # uses the cheap/fast model (Haiku) to stay within rate limits.
        self.agent = ReasoningAgent(model=model, temperature=temperature)

    def run(self, query: str, papers: list,
            vector_store_dir: str = None) -> Dict[str, Any]:
        """Run the reasoning workflow.

        Args:
            query: Research question
            papers: List of paper metadata
            vector_store_dir: Optional path to vector store directory

        Returns:
            Result dict with keys: query, conversation_history, synthesis,
            follow_up_questions, insight_report, research_summary, critique.
        """
        logger.info("=" * 80)
        logger.info("ResearchWorkflow.run() -> Claude ReAct reasoning agent")
        logger.info(f"Query: {query}")
        logger.info(f"Number of papers: {len(papers) if papers else 0}")
        logger.info(f"Vector store dir: {vector_store_dir}")
        logger.info("=" * 80)

        return self.agent.run(query, papers, vector_store_dir=vector_store_dir)

    def run_streaming(self, query: str, papers: list,
                      vector_store_dir: str = None,
                      on_event=None) -> Dict[str, Any]:
        """Run the reasoning workflow, emitting live events via `on_event`.

        `on_event` is called from a worker thread, so it must be thread-safe
        (e.g. a `queue.Queue.put`). Returns the same result dict as `run()`,
        including a `stats` entry.
        """
        logger.info("ResearchWorkflow.run_streaming() -> Claude ReAct agent")
        return self.agent.run_streaming(
            query, papers, vector_store_dir=vector_store_dir, on_event=on_event
        )

    def get_conversation_flow(self, state: Dict[str, Any]) -> list:
        """Extract the conversation flow from the state"""
        return state.get("conversation_history", [])


class InteractiveResearchWorkflow(ResearchWorkflow):
    """Backwards-compatible alias.

    The new reasoning agent already iterates on its own (it loops over
    think/act/observe until satisfied), so the previously separate "interactive
    refinement" mode is now the default behavior.
    """
    pass
