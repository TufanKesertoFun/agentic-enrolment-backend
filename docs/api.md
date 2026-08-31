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

Unknown email and incorrect password intentionally return the same `401 INVALID_CREDENTIALS` response.

### GET `/api/v1/auth/me`

Returns the current authenticated identity. Requires `Authorization: Bearer <token>`.

The response does not include password, password hash, student profile details, documents, or academic records.

## Student Self Service

All student endpoints require `Authorization: Bearer <token>` and resolve the student from the authenticated user id through `Student.user_id`. The frontend never sends a trusted `student_id`.

- `GET /api/v1/students/me`
- `GET /api/v1/students/me/profile`
- `PATCH /api/v1/students/me/profile`
- `GET /api/v1/students/me/enrolment-applications`
- `POST /api/v1/students/me/enrolment-applications`
- `GET /api/v1/students/me/enrolment-applications/{application_id}`
- `POST /api/v1/students/me/enrolment-applications/{application_id}/submit`

Profile updates are limited to `StudentProfile` fields: date of birth, phone, address lines, city, state/region, postal code, and country. A missing profile may be created by `PATCH /students/me/profile`.

Creating an enrolment application accepts only `program_id`. The backend sets `student_id` from authentication and creates the application with `DRAFT` status. Submitting an application supports only `DRAFT` to `SUBMITTED` and sets `submitted_at` to the current UTC time. Invalid transitions return `409 CONFLICT`.

## Staff Student Search

`GET /api/v1/institutions/{institution_id}/students/{student_number}` returns a safe student summary for authorized staff roles only:

- `LECTURER`
- `ENROLMENT_OFFICER`
- `CREDIT_MAPPING_OFFICER`
- `ADMINISTRATOR`

`STUDENT` receives `403 ACCESS_DENIED`. The endpoint includes `institution_id` because student numbers are not globally unique.

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

## Not Implemented After T005

T005 does not implement document upload, previous education APIs, qualifications APIs, credit mapping workflow endpoints, staff enrolment decisions, object storage, AI recommendations, RAG, chatbot, voice, frontend login UI, or university SSO.
