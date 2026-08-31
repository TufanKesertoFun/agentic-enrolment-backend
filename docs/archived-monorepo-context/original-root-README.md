# Agentic AI Enrolment & Credit Mapping System

This repository is the foundation for a Python-only, multi-service Agentic AI Enrolment & Credit Mapping System.

The system is organized as three independently deployable applications:

1. Lovable / React Frontend
2. Python FastAPI Backend
3. Python FastAPI RAG Service

The frontend communicates with the backend only. The backend is the business and authorization authority, owns access to structured data and private document storage, and may call the RAG service for AI-assisted workflows. The RAG service provides recommendations and evidence support only; authorized academic staff make final credit mapping decisions.

## Applications

### Frontend

`frontend/` will contain the Lovable-generated React, TypeScript, Vite frontend with Bootstrap or compatible UI components. Chat and voice input are frontend interaction methods and do not require a separate service.

### Backend

`backend/` will contain the Python FastAPI backend using Pydantic, SQLAlchemy, PostgreSQL, Alembic, JWT/OIDC-ready authentication architecture, role-based authorization, and structured logging.

### RAG Service

`rag-service/` will contain the Python FastAPI RAG service using Pydantic, local or Hugging Face-compatible models, embeddings, vector retrieval, RAG, LLM integration, and AI recommendations.

## Future Feature Areas

- Student Portal
- Student Enrolment
- Student Documents
- Lecturer / Officer Workspace
- Student Search
- Credit Mapping
- Historical Mapping
- AI Recommendations
- RAG
- Chatbot
- Voice Input
- Multi-country support

## Current Scope

This is T001 only. It creates the project foundation, documentation, environment examples, and placeholder directories. It does not implement database models, authentication, student APIs, document upload, RAG, LLM, chatbot, voice processing, or credit mapping logic.
