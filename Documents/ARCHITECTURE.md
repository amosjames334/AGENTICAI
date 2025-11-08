# System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User Interface Layer                  │
│  ┌──────────────────────┐      ┌──────────────────────┐    │
│  │  Streamlit Dashboard │      │     CLI Interface     │    │
│  │      (app.py)        │      │      (cli.py)         │    │
│  └──────────┬───────────┘      └──────────┬───────────┘    │
└─────────────┼──────────────────────────────┼────────────────┘
              │                              │
              └──────────────┬───────────────┘
                             │
┌─────────────────────────────▼────────────────────────────────┐
│                   Orchestration Layer                         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │          Research Workflow (LangGraph)                 │  │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐   │  │
│  │  │ Init │→ │ Rsch │→ │ Crtc │→ │ Qstn │→ │ Synth │   │  │
│  │  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘   │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────────────┬──────────────────────────────────┘
                             │
┌─────────────────────────────▼────────────────────────────────┐
│                      Agent Layer                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│  │  Researcher  │ │    Critic    │ │   Question   │         │
│  │    Agent     │ │    Agent     │ │  Generator   │         │
│  └──────────────┘ └──────────────┘ └──────────────┘         │
│  ┌──────────────┐ ┌──────────────┐                          │
│  │ Synthesizer  │ │   Refiner    │                          │
│  │    Agent     │ │   (Optional) │                          │
│  └──────────────┘ └──────────────┘                          │
└────────────────────────────┬──────────────────────────────────┘
                             │
┌─────────────────────────────▼────────────────────────────────┐
│                    Knowledge Layer                            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│  │   Document   │ │    Vector    │ │  arXiv API   │         │
│  │  Processor   │ │    Store     │ │   Loader     │         │
│  └──────────────┘ └──────────────┘ └──────────────┘         │
└────────────────────────────┬──────────────────────────────────┘
                             │
┌─────────────────────────────▼────────────────────────────────┐
│                       LLM Layer                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              OpenAI GPT-4 API                        │    │
│  └──────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────┘
```

## Component Breakdown

### 1. User Interface Layer

#### Streamlit Dashboard (`app.py`)
- **Purpose**: Interactive web interface
- **Features**:
  - Research query input
  - Paper search and display
  - Agent workflow visualization
  - Results display and export
- **Tech**: Streamlit, Plotly
- **State Management**: Session state for persistence

#### CLI Interface (`cli.py`)
- **Purpose**: Command-line automation
- **Features**:
  - Batch processing
  - Scriptable workflows
  - File output
  - Progress logging
- **Tech**: argparse, logging
- **Output**: Console or file

### 2. Orchestration Layer

#### Research Workflow (`research_graph.py`)

**State Management**
```python
AgentState = {
    query: str              # Research question
    papers: List[Dict]      # Paper metadata
    research_summary: str   # Researcher output
    critique: str           # Critic output
    follow_up_questions: [] # Question generator output
    synthesis: str          # Synthesizer output
    conversation_history: []# Full agent conversation
    current_agent: str      # Active agent
    iteration: int         # Refinement count
}
```

**Workflow Types**

1. **Standard Workflow**
   - Linear agent chain
   - Single pass
   - Fast execution

2. **Interactive Workflow**
   - Includes refinement loop
   - Conditional routing
   - Higher quality output

**LangGraph Integration**
```python
workflow = StateGraph(AgentState)
workflow.add_node("researcher", researcher_node)
workflow.add_node("critic", critic_node)
workflow.add_node("question_generator", question_node)
workflow.add_node("synthesizer", synthesizer_node)

# Define edges
workflow.set_entry_point("researcher")
workflow.add_edge("researcher", "critic")
workflow.add_edge("critic", "question_generator")
workflow.add_edge("question_generator", "synthesizer")
workflow.add_edge("synthesizer", END)
```

### 3. Agent Layer

Each agent follows this pattern:

```python
class Agent:
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.name = "Agent Name"
        self.role = "Agent Role"
    
    @property
    def system_prompt(self) -> str:
        return "Specialized instructions..."
    
    def process(self, state: AgentState) -> Dict:
        # 1. Extract relevant state
        # 2. Create prompt
        # 3. Call LLM
        # 4. Process response
        # 5. Update state
        return updated_state
```

#### Agent Specializations

**Researcher Agent**
- Reads and summarizes papers
- Extracts key findings
- Identifies methodologies
- Notes limitations

**Critic Agent**
- Evaluates findings
- Questions assumptions
- Identifies weaknesses
- Suggests improvements

**Question Generator Agent**
- Proposes research directions
- Identifies gaps
- Suggests connections
- Generates hypotheses

**Synthesizer Agent**
- Integrates perspectives
- Creates narrative
- Provides recommendations
- Makes reasoning transparent

**Refiner Agent** (Optional)
- Iterative improvement
- Addresses critiques
- Strengthens arguments
- Polishes output

### 4. Knowledge Layer

#### arXiv Loader (`arxiv_loader.py`)

```python
class ArxivLoader:
    def search_papers(query, max_results) -> List[Dict]
    def download_paper(arxiv_id) -> Path
```

**Features**:
- Search by query
- Download PDFs
- Cache management
- Metadata extraction

#### Document Processor (`document_processor.py`)

```python
class DocumentProcessor:
    def extract_text_from_pdf(pdf_path) -> str
    def process_papers(papers) -> List[Document]
    def create_vector_store(documents) -> FAISS
    def search_documents(query, k) -> List[Document]
```

**Pipeline**:
1. Extract text from PDFs
2. Create document objects
3. Chunk text (1000 chars, 200 overlap)
4. Generate embeddings
5. Store in FAISS
6. Enable semantic search

### 5. LLM Layer

#### OpenAI Integration

**Model Configuration**
- Default: `gpt-4-turbo-preview`
- Alternative: `gpt-4`, `gpt-3.5-turbo`
- Temperature: 0.7 (configurable)

**Token Management**
- Input: ~500-2000 tokens per prompt
- Output: ~500-1500 tokens per response
- Total per analysis: ~4000-6000 tokens

**Error Handling**
- Rate limiting
- Timeout management
- Retry logic
- Fallback strategies

## Data Flow

### Research Analysis Flow

```
1. User Input
   └─> Query + Parameters

2. Paper Search
   └─> arXiv API Query
       └─> Paper Metadata

3. Document Processing (Optional)
   └─> PDF Download
       └─> Text Extraction
           └─> Vector Embeddings

4. Agent Processing
   └─> Initialize State
       └─> Researcher Agent
           └─> State Update
               └─> Critic Agent
                   └─> State Update
                       └─> Question Generator
                           └─> State Update
                               └─> Synthesizer
                                   └─> Final State

5. Output
   └─> Display Results
       └─> Export Report
```

### State Evolution

```python
# Initial State
{
    query: "AI for climate modeling",
    papers: [...],
    research_summary: "",
    critique: "",
    follow_up_questions: [],
    synthesis: "",
    conversation_history: [],
    current_agent: "",
    iteration: 0
}

# After Researcher
{
    ...,
    research_summary: "Based on analysis of 10 papers...",
    conversation_history: [{agent: "Researcher", ...}],
    current_agent: "Researcher"
}

# After Critic
{
    ...,
    critique: "Key strengths include... However...",
    conversation_history: [..., {agent: "Critic", ...}],
    current_agent: "Critic"
}

# After Question Generator
{
    ...,
    follow_up_questions: ["How does X...", "What about Y..."],
    conversation_history: [..., {agent: "Questions", ...}],
    current_agent: "Question Generator"
}

# Final State
{
    ...,
    synthesis: "Integrating all perspectives...",
    conversation_history: [..., {agent: "Synthesizer", ...}],
    current_agent: "Synthesizer",
    iteration: 0
}
```

## Extension Points

### Adding New Agents

1. Create agent class in `agent_definitions.py`
2. Define system prompt
3. Implement `process()` method
4. Add node to workflow graph
5. Define edges/routing logic

### Adding New Data Sources

1. Create loader in `ingestion/`
2. Implement search interface
3. Integrate with `DocumentProcessor`
4. Add UI controls

### Custom Workflows

1. Extend `ResearchWorkflow`
2. Override `_build_graph()`
3. Define custom routing logic
4. Add conditional edges

### Tool Integration

1. Create tool functions in `tools/`
2. Register with agents
3. Update state schema if needed
4. Add to agent prompts

## Performance Considerations

### Optimization Strategies

**Caching**
- Paper PDFs cached locally
- Vector stores persisted
- API responses logged

**Parallel Processing**
- Multiple paper processing
- Batch embedding generation
- Concurrent API calls (future)

**Token Optimization**
- Chunk size tuning
- Prompt compression
- Response length limits

**Error Recovery**
- Graceful degradation
- Partial results
- Retry strategies

## Security Considerations

### API Key Management
- Environment variables
- Never in code
- .gitignore protection

### Input Validation
- Query sanitization
- Parameter bounds
- Type checking

### Output Sanitization
- Markdown escaping
- Safe file operations
- Path validation

## Monitoring and Logging

### Logging Levels
- INFO: Normal operations
- WARNING: Degraded performance
- ERROR: Failures
- DEBUG: Detailed tracing

### Tracked Metrics
- Agent execution time
- Token usage
- API calls
- Error rates
- Cache hit rates

## Future Architecture

### Planned Enhancements

**Scalability**
- Distributed agent execution
- Load balancing
- Caching layer (Redis)

**Intelligence**
- Agent learning/memory
- Dynamic agent selection
- Conversation branching

**Integration**
- More data sources
- Export formats
- Reference managers
- Collaboration features

---

This architecture provides a solid foundation for collaborative AI research while maintaining flexibility for future enhancements.

