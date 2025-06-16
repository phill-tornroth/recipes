# Recipe Assistant

A multi-user recipe management application with AI-powered chat assistance, built with FastAPI, PostgreSQL, Pinecone, and OpenAI.

## Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Installation](#installation)
  - [Google OAuth Setup](#google-oauth-setup)
  - [Manual Installation](#manual-installation)
- [Development](#development)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Introduction

Recipe Assistant is an AI-powered recipe management application that allows multiple users to:
- Store and organize their personal recipe collections
- Chat with an AI assistant for cooking help and recipe suggestions
- Upload images and URLs to get recipe information
- Search through their recipes using vector similarity

## Features

- **Multi-user support** with Google OAuth authentication
- **AI-powered chat** using OpenAI GPT-4o for recipe assistance
- **Vector search** through recipes using Pinecone
- **Image uploads** for recipe recognition and analysis
- **URL extraction** for importing recipes from websites
- **Voice input** support (Chrome/Arc browsers)
- **Real-time chat** interface with markdown support

## Requirements

- Python 3.13
- Poetry (Python dependency management)
- Docker and Docker Compose
- Google Cloud Console account (for OAuth)
- OpenAI API key
- Pinecone API key

## Quick Start

**🚀 Fastest way to get started:**

```bash
# 1. Clone and navigate to the project
git clone <your-repo-url>
cd recipes

# 2. Run the automated setup script
./scripts/setup-dev.sh

# 3. Follow the printed instructions to set up Google OAuth
# 4. Update your .env file with the OAuth credentials
# 5. Choose your workflow:

# Option A: Full Docker (recommended for first-time)
docker-compose up --build

# Option B: Development server (faster for development)
docker-compose up -d postgres
poetry run python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Installation

### Google OAuth Setup

**Required for authentication to work:**

1. **Create Google OAuth Application:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the "Google Identity API" or "Google+ API"
   - Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
   - Application type: "Web application"
   - Name: "Recipe Assistant Local Dev"
   - Authorized redirect URIs: `http://localhost:8000/auth/google/callback`

2. **Get your credentials:**
   - Copy the Client ID and Client Secret
   - Add them to your `.env` file (see below)

### Manual Installation

#### Environment Setup

1. Copy the example environment file:
```sh
cp .env.example .env
```

2. Edit `.env` and fill in all required values:
```sh
# Required API keys
OPENAI_API_KEY=your_actual_openai_api_key
PINECONE_API_KEY=your_actual_pinecone_api_key

# Google OAuth (required for authentication)
GOOGLE_CLIENT_ID=your_google_client_id_from_console
GOOGLE_CLIENT_SECRET=your_google_client_secret
SECRET_KEY=generate_a_long_random_string_for_jwt_signing

# Generate a secure JWT secret key:
# openssl rand -base64 32
```

### Python Version Management

First, ensure you have `pyenv` installed. Then, install Python 3.13:

```sh
pyenv install 3.13.0
pyenv local 3.13.0
```

### Dependency Management

Install Poetry using pip:

```sh
pip install poetry
```

Install the project dependencies:

```sh
poetry install
```

### Running the Project

Choose between two workflows:

#### Option A: Full Docker Setup (Recommended for first-time setup)

```bash
# Everything runs in containers - simpler, more isolated
docker-compose up --build
```

**Pros:** Simple, isolated, closer to production  
**Cons:** Slower rebuilds, less convenient for development

#### Option B: Hybrid Development (Recommended for active development)

```bash
# Database in Docker, FastAPI locally for hot reload
docker-compose up -d postgres
poetry run python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Pros:** Fast hot reload, better debugging, IDE integration  
**Cons:** Need Poetry locally, more setup

**Note:** Make sure you have set up your `.env` file with all required API keys and OAuth credentials before running the project.

**💡 Database initialization is automatic** - PostgreSQL will run the SQL files in `database/initialization/` on first startup.

### Testing the Application

1. Open your browser to `http://localhost:8000`
2. Click "Sign in with Google"
3. Complete the OAuth flow
4. Start chatting with the recipe assistant!

**Troubleshooting:**
- If OAuth fails, check your Google Cloud Console redirect URI matches exactly: `http://localhost:8000/auth/google/callback`
- If database connection fails, ensure PostgreSQL is running: `docker-compose up -d postgres`
- If API calls fail, verify your OpenAI and Pinecone API keys in `.env`

## Development

### Development Dependencies

Install development dependencies:

```sh
make install-dev
```

### Code Quality Tools

Format code:
```sh
make format
```

Run linting:
```sh
make lint
```

Run tests:
```sh
make test
```

Run tests with coverage:
```sh
make test-cov
```

Run all checks:
```sh
make check-all
```

### Pre-commit Hooks

Set up pre-commit hooks to automatically format and lint code:

```sh
make setup-pre-commit
```

### Frontend Development

Install Node.js dependencies:
```sh
npm install
```

Format frontend code:
```sh
npm run format
```

Lint frontend code:
```sh
npm run lint
```

### Available Make Commands

Run `make help` to see all available commands.

### VSCode/Cursor Setup

The project includes VSCode/Cursor configuration for seamless development:

1. **Install recommended extensions** - VSCode will prompt you to install recommended extensions when you open the project
2. **Format on save** - Black and Prettier will automatically format your code when you save
3. **Integrated linting** - Flake8, mypy, and ESLint will show errors and warnings inline
4. **Debugging** - Pre-configured debug configurations for FastAPI and tests
5. **Tasks** - Use Ctrl/Cmd+Shift+P → "Tasks: Run Task" to access:
   - Format Python Code
   - Lint Python Code  
   - Run Tests
   - Run Tests with Coverage
   - Check All
   - Start Development Server
   - Docker: Build and Up

**Key shortcuts:**
- `Ctrl/Cmd+Shift+P` → "Python: Select Interpreter" → Choose `.venv/bin/python`
- `F5` - Start debugging FastAPI server
- `Ctrl/Cmd+Shift+P` → "Tasks: Run Task" - Access development tasks

## Usage

Instructions on how to use the project will go here.

## Contributing

Guidelines for contributing to the project will go here.

## License

Information about the project's license will go here.
