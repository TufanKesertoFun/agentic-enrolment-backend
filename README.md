# Backend

Python FastAPI backend foundation for the Agentic AI Enrolment & Credit Mapping System.

This backend is independently deployable and remains the business and authorization authority for student records, enrolment workflows, document access, credit mapping decisions, staff workflows, audit, and RAG orchestration.

## Technology

- Python 3.12
- FastAPI
- Pydantic v2
- pydantic-settings
- SQLAlchemy 2.x
- PostgreSQL with asyncpg
- Alembic
- JWT bearer authentication for development
- Argon2 password hashing through `pwdlib`
- pytest and pytest-asyncio
- httpx
- Ruff
- mypy where practical

## Architecture

- `app/api/`: FastAPI routers and endpoint modules. Routes stay thin and delegate business behavior to application services in later tasks.
- `app/auth/`: authentication provider abstraction, JWT provider, password hashing, authenticated user context, FastAPI auth dependencies, and RBAC policy helpers.
- `app/application/`: use cases, handlers, and lightweight CQRS-style command/query conventions.
- `app/domain/`: domain entities, aggregate roots, and domain exceptions.
- `app/infrastructure/`: database sessions, persistence implementation, storage, and provider-specific infrastructure.
- `app/repositories/`: lightweight repository interface conventions. Future repositories should be purpose-specific.
- `app/country_strategies/`: future Strategy Pattern implementations for academic credit differences between countries and frameworks.
- `app/integrations/`: future Adapter Pattern implementations for external university and student management systems.

The API is versioned under `/api/v1`. The backend may call the RAG service in future tasks, but the frontend must not bypass backend authorization for privileged student data.

## Run Locally

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Create a local `.env` from `.env.example` and set explicit development-only values:

```powershell
JWT_SECRET=<local-development-secret-at-least-32-bytes>
DEMO_USER_PASSWORD=development-password
```

Do not commit `.env` or real secrets.

Apply migrations and seed development data:

```powershell
python -m alembic upgrade head
python -m app.infrastructure.database.seed
```

Run the API:

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

## API Documentation

- Swagger: http://localhost:8000/docs
- OpenAPI: http://localhost:8000/openapi.json

Swagger shows Bearer authentication for protected endpoints. Use `POST /api/v1/auth/login` to obtain a development access token, then click Authorize and paste the token.

## Authentication Endpoints

### POST `/api/v1/auth/login`

Request:

```json
{
  "email": "demo.student@example.invalid",
  "password": "development-password"
}
```

Response:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 3600
}
```

Unknown email and invalid password return the same generic `401 INVALID_CREDENTIALS` response.

### GET `/api/v1/auth/me`

Requires `Authorization: Bearer <token>`. Returns only the current identity and trusted PostgreSQL roles. It never returns passwords or password hashes.

## Development Users

The development seed creates these fake users when `DEMO_USER_PASSWORD` is configured:

- `demo.student@example.invalid` -> `STUDENT`
- `demo.lecturer@example.invalid` -> `LECTURER`
- `demo.enrolment@example.invalid` -> `ENROLMENT_OFFICER`
- `demo.credit@example.invalid` -> `CREDIT_MAPPING_OFFICER`
- `demo.admin@example.invalid` -> `ADMINISTRATOR`

The existing fake student number remains `11111`.

## Health Endpoints

- `GET /api/v1/health`
- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`

The readiness endpoint checks PostgreSQL connectivity and returns an HTTP failure response when the database is unavailable.

## Tests

```powershell
python -m pytest
```

Run PostgreSQL-gated tests:

```powershell
$env:RUN_POSTGRES_TESTS='1'
python -m pytest
```

## Lint And Type Check

```powershell
python -m ruff check .
python -m mypy app tests migrations
```

## Database Development Commands

Create migration:

```powershell
python -m alembic revision --autogenerate -m "description"
```

Apply migration:

```powershell
python -m alembic upgrade head
```

Rollback:

```powershell
python -m alembic downgrade -1
```

The T003 core domain schema is created by migration `20260831_0002_core_domain_schema.py`.
The T004 authentication schema change is created by migration `20260901_0003_add_user_password_hash.py`.

## Security Limits Still Remaining

This is a development authentication foundation. Production hardening still needs rate limiting, refresh-token/session strategy, SSO/OIDC integration, audit event persistence, account lockout policy, secret management, stronger operational monitoring, and resource-level authorization policies.