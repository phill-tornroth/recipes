FROM tiangolo/uvicorn-gunicorn-fastapi:python3.10

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="/root/.local/bin:$PATH"

# Set work directory
WORKDIR /app

# Copy only the necessary files to install dependencies
COPY pyproject.toml poetry.lock ./

# Install project dependencies
RUN poetry install --no-root --no-cache

# Copy the rest of the application
COPY ./backend .

# Run the application
CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "$LOG_LEVEL"]
