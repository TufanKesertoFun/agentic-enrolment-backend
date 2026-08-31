# API

The backend API is versioned under `/api/v1`. The frontend calls the backend only. The backend decides whether a request is handled with structured PostgreSQL data or delegated to the RAG service after authorization checks.

## Error Shape

Errors use the standard envelope:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": null
  }
}
```

## Authentication

### POST `/api/v1/auth/login`

Authenticates a development user and returns a JWT bearer access token.

Request:

```json
{
  "email": "demo.student@example.invalid",
  "password": "development-password"
}
```

Success response:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 3600
}
```

Failure response for unknown email or bad password:

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid email or password",
    "details": null
  }
}
```

Unknown email and incorrect password intentionally return the same `401` response.

### GET `/api/v1/auth/me`

Returns the current authenticated identity. Requires `Authorization: Bearer <token>`.

Success response:

```json
{
  "id": "<user-id>",
  "email": "demo.student@example.invalid",
  "first_name": "Demo",
  "last_name": "Student",
  "preferred_name": "Demo",
  "roles": ["STUDENT"]
}
```

The response does not include password, password hash, student profile details, documents, or academic records.

## Authorization Errors

Missing, malformed, incorrectly signed, expired, inactive-user, or otherwise invalid tokens return `401`.

Authenticated users who lack the required role return `403 ACCESS_DENIED`.

## Health

- `GET /api/v1/health`
- `GET /api/v1/health/live`
- `GET /api/v1/health/ready`

## OpenAPI

Swagger is available at http://localhost:8000/docs and OpenAPI JSON is available at http://localhost:8000/openapi.json.

Protected endpoints use HTTP Bearer authentication in OpenAPI, so Swagger displays the Authorize button.

## Not Implemented In T004

T004 does not implement student profile APIs, student search, enrolment workflows, document upload, object storage, credit mapping workflow endpoints, AI recommendations, RAG, chatbot, voice, frontend login UI, or university SSO.