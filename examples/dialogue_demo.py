"""
Demonstration of the Conversational Dialogue System

This example shows how agents engage in visible conversations
with challenge-response dynamics and explicit reasoning chains.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.agent_definitions import DialogueModerator, AgentState
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()


def demo_debate():
    """Demonstrate debate-style dialogue"""
    print("=" * 80)
    print("🎯 DEMO 1: Debate-Style Dialogue")
    print("=" * 80)
    print()
    
    llm = ChatOpenAI(
        model="gpt-4-turbo-preview",
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    moderator = DialogueModerator(llm)
    
    # Create a mock state
    state: AgentState = {
        "query": "Quantum computing for drug discovery",
        "papers": [],
        "research_summary": "Research shows quantum algorithms can simulate molecular interactions with 15% improved accuracy.",
        "critique": "However, current quantum hardware limitations and error rates make practical applications uncertain.",
        "follow_up_questions": [],
        "synthesis": "",
        "conversation_history": [],
        "dialogue_exchanges": [],
        "current_agent": "",
        "iteration": 0,
        "vector_store_dir": None
    }
    
    print("Creating debate on: Hardware Readiness for Drug Discovery")
    print()
    
    result = moderator.create_debate(
        state=state,
        debate_topic="Are quantum computers ready for practical drug discovery?",
        position_a="Current NISQ devices are sufficient for initial molecular simulations",
        position_b="We need error correction and more qubits before practical applications"
    )
    
    dialogue = result["dialogue_exchanges"][0]
    print(f"Type: {dialogue['type']}")
    print(f"Topic: {dialogue['topic']}")
    print(f"Position A: {dialogue['position_a']}")
    print(f"Position B: {dialogue['position_b']}")
    print()
    print("--- DIALOGUE ---")
    print(dialogue['content'])
    print()


def demo_reasoning_chain():
    """Demonstrate reasoning chain dialogue"""
    print("=" * 80)
    print("🎯 DEMO 2: Reasoning Chain Dialogue")
    print("=" * 80)
    print()
    
    llm = ChatOpenAI(
        model="gpt-4-turbo-preview",
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    moderator = DialogueModerator(llm)
    
    state: AgentState = {
        "query": "Hybrid quantum-classical approaches",
        "papers": [],
        "research_summary": "Multiple papers explore hybrid approaches combining quantum and classical computation.",
        "critique": "",
        "follow_up_questions": [],
        "synthesis": "",
        "conversation_history": [],
        "dialogue_exchanges": [],
        "current_agent": "",
        "iteration": 0,
        "vector_store_dir": None
    }
    
    print("Building reasoning chain for: Hybrid approaches are most promising")
    print()
    
    result = moderator.create_reasoning_chain(
        state=state,
        claim="Hybrid quantum-classical approaches offer the most practical path forward",
        evidence_points=[
            "NISQ devices have limited qubit counts (50-100)",
            "Classical preprocessing can reduce quantum circuit depth",
            "Demonstrated 15% accuracy improvement over pure classical methods",
            "Error mitigation techniques work better in hybrid systems",
            "Near-term implementable on current hardware"
        ]
    )
    
    dialogue = result["dialogue_exchanges"][0]
    print(f"Type: {dialogue['type']}")
    print(f"Claim: {dialogue['claim']}")
    print()
    print("--- REASONING DIALOGUE ---")
    print(dialogue['content'])
    print()


def demo_facilitated_dialogue():
    """Demonstrate facilitated dialogue"""
    print("=" * 80)
    print("🎯 DEMO 3: Facilitated Multi-Turn Dialogue")
    print("=" * 80)
    print()
    
    llm = ChatOpenAI(
        model="gpt-4-turbo-preview",
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    moderator = DialogueModerator(llm)
    
    state: AgentState = {
        "query": "Scalability challenges in quantum drug discovery",
        "papers": [],
        "research_summary": "Current quantum simulations are limited to small molecules due to qubit and coherence constraints.",
        "critique": "The gap between toy problems and drug-relevant molecules (100+ atoms) remains substantial.",
        "follow_up_questions": [],
        "synthesis": "",
        "conversation_history": [],
        "dialogue_exchanges": [],
        "current_agent": "",
        "iteration": 0,
        "vector_store_dir": None
    }
    
    print("Facilitating dialogue on: Bridging the scalability gap")
    print()
    
    result = moderator.facilitate_dialogue(
        state=state,
        topic="Can we bridge the scalability gap with near-term innovations?",
        participants=["Optimistic Analyst", "Skeptical Critic", "Pragmatic Moderator"],
        turns=4
    )
    
    dialogue = result["dialogue_exchanges"][0]
    print(f"Type: {dialogue['type']}")
    print(f"Topic: {dialogue['topic']}")
    print(f"Participants: {', '.join(dialogue['participants'])}")
    print()
    print("--- CONVERSATION ---")
    print(dialogue['content'])
    print()


def show_comparison():
    """Show before/after comparison"""
    print("=" * 80)
    print("📊 BEFORE vs AFTER: Sequential Essays vs Conversational Dialogue")
    print("=" * 80)
    print()
    
    print("❌ BEFORE (Sequential Essays):")
    print("-" * 40)
    print("""
Researcher: The literature demonstrates quantum computing's potential 
for drug discovery through molecular simulation. Papers show 15% 
improvement in accuracy...
[500 words of analysis]

Critic: However, several limitations exist. Current hardware constraints 
include limited qubit counts, high error rates, and short coherence times...
[400 words of critique]
    """)
    
    print()
    print("✅ AFTER (With Dialogue):")
    print("-" * 40)
    print("""
Researcher: [Analysis content...]

Critic: [Critique content...]

💬 Agents now engage in dialogue...

**Analyst:** "The papers show consistent 15% improvements using VQE 
for molecular ground states."

**Critic:** "But that's on 12-qubit systems with toy molecules. Does 
that scale to drug molecules with 50+ atoms?"

**Analyst:** "Fair point. Yet hybrid quantum-classical approaches 
offset some limits—classical preprocessing handles bulk complexity."

**Critic:** "True. So we're saying the *approach* is promising, but 
current hardware isn't ready?"

**Analyst:** "Exactly. The methodology shows potential, pending 
hardware advances."

**Critic:** "That's more accurate. Given that caveat, the improvement 
is still significant for proof-of-concept."
    """)
    
    print()
    print("🎯 Key Differences:")
    print("  ✓ Direct challenge-response exchanges")
    print("  ✓ Agents reference each other's points")
    print("  ✓ Visible reasoning process (not just conclusions)")
    print("  ✓ Tension → refinement → resolution")
    print("  ✓ Reads like real collaborative research")
    print()


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════╗
║        Conversational Agent Dialogue System - Demo              ║
║                                                                  ║
║  This demonstrates the new dialogue system that makes agent     ║
║  reasoning visible through conversational exchanges.            ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    print("\n📝 NOTE: This demo requires OpenAI API key in .env file")
    print()
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in environment")
        print("Please add it to your .env file:")
        print("OPENAI_API_KEY=your_key_here")
        sys.exit(1)
    
    # Show comparison first
    show_comparison()
    
    # Run demos
    try:
        demo_debate()
        print("\n⏳ Generating next demo...\n")
        
        demo_reasoning_chain()
        print("\n⏳ Generating next demo...\n")
        
        demo_facilitated_dialogue()
        
        print("=" * 80)
        print("✅ All demos completed!")
        print("=" * 80)
        print()
        print("🎯 Next Steps:")
        print("  1. Run the full workflow: streamlit run app.py")
        print("  2. Load a session and start agent analysis")
        print("  3. Observe dialogues in the 'Agent Collaboration Flow' tab")
        print("  4. Download the report to see formatted dialogues")
        print()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nThis might be due to:")
        print("  - Invalid API key")
        print("  - Network issues")
        print("  - API rate limits")
        import traceback
        print("\nFull traceback:")
        print(traceback.format_exc())

