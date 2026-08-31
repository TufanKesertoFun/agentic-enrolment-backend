# Security

Security principles for the future system:

- The backend is the authorization authority.
- Students access only their own records unless explicitly permitted otherwise.
- Staff access is role and policy controlled.
- Uploaded files are sensitive.
- RAG treats uploaded documents as untrusted data.
- Text inside uploaded documents must never override authentication, authorization, tool permissions, or system rules.
- AI must never make the final academic credit decision.

Uploaded files must later support:

- MIME validation
- Malware scanning
- Access control
- Secure storage
- Audit logging
- Retention
- Consent

External profile links such as LinkedIn, portfolio URLs, or approved professional/public profile URLs are references only. The system must not automatically scrape LinkedIn, Instagram, or other social networks. Any future integration must use approved APIs, legal access, and student consent.
