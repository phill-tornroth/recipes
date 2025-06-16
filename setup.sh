#!/bin/bash

# Development environment setup script
set -e

echo "🚀 Setting up Recipes development environment..."

# Check if poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry not found. Please install Poetry first:"
    echo "   curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# Check if node is installed for frontend tools
if ! command -v node &> /dev/null; then
    echo "⚠️  Node.js not found. Frontend tools will not be available."
    echo "   You can install Node.js from: https://nodejs.org/"
    SKIP_FRONTEND=true
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created. Please edit it with your API keys:"
    echo "   - OPENAI_API_KEY"
    echo "   - PINECONE_API_KEY"
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
poetry install --with dev

# Install pre-commit hooks
echo "🔧 Setting up pre-commit hooks..."
poetry run pre-commit install

# Install frontend dependencies if Node.js is available
if [ "$SKIP_FRONTEND" != true ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
else
    echo "⏭️  Skipping frontend dependencies (Node.js not found)"
fi

echo ""
echo "✅ Setup complete! Next steps:"
echo ""
echo "1. Edit .env file with your API keys"
echo "2. Open the project in VSCode/Cursor:"
echo "   code recipes.code-workspace"
echo ""
echo "3. Install recommended extensions when prompted"
echo ""
echo "4. Run the application:"
echo "   make run              # Local development"
echo "   make docker-up        # Docker development"
echo ""
echo "5. Run quality checks:"
echo "   make check-all        # Format, lint, and test"
echo "   make help             # See all available commands"
echo ""
echo "Happy coding! 🎉"
