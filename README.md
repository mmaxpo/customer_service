# Tajeran Customer Service

Tajeran is an AI-assisted customer-service platform for Shopify merchants.

## Services

- `backend/` — FastAPI API, Shopify integration, workflows, jobs, and persistence.
- `frontend/` — customer-service workspace and merchant console.
- `MCP Server/` — tool server used by the agentic support runtime.

## Local development

Each service contains its own Docker/Just/Python or Node setup and environment
template. Copy the relevant `.env.example` to a local environment file and
never commit credentials. PostgreSQL and Redis are development dependencies.

## Deployment

The services are kept together so a backend, frontend, and MCP change can be
reviewed and released from one repository. Production secrets must be supplied
by the deployment platform, not stored in Git.
