"""Claude-powered ReAct reasoning agent with tiered model usage.

Uses a lightweight model (Haiku) for the iterative tool-calling reasoning loop,
then a stronger model (Sonnet) only for producing the final structured answer.
This keeps costs and rate-limit usage low while preserving quality where it
matters.

Tools available to the agent:
- `vector_store_search`: retrieve evidence from the local FAISS vector store.
- Brave Search MCP tools: live web search (if BRAVE_API_KEY is configured).
"""
import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Tiered model defaults — Haiku for cheap reasoning, Sonnet for final answer.
LIGHT_MODEL = "claude-haiku-4-5-20251001"
HEAVY_MODEL = "claude-sonnet-4-5-20250929"

REASONING_SYSTEM_PROMPT = """You are an autonomous Research Reasoning Agent.

You are given a research question and a set of source papers. Your job is not to
blindly summarize, but to *think for yourself* and build a well-reasoned answer.

How you must work:
1. THINK FIRST. Before answering, lay out your reasoning: what do you already
   know, what is uncertain, and what evidence you need to gather.
2. USE YOUR TOOLS DELIBERATELY. You decide when and how to use them:
   - `vector_store_search`: search the ingested research papers for grounded
     evidence. Prefer this for claims about the papers themselves. Call it
     multiple times with different, focused queries to dig deeper.
   - Brave web search tools (if available): use for recent developments,
     definitions, context, or to cross-check claims against the wider world.
3. REASON OVER EVIDENCE. Compare sources, weigh agreement vs. disagreement,
   surface assumptions, and challenge weak claims (play your own critic).
4. ITERATE. If the evidence is thin or contradictory, search again with better
   queries before concluding. Do not stop at the first result.
5. BE HONEST about uncertainty and gaps. Distinguish what the evidence supports
   from your own inference.
6. BE CONCISE. Keep tool queries short and focused. Avoid repeating large blocks
   of evidence in your reasoning — refer to them by source and key point.

When you have gathered enough, produce your final answer as a coherent
narrative: a thorough synthesis, concrete follow-up research questions, and a
concise collective insight report with a testable hypothesis.

Show real reasoning, not a rigid template. Think like a careful researcher."""


class ResearchAnswer(BaseModel):
    """Structured final answer from the reasoning agent."""

    synthesis: str = Field(
        description="A thorough, well-reasoned synthesis answering the research "
        "question, grounded in the evidence gathered and noting agreements, "
        "tensions, and limitations."
    )
    follow_up_questions: List[str] = Field(
        default_factory=list,
        description="5-7 specific, actionable follow-up research questions.",
    )
    insight_report: str = Field(
        description="A concise collective insight report: a Core Insight, a "
        "Reasoning Trace citing the evidence used, a testable Hypothesis "
        "(If/then), and a Confidence Level (High/Medium/Low) with justification.",
    )


def _extract_text(content: Any) -> str:
    """Extract plain text from a message content (str or Anthropic blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "thinking":
                    parts.append(block.get("thinking", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(p for p in parts if p)
    return str(content) if content is not None else ""


def _make_vector_store_tool(vector_store_dir: Optional[str]):
    """Create a vector_store_search tool bound to a specific vector store dir."""

    @tool
    def vector_store_search(query: str, k: int = 5) -> str:
        """Search the ingested research papers (local vector store) for evidence
        relevant to a query. Use focused queries. Returns the top matching
        passages with their relevance scores and source paper titles."""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from agents.agent_definitions import retrieve_evidence

        hits = retrieve_evidence(query, k=k, vector_store_dir=vector_store_dir)
        if not hits:
            return ("No matching passages found in the local paper vector store "
                    "for this query.")

        blocks = []
        for i, h in enumerate(hits):
            meta = h.get("meta", {}) or {}
            title = meta.get("paper_title", "Unknown paper")
            blocks.append(
                f"[Result {i+1}] score={h.get('score', 0):.3f} | source: {title}\n"
                f"{h.get('text', '')}"
            )
        return "\n\n---\n\n".join(blocks)

    return vector_store_search


def _format_tool_args(args: Any) -> str:
    """Render tool-call arguments compactly for display."""
    if isinstance(args, dict):
        if "query" in args:
            return str(args["query"])
        return ", ".join(f"{k}={v}" for k, v in args.items())[:300]
    return str(args)[:300]


class ReasoningAgent:
    """Tiered Claude ReAct agent: Haiku reasons & calls tools, Sonnet synthesizes."""

    def __init__(self, model: str = HEAVY_MODEL,
                 temperature: float = 0.7, max_tokens: int = 4096):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from utils.config import Config

        api_key = Config.ANTHROPIC_API_KEY

        # Light model for the ReAct tool-calling loop (cheap, fast, low tokens).
        self.light_llm = ChatAnthropic(
            model=LIGHT_MODEL,
            temperature=temperature,
            max_tokens=2048,
            api_key=api_key,
        )

        # Heavy model only for the final structured synthesis pass.
        self.heavy_llm = ChatAnthropic(
            model=model if model != LIGHT_MODEL else HEAVY_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
        )

    async def _astream_run(self, query: str, papers: list,
                           vector_store_dir: Optional[str],
                           on_event: Optional[Callable[[Dict], None]] = None
                           ) -> Dict[str, Any]:
        """Core run that streams the reasoning loop and collects statistics.

        Emits events through `on_event` as the agent thinks, calls tools, and
        observes results. Returns the full result dict (including `stats`).
        """
        def emit(event: Dict) -> None:
            if on_event is not None:
                try:
                    on_event(event)
                except Exception:  # never let UI plumbing break the run
                    pass

        from tools.brave_search import get_brave_tools

        start_time = time.perf_counter()

        brave_tools = await get_brave_tools()
        tools = [_make_vector_store_tool(vector_store_dir)] + brave_tools

        tool_names = [getattr(t, "name", str(t)) for t in tools]
        logger.info(f"Reasoning agent tools: {tool_names}")
        logger.info(f"Light model (reasoning loop): {LIGHT_MODEL}")
        logger.info(f"Heavy model (final synthesis): {self.heavy_llm.model}")

        emit({
            "type": "phase",
            "label": "Reasoning & gathering evidence...",
            "tools": tool_names,
            "brave_enabled": bool(brave_tools),
        })

        # --- Phase 1: Haiku drives the ReAct reasoning + tool-calling loop ---
        agent = create_react_agent(
            self.light_llm,
            tools,
            prompt=REASONING_SYSTEM_PROMPT,
        )

        paper_context = "\n".join(
            f"- {p.get('title', 'Untitled')}" for p in (papers or [])[:10]
        )
        user_message = (
            f"Research question: {query}\n\n"
            f"Source papers in the local vector store:\n"
            f"{paper_context or '(none listed)'}\n\n"
            "Investigate this question. Reason step by step, use your tools to "
            "gather and cross-check evidence, then provide a thorough final "
            "answer with your synthesis, follow-up questions, and insight report."
        )

        conversation_history: List[Dict] = []
        reasoning_text = ""
        tool_counts: Dict[str, int] = {}
        thinking_steps = 0

        async for chunk in agent.astream(
            {"messages": [{"role": "user", "content": user_message}]},
            stream_mode="updates",
            config={"recursion_limit": 25},
        ):
            for node_name, node_update in (chunk or {}).items():
                new_messages = (node_update or {}).get("messages", []) \
                    if isinstance(node_update, dict) else []
                for msg in new_messages:
                    if isinstance(msg, AIMessage):
                        text = _extract_text(msg.content).strip()
                        if text:
                            thinking_steps += 1
                            reasoning_text += text + "\n\n"
                            step_entry = {
                                "agent": "Reasoning Agent",
                                "role": f"Thinking (step {thinking_steps})",
                                "message": text,
                            }
                            conversation_history.append(step_entry)
                            emit({"type": "thinking",
                                  "step": thinking_steps,
                                  "text": text})

                        for call in getattr(msg, "tool_calls", []) or []:
                            name = call.get("name", "tool")
                            args = call.get("args", {})
                            tool_counts[name] = tool_counts.get(name, 0) + 1
                            arg_str = _format_tool_args(args)
                            conversation_history.append({
                                "agent": "Reasoning Agent",
                                "role": "Tool Call",
                                "message": f"Calling `{name}` with: {arg_str}",
                            })
                            emit({"type": "tool_call",
                                  "name": name,
                                  "args": arg_str})

                    elif isinstance(msg, ToolMessage):
                        result = _extract_text(msg.content).strip()
                        display = result
                        if len(display) > 1200:
                            display = display[:1200] + "\n... (truncated)"
                        name = str(getattr(msg, "name", "tool")) or "tool"
                        conversation_history.append({
                            "agent": name,
                            "role": "Tool Result",
                            "message": display,
                            "responding_to": "Reasoning Agent",
                        })
                        emit({"type": "tool_result",
                              "name": name,
                              "result": display})

        # --- Phase 2: Sonnet produces the final structured answer ---
        emit({"type": "phase", "label": "Synthesizing final answer..."})

        synthesis_prompt = (
            f"A research reasoning agent investigated the following question:\n\n"
            f"**{query}**\n\n"
            f"Here is the full reasoning trace and evidence it gathered:\n\n"
            f"{reasoning_text[:6000]}\n\n"
            f"Based on this reasoning and evidence, produce the final output. "
            f"Structure your response as JSON with these keys:\n"
            f'- "synthesis": a thorough, well-reasoned synthesis\n'
            f'- "follow_up_questions": a list of 5-7 follow-up research questions\n'
            f'- "insight_report": a concise report with Core Insight, Reasoning '
            f"Trace, testable Hypothesis (If/then), and Confidence Level"
        )

        try:
            structured_response = await self.heavy_llm.with_structured_output(
                ResearchAnswer
            ).ainvoke([
                SystemMessage(content="You synthesize research findings into "
                              "structured, evidence-based reports."),
                HumanMessage(content=synthesis_prompt),
            ])
            synthesis = structured_response.synthesis
            follow_up_questions = structured_response.follow_up_questions
            insight_report = structured_response.insight_report
        except Exception as e:
            logger.error(f"Structured synthesis failed, using raw reasoning: {e}")
            synthesis = reasoning_text[:3000]
            follow_up_questions = []
            insight_report = ""

        conversation_history.append({
            "agent": "Reasoning Agent",
            "role": "Final Synthesis",
            "message": synthesis,
        })
        emit({"type": "synthesis", "text": synthesis})

        duration = time.perf_counter() - start_time
        stats = {
            "tool_counts": tool_counts,
            "total_tool_calls": sum(tool_counts.values()),
            "thinking_steps": thinking_steps,
            "duration_seconds": round(duration, 1),
            "light_model": LIGHT_MODEL,
            "heavy_model": self.heavy_llm.model,
            "brave_enabled": bool(brave_tools),
            "available_tools": tool_names,
        }

        result = {
            "query": query,
            "papers": papers,
            "research_summary": synthesis,
            "critique": "",
            "follow_up_questions": follow_up_questions,
            "synthesis": synthesis,
            "insight_report": insight_report,
            "conversation_history": conversation_history,
            "current_agent": "Reasoning Agent",
            "iteration": 1,
            "vector_store_dir": vector_store_dir,
            "stats": stats,
        }

        emit({"type": "stats", "stats": stats})
        emit({"type": "final", "results": result})
        return result

    async def _arun(self, query: str, papers: list,
                    vector_store_dir: Optional[str]) -> Dict[str, Any]:
        """Non-streaming run (CLI/back-compat). Still returns `stats`."""
        return await self._astream_run(query, papers, vector_store_dir,
                                       on_event=None)

    def run(self, query: str, papers: list,
            vector_store_dir: Optional[str] = None) -> Dict[str, Any]:
        """Synchronous entry point that drives the async ReAct loop.

        Runs the async agent in a dedicated thread with its own event loop so it
        works cleanly from synchronous callers (Streamlit, CLI) regardless of
        whether an event loop is already running in the calling thread.
        """
        import concurrent.futures

        def _runner() -> Dict[str, Any]:
            return asyncio.run(self._arun(query, papers, vector_store_dir))

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(_runner).result()

    def run_streaming(self, query: str, papers: list,
                      vector_store_dir: Optional[str] = None,
                      on_event: Optional[Callable[[Dict], None]] = None
                      ) -> Dict[str, Any]:
        """Synchronous streaming entry point.

        Drives the async streaming loop in a dedicated thread (own event loop)
        and invokes `on_event` as events occur. `on_event` must be thread-safe
        (e.g. a `queue.Queue.put`); it is called from the worker thread.
        """
        import concurrent.futures

        def _runner() -> Dict[str, Any]:
            return asyncio.run(
                self._astream_run(query, papers, vector_store_dir, on_event)
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(_runner).result()
