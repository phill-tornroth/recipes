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

### Environment Setup

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

## Usage

Instructions on how to use the project will go here.

## Contributing

Guidelines for contributing to the project will go here.

## License

Information about the project's license will go here.
