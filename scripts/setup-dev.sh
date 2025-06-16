#!/bin/bash

# Recipe App - Development Environment Setup
# This script sets up your local development environment

set -e  # Exit on any error

echo "🍳 Recipe Assistant - Development Setup"
echo "======================================="

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Please run this script from the root directory of the recipe app"
    exit 1
fi

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry is not installed. Please install Poetry first:"
    echo "   curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✅ Prerequisites check passed"
echo ""

# Install Python dependencies for local development
echo "📦 Installing Python dependencies..."
poetry install

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Update .env with your actual values before running the app!"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. 🔐 Set up Google OAuth (REQUIRED):"
echo "   • Go to https://console.cloud.google.com/"
echo "   • Create/select a project"
echo "   • Enable 'Google Identity API'"
echo "   • Create OAuth 2.0 Client ID credentials"
echo "   • Add redirect URI: http://localhost:8000/auth/google/callback"
echo ""
echo "2. 📝 Update your .env file with:"
echo "   • GOOGLE_CLIENT_ID=your_client_id_from_google"
echo "   • GOOGLE_CLIENT_SECRET=your_client_secret_from_google"
echo "   • SECRET_KEY=\$(openssl rand -base64 32)  # Generate a secure key"
echo "   • OPENAI_API_KEY=your_openai_key"
echo "   • PINECONE_API_KEY=your_pinecone_key"
echo ""
echo "3. 🚀 Choose how to run the application:"
echo ""
echo "   Option A - Full Docker (recommended for first-time setup):"
echo "   docker-compose up --build"
echo ""
echo "   Option B - Development server (faster for development):"
echo "   docker-compose up -d postgres  # Start database only"
echo "   poetry run python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "4. 🌐 Visit http://localhost:8000 and test the Google login!"
echo ""
echo "💡 Pro tip: The database will automatically initialize when PostgreSQL starts."
