# Security

The backend is the security authority. Frontend UI state is never trusted for authorization. A hidden button in React is not protection; every sensitive API endpoint must authenticate the caller and authorize the operation server-side.

## Authentication

Authentication answers: who are you?

T004 implements a development JWT authentication provider behind an `AuthenticationProvider` abstraction. The current provider is `DevelopmentJwtAuthenticationProvider`. Future providers can include university SSO, OIDC, Azure/Entra, or another institutional identity provider without forcing business code to depend directly on JWT payload dictionaries.

Access tokens contain only minimal claims:

- `sub`: the backend `users.id`
- `iat`: issued-at timestamp
- `exp`: expiration timestamp
- `jti`: token identifier

Tokens must not contain passwords, password hashes, dates of birth, addresses, documents, academic records, or role authority.

## Password Hashing

Local development users authenticate with passwords only for development. Passwords are hashed with Argon2 through the maintained `pwdlib` package. Only `users.password_hash` is persisted, and it is nullable so future SSO-only users can exist without local passwords.

`DEMO_USER_PASSWORD` must be explicitly configured before running the authenticated development seed. The seed stores only Argon2 hashes and never prints or logs plaintext passwords.

## Authorization

RBAC answers: what class of operation may you perform?

The supported roles are:

- `STUDENT`
- `LECTURER`
- `ENROLMENT_OFFICER`
- `CREDIT_MAPPING_OFFICER`
- `ADMINISTRATOR`

Reusable policy dependencies live in `app.auth.permissions`:

- `require_role(RoleName.ADMINISTRATOR)`
- `require_any_role(RoleName.LECTURER, RoleName.ENROLMENT_OFFICER)`

Endpoint code should use centralized authorization dependencies rather than scattering direct role checks through handlers.

## Trusted Roles

JWT role claims are not authoritative. The authentication dependency validates the token, loads the `User` from PostgreSQL, rejects inactive users, and loads trusted role assignments from PostgreSQL for every authenticated request.

A malicious client cannot add `ADMINISTRATOR` to a frontend request body or forged JWT role claim and become an administrator. Backend persistence is the source of truth.

## Resource Authorization

Resource authorization answers: are you allowed to perform this operation on this specific resource?

A `STUDENT` role does not mean the user can read every student. Future policies should enforce resource-level rules, for example:

- `CanAccessStudentPolicy`
- `CanViewStudentDocumentPolicy`
- `CanReviewCreditMappingPolicy`

Future behavior should allow Student A to access Student A's permitted resources while denying access to Student B's records.

## 401 vs 403

Use `401 Unauthorized` when authentication is missing, invalid, expired, or belongs to an inactive user.

Use `403 Forbidden` when the user is authenticated but lacks the required role or future resource permission.

## Security Logging

Security events use safe event names such as:

- `LOGIN_SUCCESS`
- `LOGIN_FAILURE`
- `AUTH_TOKEN_INVALID`
- `AUTH_TOKEN_EXPIRED`
- `ACCESS_DENIED`

Logs must never include plaintext passwords, password hashes, JWTs, JWT secrets, dates of birth, addresses, document content, or academic record details.

## Remaining Production Hardening

Still required before production:

- login rate limiting
- account lockout or throttling policy
- refresh-token/session design
- secret management outside `.env`
- university SSO/OIDC integration
- persistent audit logs
- resource-level authorization policies
- stronger monitoring and alerting
- HTTPS-only deployment configuration

## File And RAG Safety

Uploaded files are sensitive and must later support MIME validation, malware scanning, access control, secure storage, audit logging, retention, and consent.

RAG treats uploaded documents as untrusted data. Text inside uploaded documents must never override authentication, authorization, tool permissions, or system rules. AI must never make the final academic credit decision.

External profile links such as LinkedIn, portfolio URLs, or approved professional/public profile URLs are references only. The system must not automatically scrape LinkedIn, Instagram, or other social networks. Any future integration must use approved APIs, legal access, and student consent.