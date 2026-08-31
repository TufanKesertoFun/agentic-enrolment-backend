# Backend

Python FastAPI backend foundation for the Agentic AI Enrolment & Credit Mapping System.

This backend is independently deployable and will remain the business and authorization authority for student records, enrolment workflows, document access, credit mapping decisions, staff workflows, audit, and RAG orchestration.

## Technology

- Python 3.12
- FastAPI
- Pydantic v2
- pydantic-settings
- SQLAlchemy 2.x
- PostgreSQL with asyncpg
- Alembic
- pytest and pytest-asyncio
- httpx
- Ruff
- mypy where practical

## Architecture

- `app/api/`: FastAPI routers and endpoint modules. Routes stay thin and delegate business behavior to application services in later tasks.
- `app/application/`: use cases, handlers, and lightweight CQRS-style command/query conventions.
- `app/domain/`: domain entities, aggregate roots, and domain exceptions.
- `app/infrastructure/`: database sessions, persistence implementation, storage, and provider-specific infrastructure.
- `app/repositories/`: lightweight repository interface conventions. Future repositories should be purpose-specific.
- `app/country_strategies/`: future Strategy Pattern implementations for academic credit differences between countries and frameworks.
- `app/integrations/`: future Adapter Pattern implementations for external university and student management systems.

The API is versioned under `/api/v1`. The backend may call the RAG service in future tasks, but the frontend must not bypass backend authorization for privileged student data.

## Run Locally

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run the API:

```powershell
uvicorn app.main:app --reload --port 8000
```

## API Documentation

- Swagger: http://localhost:8000/docs
- OpenAPI: http://localhost:8000/openapi.json

## Health Endpoints

- `GET /api/v1/health`
- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`

The readiness endpoint checks PostgreSQL connectivity and returns an HTTP failure response when the database is unavailable.

## Tests

```powershell
pytest
```

## Lint

```powershell
ruff check .
```

## Database Development Commands

Create migration:

```powershell
alembic revision --autogenerate -m "description"
```

Apply migration:

```powershell
alembic upgrade head
```

Rollback:

```powershell
alembic downgrade -1
```

The T003 core domain schema is created by migration `20260831_0002_core_domain_schema.py`.

## Development Seed Data

Preview seed data without connecting to PostgreSQL:

```powershell
python -m app.infrastructure.database.seed --dry-run
```

Seed configured PostgreSQL after applying migrations:

```powershell
python -m app.infrastructure.database.seed
```

The development seed contains reference countries, roles, a clearly fake demo student with student number `11111`, and mock historical credit mappings only.

