# Examples

This directory contains example scripts demonstrating different features of the Research Agent System.

## Basic Usage

Simple example showing the core workflow:

```bash
python examples/basic_usage.py
```

This script:
1. Searches for papers on "AI for climate change modeling"
2. Runs the multi-agent analysis
3. Displays abbreviated results

## Interactive Workflow

Example using the interactive workflow with refinement:

```bash
python examples/interactive_workflow.py
```

This script:
1. Searches for papers on "Quantum computing in drug discovery"
2. Runs the interactive workflow (includes refinement loop)
3. Shows the full agent conversation flow
4. Displays the refined synthesis

## Custom Topics

Modify the `query` variable in any example to analyze your own topic:

```python
query = "Your research question here"
```

### Suggested Topics

- **AI/ML**: "Transformer models for time series", "Few-shot learning techniques"
- **Physics**: "Topological quantum computing", "Dark matter detection methods"
- **Biology**: "Single-cell RNA sequencing analysis", "Protein folding predictions"
- **Chemistry**: "Catalyst design with machine learning", "Sustainable energy storage"
- **Computer Science**: "Federated learning privacy", "Graph neural networks"

## Tips

1. **Start Small**: Use 5-10 papers for initial testing
2. **Be Specific**: Narrow queries yield better results
3. **Check Output**: Review all agent outputs for quality
4. **Iterate**: Try different temperature settings for varied results

## Creating Your Own Examples

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
from ingestion.arxiv_loader import ArxivLoader
from agents.research_graph import ResearchWorkflow

load_dotenv()

# Your custom analysis code here
```

## Running Examples

Make sure you've:
1. Installed dependencies: `pip install -r requirements.txt`
2. Set up your `.env` file with `OPENAI_API_KEY`
3. Activated your virtual environment

Then run any example:

```bash
python examples/basic_usage.py
```

