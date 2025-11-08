#!/bin/bash

# Setup script for Research Agent System

echo "🔬 Research Agent System - Setup"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 )
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then 
    echo "❌ Error: Python $required_version or higher is required"
    echo "   Current version: $python_version"
    exit 1
fi
echo "✅ Python version: $python_version"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
echo "✅ Virtual environment created"
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip -q
echo "✅ pip upgraded"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt -q
echo "✅ Dependencies installed"
echo ""

# Create data directories
echo "Creating data directories..."
mkdir -p data/papers data/cache data/vector_store
echo "✅ Data directories created"
echo ""

# Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  No .env file found"
    echo "Creating .env from template..."
    
    echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
    echo "OPENAI_MODEL=gpt-4-turbo-preview" >> .env
    echo "OPENAI_TEMPERATURE=0.7" >> .env
    
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your OpenAI API key!"
    echo ""
else
    echo "✅ .env file found"
    echo ""
fi

# Done
echo "=================================="
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your OPENAI_API_KEY"
echo "2. Run: source venv/bin/activate"
echo "3. Run: streamlit run app.py"
echo ""
echo "Or use the CLI:"
echo "  python cli.py \"your research query\""
echo ""
echo "=================================="

