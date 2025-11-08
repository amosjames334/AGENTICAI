# 🔬 Research Agent System

### Agentic AI for Accelerated Research

A sophisticated multi-agent system that collaborates to analyze research papers, generate insights, and explain reasoning in a clear, verifiable way. Built with LangGraph and powered by advanced LLMs.

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![LangChain](https://img.shields.io/badge/LangChain-latest-green.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-latest-red.svg)

## 🎯 Overview

The Research Agent System creates a mini research lab powered by AI agents, where specialized agents work together to:

- 📚 **Ingest Knowledge**: Search and parse research papers from arXiv
- 🔍 **Research**: Analyze and summarize key findings and methodologies
- 🎯 **Critique**: Evaluate findings and identify limitations
- ❓ **Question**: Generate follow-up research questions
- 🧩 **Synthesize**: Integrate insights into coherent reports

**Think of it as a collaborative research team, where agents think better together than alone.**

## ✨ Features

### Core Capabilities

- **Multi-Agent Collaboration**: 4+ specialized agents working in concert
- **Knowledge Ingestion**: Automatic paper search and parsing from arXiv
- **Reasoning Chain**: Transparent agent-to-agent conversation flow
- **Interactive Workflow**: Optional refinement loops for iterative improvement
- **Rich Visualization**: Streamlit dashboard showing agent interactions
- **Exportable Reports**: Download comprehensive research analyses

### Agent Roles

1. **🔍 Researcher Agent**
   - Reads and summarizes research papers
   - Extracts key findings and methodologies
   - Identifies novel contributions

2. **🎯 Critic Agent**
   - Critically evaluates findings
   - Identifies weaknesses and gaps
   - Questions assumptions

3. **❓ Question Generator Agent**
   - Proposes follow-up research directions
   - Identifies unexplored areas
   - Suggests interdisciplinary connections

4. **🧩 Synthesizer Agent**
   - Integrates all perspectives
   - Creates coherent narratives
   - Provides actionable recommendations

5. **⚡ Refiner Agent** (Interactive mode)
   - Iteratively improves outputs
   - Addresses concerns from critique
   - Polishes final synthesis

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- OpenAI API key

### Installation

1. **Clone the repository**

```bash
cd AgenticAI
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Set up environment variables**

Create a `.env` file in the root directory:

```bash
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4-turbo-preview  # Optional
OPENAI_TEMPERATURE=0.7             # Optional
```

### Running the Application

Launch the Streamlit dashboard:

```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

## 📖 Usage Guide

### 1. Enter Research Query

Start by entering a research question or topic:

```
Examples:
- "AI for climate change modeling"
- "Quantum computing applications in cryptography"
- "CRISPR gene editing advances"
- "Battery efficiency improvements"
```

### 2. Search Papers

- Adjust the number of papers to search (5-20)
- Click "Search Papers" to fetch from arXiv
- Review the found papers

### 3. Run Agent Analysis

- Click "Start Agent Analysis"
- Watch agents collaborate in real-time
- View the conversation flow in the "Agent Collaboration" tab

### 4. Review Results

- Check the "Results" tab for the final synthesis
- Review follow-up research questions
- Download the complete report

## 🏗️ Architecture

### Project Structure

```
AgenticAI/
├── app.py                          # Streamlit UI
├── requirements.txt                # Dependencies
├── .env                           # Environment variables
├── data/
│   ├── papers/                    # Cached paper PDFs
│   ├── cache/                     # Processing cache
│   └── vector_store/              # Vector embeddings
├── src/
│   ├── agents/
│   │   ├── agent_definitions.py   # Agent classes and prompts
│   │   └── research_graph.py      # LangGraph workflow
│   ├── ingestion/
│   │   ├── arxiv_loader.py       # arXiv integration
│   │   └── document_processor.py  # Document parsing
│   ├── tools/                     # Agent tools
│   └── utils/                     # Utility functions
└── README.md
```

### Technology Stack

- **LLM Framework**: LangChain + LangGraph
- **Vector Store**: FAISS
- **Document Processing**: PyPDF, arXiv API
- **UI**: Streamlit + Plotly
- **LLM Provider**: OpenAI (GPT-4)

### Agent Workflow

```
┌─────────────┐
│   Query     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Researcher  │──► Analyzes papers, creates summary
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Critic    │──► Evaluates findings, identifies gaps
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Questions  │──► Generates follow-up questions
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Synthesizer │──► Creates final integrated report
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Results   │
└─────────────┘
```

## 🎓 Example Use Cases

### Climate Research

**Query**: "AI applications in climate change prediction"

**Outcome**: 
- Summary of recent ML approaches for climate modeling
- Critical analysis of model limitations
- Questions about data quality and long-term predictions
- Synthesis connecting research to policy implications

### Medical Research

**Query**: "CRISPR gene editing therapeutic applications"

**Outcome**:
- Overview of clinical trials and techniques
- Critique of safety concerns and ethical considerations
- Questions about delivery mechanisms and off-target effects
- Integrated view of current state and future directions

### Technology Research

**Query**: "Quantum computing for optimization problems"

**Outcome**:
- Analysis of quantum algorithms and hardware progress
- Critical evaluation of scalability challenges
- Questions about practical applications and error correction
- Synthesis of near-term vs long-term prospects

## 🔧 Configuration

### Model Selection

Choose different OpenAI models via the sidebar:
- `gpt-4-turbo-preview` (recommended, most capable)
- `gpt-4` (reliable, slower)
- `gpt-3.5-turbo` (faster, less sophisticated)

### Temperature

Adjust response creativity (0.0 = deterministic, 1.0 = creative):
- **Low (0.1-0.3)**: Factual, consistent analysis
- **Medium (0.5-0.7)**: Balanced (recommended)
- **High (0.8-1.0)**: Creative, exploratory

### Workflow Type

- **Standard**: Single-pass analysis (faster)
- **Interactive**: Includes refinement loop (more thorough)

## 🧪 Advanced Features

### Custom Research Topics

You can focus on narrow, specific topics for deeper analysis:

```python
# Example: Focus on a specific paper
papers = arxiv_loader.search_papers(
    query="arxiv:2301.12345",
    max_results=1
)
```

### Vector Store Search

For large document sets, enable semantic search:

```python
processor = DocumentProcessor()
vector_store = processor.create_vector_store(documents)
relevant_chunks = processor.search_documents(query, k=10)
```

### Custom Agents

Add your own specialized agents:

```python
class DataAnalystAgent:
    def __init__(self, llm):
        self.llm = llm
        self.name = "Data Analyst"
    
    def process(self, state):
        # Your custom logic
        pass
```

## 📊 Performance Tips

1. **Start Small**: Begin with 5-10 papers to test
2. **Narrow Topics**: Specific queries yield better results
3. **Use GPT-4**: More capable reasoning and synthesis
4. **Cache Results**: Vector stores are saved for reuse
5. **Batch Processing**: Process multiple related queries together

## 🤝 Contributing

This is a hackathon project, but contributions are welcome!

### Ideas for Enhancement

- [ ] Support for additional paper sources (Semantic Scholar, PubMed)
- [ ] PDF upload functionality
- [ ] Multi-language support
- [ ] Agent memory and learning
- [ ] Export to various formats (PDF, LaTeX)
- [ ] Real-time collaboration features
- [ ] Integration with reference managers

## 📝 License

MIT License - feel free to use and modify!

## 🙏 Acknowledgments

- **LangChain & LangGraph**: Multi-agent framework
- **OpenAI**: LLM capabilities
- **arXiv**: Open access to research papers
- **Streamlit**: Rapid UI development

## 🐛 Troubleshooting

### Common Issues

**API Key Error**
```
Solution: Ensure .env file has valid OPENAI_API_KEY
```

**Import Errors**
```
Solution: pip install -r requirements.txt
```

**arXiv Search Fails**
```
Solution: Check internet connection, try fewer papers
```

**Memory Issues**
```
Solution: Reduce number of papers or use gpt-3.5-turbo
```

## 📧 Contact

For questions or feedback about this project, please open an issue on GitHub.

---

**Built for the VC Big Bets Track - Agentic AI Challenge** 🚀

*Demonstrating how AI agents can collaborate to push understanding forward, thinking better together than alone.*

