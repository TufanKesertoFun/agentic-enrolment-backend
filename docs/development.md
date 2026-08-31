# Development

This backend is independently developed and deployed from `agentic-enrolment-backend`.

## Current Scope

Implemented foundations:

- FastAPI application structure
- PostgreSQL configuration with async SQLAlchemy
- Alembic migrations
- core student, enrolment, document, credit mapping, country, institution, user, and role data model
- development JWT authentication
- Argon2 password hashing
- RBAC dependency helpers
- fake development users and roles

Not yet implemented:

- student profile business APIs
- enrolment workflows
- document upload/storage
- credit mapping workflow APIs
- RAG/LLM integration
- chatbot or voice features
- university SSO/OIDC

## Local Auth Setup

Set local-only values before authenticated development runs:

```powershell
JWT_SECRET=<local-development-secret-at-least-32-bytes>
DEMO_USER_PASSWORD=development-password
```

Never commit `.env` or real secrets.