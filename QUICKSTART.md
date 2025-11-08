# 🚀 Quick Start Guide

Get up and running with Research Agent System in 5 minutes!

## Prerequisites

- Python 3.9+
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))

## Installation (3 steps)

### 1. Setup

```bash
cd AgenticAI
./setup.sh
```

This will:
- Create a virtual environment
- Install all dependencies
- Set up data directories
- Create a `.env` template

### 2. Configure API Key

Edit the `.env` file and add your OpenAI API key:

```bash
OPENAI_API_KEY=sk-your-actual-api-key-here
```

### 3. Run!

**Option A: Web Interface (Recommended)**

```bash
source venv/bin/activate
streamlit run app.py
```

Then open your browser to `http://localhost:8501`

**Option B: Command Line**

```bash
source venv/bin/activate
python cli.py "AI for climate modeling" --max-papers 10
```

## First Research Query

### Using the Web Interface

1. Enter a research question:
   - "Quantum computing applications in cryptography"
   - "CRISPR gene editing advances"
   - "AI for protein folding"

2. Click "Search Papers" (wait ~10 seconds)

3. Review the papers found

4. Click "Start Agent Analysis" (wait ~2-3 minutes)

5. Watch the agents collaborate in the "Agent Collaboration" tab

6. View results in the "Results" tab

7. Download the report!

### Using the CLI

```bash
# Basic usage
python cli.py "your research question"

# With options
python cli.py "AI for climate modeling" \
  --max-papers 15 \
  --model gpt-4 \
  --output my_report.md
```

## Example Queries

### Technology
```
- "Transformer architectures for time series prediction"
- "Federated learning privacy mechanisms"
- "Edge computing for IoT applications"
```

### Science
```
- "CRISPR applications in agriculture"
- "Graphene applications in energy storage"
- "Dark matter detection methods"
```

### AI/ML
```
- "Few-shot learning in computer vision"
- "Explainable AI techniques"
- "Reinforcement learning for robotics"
```

## Understanding Results

### Agent Roles

- **🔍 Researcher**: Analyzes and summarizes papers
- **🎯 Critic**: Evaluates findings and identifies gaps
- **❓ Question Generator**: Creates follow-up questions
- **🧩 Synthesizer**: Integrates everything into a coherent report

### Output Sections

1. **Research Summary**: Overview of key findings
2. **Critical Analysis**: Limitations and concerns
3. **Follow-up Questions**: Future research directions
4. **Synthesis**: Integrated insights and recommendations

## Tips for Best Results

### ✅ Do
- Use specific, focused queries
- Start with 5-10 papers for testing
- Use GPT-4 for best quality
- Review the agent conversation flow

### ❌ Avoid
- Very broad queries ("AI" or "physics")
- Too many papers (>20) on first try
- Very niche topics with few papers
- Extremely recent topics (<1 week old)

## Common Issues

### "No papers found"
- Try a broader query
- Check your spelling
- Try alternative keywords

### "API Key Error"
- Verify your `.env` file has the correct key
- Check the key is valid at platform.openai.com
- Ensure no extra spaces in the `.env` file

### "Import errors"
- Run: `pip install -r requirements.txt`
- Ensure virtual environment is activated
- Try: `python3` instead of `python`

### Slow performance
- Use fewer papers (5-10)
- Try `gpt-3.5-turbo` model (faster, less sophisticated)
- Check your internet connection

## Next Steps

- Try the example scripts in `examples/`
- Read the full README.md for advanced features
- Check CONTRIBUTING.md to add features
- Experiment with different agent configurations

## Need Help?

- Check the full [README.md](README.md)
- Review [examples/](examples/)
- Open an issue on GitHub

## Ready to Go! 🎉

You're all set! Start researching:

```bash
streamlit run app.py
```

or

```bash
python cli.py "your fascinating research question"
```

Happy researching! 🔬✨

