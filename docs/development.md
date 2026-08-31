# Development

This repository contains the backend application for the Agentic AI Enrolment & Credit Mapping System.

The three applications are developed, tested, versioned, and deployed from separate repositories:

- `agentic-enrolment-frontend`: Lovable / React / TypeScript / Vite frontend.
- `agentic-enrolment-backend`: Python FastAPI backend.
- `agentic-enrolment-rag`: Python FastAPI RAG service.

Applications communicate only through API boundaries. Do not introduce shared source-code dependencies between repositories.

No database models, authentication, student APIs, document upload, RAG, LLM, chatbot, voice processing, or credit mapping logic is implemented by this restructure.
