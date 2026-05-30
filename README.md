# 🔬 Research Reasoning Agent

### Agentic AI for Accelerated Research — powered by Claude + MCP

An autonomous research agent that **reasons for itself**. Instead of a fixed
`A → B → C → D` pipeline, a single ReAct-style agent decides *what to think
about, which tools to call, and when it has gathered enough evidence* — then
synthesizes a grounded, well-reasoned answer. It searches your ingested research
papers (local FAISS vector store) and the live web (Brave Search via MCP), and
streams its full reasoning flow to the UI in real time.

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-ReAct-green.svg)
![Claude](https://img.shields.io/badge/Anthropic-Claude-orange.svg)
![MCP](https://img.shields.io/badge/MCP-Brave_Search-purple.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-red.svg)

---

## 🎯 What it does

1. **Ingests knowledge** — searches arXiv, downloads PDFs, and builds a local
   FAISS vector store with sentence-transformer embeddings.
2. **Reasons autonomously** — a Claude-powered ReAct agent thinks step by step,
   chooses tools, gathers evidence, critiques weak claims, and iterates until it
   is confident.
3. **Synthesizes** — produces a thorough synthesis, follow-up research
   questions, and a collective insight report with a testable hypothesis and a
   confidence level.
4. **Shows its work** — the agent's thinking, tool calls, tool results, and
   run statistics stream live to the dashboard.

---

## ✨ Key Features

### 🧠 Autonomous reasoning (not a fixed chain)
- Single **ReAct agent** built on LangGraph's `create_react_agent` that plans,
  acts, and observes in a loop — deciding its own path rather than following
  hard-coded steps.
- Structured final output (`synthesis`, `follow_up_questions`, `insight_report`)
  via Pydantic-typed responses.

### 💸 Tiered model strategy (cost & rate-limit aware)
- **Claude Haiku** drives the cheap, fast reasoning/tool-calling loop.
- **Claude Sonnet** is used **only** for the final high-quality synthesis.
- Tuned `recursion_limit`, `max_tokens`, and trimmed context to stay within
  Anthropic rate limits.

### 🛠️ Tools the agent can call
- **`vector_store_search`** — semantic retrieval over your ingested papers
  (FAISS + sentence-transformers).
- **Brave Search (via MCP)** — live web search through the official
  `@modelcontextprotocol/server-brave-search` MCP server, spawned over stdio
  with `npx`. Degrades gracefully if Node.js or `BRAVE_API_KEY` is missing.

### 📡 Live reasoning stream + run statistics
- The Streamlit UI shows the agent's reasoning **as it happens** (thinking
  steps, tool calls, tool results, phase transitions) via a background thread +
  thread-safe queue.
- End-of-run **stats**: total duration, number of reasoning steps, which tools
  were used and how many times, and which models ran.

### 💾 Session management & persistence
- Multiple named research sessions, each with its own papers, vector store, and
  saved results under `data/sessions/<id>/`.
- Switch between sessions, re-run analysis, and reload previous results across
  app restarts (persisted to `results.json`).

### 🖥️ Two interfaces
- **Streamlit dashboard** (`app.py`) — full visual workflow.
- **CLI** (`cli.py`) — scriptable session, ingestion, query, and research
  commands.

---

## 🏗️ Architecture

```
                         ┌──────────────────────────┐
                         │  Streamlit UI / CLI       │
                         │  (sessions, live stream)  │
                         └────────────┬─────────────┘
                                      │
                         ┌────────────▼─────────────┐
                         │   ResearchWorkflow        │
                         │   (research_graph.py)     │
                         └────────────┬─────────────┘
                                      │ delegates
                         ┌────────────▼─────────────┐
                         │   ReasoningAgent (ReAct)  │
                         │   reasoning_agent.py      │
                         │                           │
                         │  Phase 1: Haiku loop      │
                         │   think → act → observe   │
                         │  Phase 2: Sonnet synth    │
                         └───┬───────────────────┬───┘
                             │                   │
              ┌──────────────▼──┐        ┌───────▼───────────────┐
              │ vector_store_   │        │ Brave Search (MCP)    │
              │ search (FAISS)  │        │ via npx + stdio       │
              └─────────────────┘        └───────────────────────┘
```

**Reasoning loop:** `THINK → ACT (call a tool) → OBSERVE (read result) → repeat`
until the agent has enough evidence, then a single Sonnet call produces the
structured final answer.

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.9+**
- **Anthropic API key** ([console.anthropic.com](https://console.anthropic.com))
- *(Optional)* **Brave Search API key** ([brave.com/search/api](https://brave.com/search/api/))
  and **Node.js** (provides `npx`) — only needed to enable live web search.

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Create a `.env` file in the project root:

```ini
# Required
ANTHROPIC_API_KEY=sk-ant-your-actual-api-key-here
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
ANTHROPIC_TEMPERATURE=0.7

# Optional — enables the Brave Search MCP tool
BRAVE_API_KEY=your-brave-search-api-key-here
```

### 3. Run the dashboard

```bash
streamlit run app.py
```

Open `http://localhost:8501`.

---

## 📖 Usage

### Streamlit dashboard

1. **Create / select a session** in the sidebar.
2. **Search arXiv** for a topic and pick the papers to ingest.
3. **Process papers** — PDFs are downloaded and embedded into the session's
   FAISS vector store.
4. **Run Agent Analysis** — watch the agent reason live: its thinking, each tool
   call (vector store / Brave), the results it observes, and the final synthesis.
5. **Review results** — synthesis, follow-up questions, insight report, and run
   statistics. Re-run anytime; results persist per session.

### Command line

```bash
# Create a new session
python cli.py new "Quantum error correction"

# List / load / delete sessions
python cli.py list
python cli.py load <session_id>
python cli.py delete <session_id>

# Download papers and build the vector store
python cli.py ingest "quantum error correction" --max-papers 10

# Query the vector store directly
python cli.py query "what threshold theorems exist?"

# Run the full reasoning agent
python cli.py research "How mature is fault-tolerant quantum computing?"
```

The default model is `claude-sonnet-4-5-20250929`; override with `--model`.

---

## 🧰 Tech Stack

| Layer            | Technology |
|------------------|------------|
| Reasoning agent  | LangGraph `create_react_agent`, LangChain |
| LLM provider     | Anthropic Claude (Haiku for reasoning, Sonnet for synthesis) |
| Tool protocol    | Model Context Protocol (MCP) via `langchain-mcp-adapters` |
| Web search       | Brave Search MCP server (`@modelcontextprotocol/server-brave-search`) |
| Vector store     | FAISS + `sentence-transformers` embeddings |
| Ingestion        | arXiv API, PyPDF |
| UI               | Streamlit + Plotly |
| Config / data    | python-dotenv, Pydantic, JSON session persistence |

---

## 📁 Project Structure

```
AGENTICAI/
├── app.py                          # Streamlit dashboard (live reasoning stream)
├── cli.py                          # Command-line interface
├── requirements.txt                # Dependencies
├── .env                            # API keys (not committed)
├── data/                           # Sessions, papers, vector stores (gitignored)
│   └── sessions/<id>/
│       ├── papers/                 # Downloaded PDFs
│       ├── vector_store/           # FAISS index
│       ├── session.json            # Session metadata
│       └── results.json            # Persisted agent run results
├── src/
│   ├── agents/
│   │   ├── reasoning_agent.py      # Claude ReAct agent (tiered, streaming)
│   │   ├── research_graph.py       # Workflow orchestration / delegation
│   │   └── agent_definitions.py    # Shared utilities & reference agents
│   ├── tools/
│   │   └── brave_search.py         # Brave Search via MCP (npx + stdio)
│   ├── ingestion/
│   │   ├── arxiv_loader.py         # arXiv search + PDF download
│   │   └── document_processor.py   # Text extraction & embeddings
│   ├── DataPipeline/preprocessing/ # Text cleaning & chunking
│   └── utils/
│       ├── config.py               # Configuration management
│       ├── session_manager.py      # Session + results persistence
│       └── logger.py
├── examples/                       # Usage examples
└── test_setup.py                   # Environment verification
```

---

## 🔧 Configuration

| Variable               | Required | Default                         | Description |
|------------------------|----------|---------------------------------|-------------|
| `ANTHROPIC_API_KEY`    | ✅       | —                               | Claude API key |
| `ANTHROPIC_MODEL`      | ✅       | `claude-sonnet-4-5-20250929`    | Synthesis model |
| `ANTHROPIC_TEMPERATURE`| ❌       | `0.7`                           | Sampling temperature |
| `BRAVE_API_KEY`        | ✅       | —                               | Enables Brave Search MCP tool |
| `DEFAULT_MAX_PAPERS`   | ❌       | `10`                            | Default arXiv result count |

> **Note:** Without `BRAVE_API_KEY` (or Node.js / `npx`), the agent still runs
> fully on the local vector store — web search is simply skipped.

---

## 🐛 Troubleshooting

| Issue | Fix |
|-------|-----|
| `ANTHROPIC_API_KEY is not set` | Add a valid key to `.env`. |
| Rate limit (`429`) errors | Tiered models already mitigate this; reduce papers/queries or upgrade your Anthropic tier. |
| Brave Search not used | Set `BRAVE_API_KEY` **and** install Node.js so `npx` is available. |
| Import / dependency errors | `pip install -r requirements.txt` (pins `torch`, `transformers`, `sentence-transformers` for compatibility). |
| arXiv search fails | Check your connection and try fewer papers. |

---

## 📝 License

MIT License — free to use and modify.

## 🙏 Acknowledgments

- **Anthropic Claude** — reasoning and synthesis
- **LangChain / LangGraph** — agent orchestration
- **Model Context Protocol & Brave Search** — live web tooling
- **arXiv** — open-access research papers
- **Streamlit** — rapid UI
