# Development Guide

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd agent-queue-system
   ```

2. **Install dependencies:**
   Using `uv`:
   ```bash
   uv sync
   ```
   Or using `pip`:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   See [Configuration](CONFIGURATION.md) for details.

## Running the Server

Start the development server with hot reload:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Testing

We use `pytest` for unit and integration testing.

### Run all tests
```bash
uv run pytest
```

### Run with coverage
```bash
uv run pytest --cov=app --cov-report=html
```

### Run specific tests
```bash
# Unit tests
uv run pytest tests/unit/

# Integration tests
uv run pytest tests/integration/
```

## Code Quality

We use `black` for formatting and `ruff` for linting.

### Format code
```bash
uv run black app tests
```

### Lint code
```bash
uv run ruff check app tests
```

## Project Structure

```
src/shinzo/
├── agent/               # Agent processor module
├── api/                 # API endpoints
├── queue/               # Queue management module
├── worker/              # Background worker module
├── utils/               # Utility functions
├── main.py              # Application entry point
├── models.py            # Pydantic data models
├── config.py            # Configuration loading
└── tools.py             # Agent tools
tests/
├── unit/                # Unit tests
└── integration/         # Integration tests
docs/                    # Documentation
config/                  # Config files
.env.example             # Template for env vars
pyproject.toml           # Project dependencies
README.md                # Project overview
```

