# Recipes Project

## Table of Contents

- [Introduction](#introduction)
- [Requirements](#requirements)
- [Installation](#installation)
  - [Python Version Management](#python-version-management)
  - [Dependency Management](#dependency-management)
  - [Running the Project](#running-the-project)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Introduction

Welcome to the Recipes Project! This project aims to provide a collection of delicious recipes.

## Requirements

- Python 3.13
- Poetry
- Docker and Docker Compose

## Installation

### Quick Setup

For a complete development environment setup, run:

```sh
./setup.sh
```

This script will:
- Create `.env` file from template
- Install Python and Node.js dependencies
- Set up pre-commit hooks
- Provide next steps

### Manual Setup

#### Environment Setup

1. Copy the example environment file:
```sh
cp .env.example .env
```

2. Edit `.env` and fill in your API keys:
```sh
# Required API keys
OPENAI_API_KEY=your_actual_openai_api_key
PINECONE_API_KEY=your_actual_pinecone_api_key
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

To build and run the project using Docker Compose, execute:

```sh
docker-compose up --build
```

**Note:** Make sure you have set up your `.env` file with valid API keys before running the project.

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
