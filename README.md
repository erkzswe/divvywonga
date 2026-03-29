# DivvyWonga

A Django-based group trounament betting application.

## Quick Start

```bash
# Start the application
docker compose up --build

# Run migrations
docker compose exec api uv run python divvywonga/manage.py migrate

# Access at http://localhost:8000
```

## Development

### Running Tests

```bash
# Run all tests
docker compose exec api uv run python divvywonga/manage.py test

# Run with coverage report
docker compose exec api uv run pytest --cov=divvywonga --cov-report=term-missing
```

### Test Coverage Report

```bash
# Generate HTML coverage report
docker compose exec api uv run pytest --cov=divvywonga --cov-report=html

# View report in browser (from host)
open htmlcov/index.html
```

### Code Quality

```bash
# Run linter
docker compose exec api uv run ruff check

# Run linter with auto-fix
docker compose exec api uv run ruff check --fix
```

## Project Structure

```
divvywonga/
├── core/           # Main app with index view
├── users/          # User authentication and group management
├── data/           # SQLite database (persisted via Docker volume)
└── manage.py       # Django management script

tests/              # Test suite
├── core/           # Core app tests
├── users/          # Users app tests
└── integration/   # Integration tests
```

## Database

The SQLite database is stored in a Docker volume for persistence. To reset:

```bash
docker compose down -v
docker compose up --build
docker compose exec api uv run python divvywonga/manage.py migrate
```
