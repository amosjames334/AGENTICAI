# Contributing to Research Agent System

Thank you for your interest in contributing! This project was created for a hackathon but welcomes improvements and extensions.

## Getting Started

1. Fork the repository
2. Clone your fork
3. Create a feature branch
4. Make your changes
5. Test thoroughly
6. Submit a pull request

## Development Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/AgenticAI.git
cd AgenticAI

# Run setup
./setup.sh

# Activate virtual environment
source venv/bin/activate

# Install dev dependencies (optional)
pip install pytest black flake8
```

## Project Structure

```
AgenticAI/
├── src/
│   ├── agents/        # Agent definitions and workflow
│   ├── ingestion/     # Document processing
│   ├── tools/         # Agent tools
│   └── utils/         # Utilities
├── examples/          # Example scripts
├── app.py            # Streamlit UI
└── cli.py            # CLI interface
```

## Adding New Features

### Adding a New Agent

1. Create agent class in `src/agents/agent_definitions.py`:

```python
class YourAgent:
    def __init__(self, llm):
        self.llm = llm
        self.name = "Your Agent"
        self.role = "Your Role"
    
    @property
    def system_prompt(self) -> str:
        return "Your agent's system prompt..."
    
    def process(self, state: AgentState) -> Dict:
        # Your processing logic
        pass
```

2. Add node to workflow in `src/agents/research_graph.py`
3. Update the graph edges
4. Test thoroughly

### Adding a New Data Source

1. Create loader in `src/ingestion/`:

```python
class YourLoader:
    def search(self, query: str) -> List[Dict]:
        # Implement search logic
        pass
    
    def load(self, document_id: str) -> str:
        # Implement loading logic
        pass
```

2. Integrate with `DocumentProcessor`
3. Add UI controls in `app.py`

### Adding New Tools

Create tool functions in `src/tools/` and register them with agents.

## Code Style

- Follow PEP 8
- Use type hints
- Add docstrings to all public functions
- Keep functions focused and small

```python
def example_function(param: str) -> Dict:
    """
    Brief description of function
    
    Args:
        param: Description of parameter
        
    Returns:
        Description of return value
    """
    pass
```

## Testing

```bash
# Run tests (if implemented)
pytest

# Check code style
flake8 src/
black --check src/
```

## Ideas for Contributions

### High Priority
- [ ] Add more data sources (Semantic Scholar, PubMed)
- [ ] Implement PDF upload functionality
- [ ] Add more agent types (Data Analyst, Visualizer)
- [ ] Improve error handling
- [ ] Add unit tests

### Medium Priority
- [ ] Multi-language support
- [ ] Export to PDF/LaTeX
- [ ] Agent memory system
- [ ] Conversation branching
- [ ] Real-time streaming

### Nice to Have
- [ ] Integration with reference managers (Zotero, Mendeley)
- [ ] Social features (share analyses)
- [ ] Custom agent builder UI
- [ ] Mobile-responsive design
- [ ] Dark mode

## Pull Request Guidelines

1. **Description**: Clearly describe what your PR does
2. **Testing**: Include evidence of testing
3. **Documentation**: Update README/docs if needed
4. **Code Quality**: Follow style guidelines
5. **Scope**: Keep PRs focused on one feature/fix

## Questions?

Open an issue for:
- Feature requests
- Bug reports
- Questions about implementation
- Ideas for improvement

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Acknowledgments

Contributors will be acknowledged in the README.

Thank you for helping make this project better! 🚀

