# Ness Chatbot

Hybrid RAG + tool-calling chatbot for ness.com, with admin-triggered ingestion and cost-first architecture.

## Architecture

See [architecture.md](architecture.md) for design principles, high-level diagram, request flow, and modularity approach.

Implementation follows [prompt_plan.md](prompt_plan.md) — 13 phases from repo scaffolding through Docker container.

## Setup (Local Development)

### Prerequisites
- Python 3.14 or later
- Docker + Docker Compose (recommended for local dev due to FAISS compilation requirements)
- AWS credentials (for Bedrock + local MinIO/DynamoDB)
- On Windows: C++ build tools if installing FAISS locally (see note below)

### Environment Files

**Two environment templates are provided:**

1. **`.env.example`** — Production setup (use real AWS credentials, real DynamoDB/S3)
   ```bash
   cp .env.example .env
   # Edit with your AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, etc.
   ```

2. **`.env.local.example`** — Local development setup (docker-compose with MinIO/DynamoDB Local)
   ```bash
   cp .env.local.example .env
   # Use dummy MinIO credentials, local Docker endpoints
   ```

**Choose based on your environment:**
- **Local dev**: Use `.env.local.example` with `docker-compose up -d`
- **Production**: Use `.env.example` with real AWS credentials and Terraform deployment

### Note on FAISS Installation
FAISS CPU requires a C++ compiler for local installation on Windows. For development, it's recommended to use **Docker and `docker-compose`** (Phase 13) which eliminates local compilation. If you must install locally on Windows:
1. Install "Microsoft C++ Build Tools" from Visual Studio
2. Then run `pip install -r requirements.txt`

For macOS/Linux, installation typically works without additional tools.

### 1. Clone and Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# OR (Linux/macOS)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

```bash
cp .env.example .env
# Edit .env with your AWS credentials and Bedrock model IDs
```

### 3. Start Local Infrastructure

```bash
# Start DynamoDB Local + MinIO
docker compose up -d

# Create tables + buckets
python scripts/create_local_tables.py
python scripts/create_local_bucket.py
```

### Alternative: Full Docker Development (Recommended for Windows)

Skip the venv setup above and use Docker instead:

```bash
# Build and start all services (API, DynamoDB, MinIO)
docker compose up -d --build

# API will be available at http://localhost:8080
```

### 4. Run the API Locally

```bash
uvicorn api.app:app --reload
```

The API will be available at `http://localhost:8080`.

- POST `/session/start` — get welcome message + quick-action buttons
- POST `/message` — send user message
- GET `/admin/pages` — list all pages for admin
- POST `/admin/refresh` — trigger page discovery
- POST `/admin/embed` — trigger embedding of selected pages

### 5. Run Tests

```bash
# Full unit + integration test suite
python -m pytest tests/ -v

# Skip tests that require local MinIO/DynamoDB (docker compose up -d)
python -m pytest tests/ -v -k "not rag_retriever"
```

## Folder Structure

```
ness-chatbot/
├── config/
│   └── sites/ness.json
├── ingestion/              # Offline batch (scraper, chunker, embedder)
│   ├── scraper.py
│   ├── chunker.py
│   └── embedder.py
├── api/                    # FastAPI orchestration
│   ├── app.py
│   ├── orchestrator.py
│   ├── intent_router.py
│   ├── rag_retriever.py
│   ├── guardrails.py
│   ├── cache.py
│   ├── admin_pages.py
│   ├── config_loader.py
│   ├── llm/
│   │   ├── base_provider.py
│   │   ├── bedrock_provider.py
│   │   └── __init__.py
│   ├── tools/
│   │   ├── get_open_positions.py
│   │   └── get_latest_news.py
│   └── __init__.py
├── widget/                 # React chat UI
│   ├── src/
│   ├── vite.config.ts
│   └── package.json
├── admin/                  # React admin console
│   ├── src/
│   ├── vite.config.ts
│   └── package.json
├── scripts/
│   ├── create_local_tables.py
│   └── create_local_bucket.py
├── tests/                  # Minimal tests
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── .dockerignore
├── .gitignore
├── README.md
├── architecture.md
└── prompt_plan.md
```

## Development Phases

| Phase | Status | Goal |
|-------|--------|------|
| 0 | ✅ Done | Base folder structure, dependencies |
| 1 | ✅ Done | Site config + config loader |
| 2 | ✅ Done | LLM provider abstraction (Bedrock) |
| 3 | ✅ Done | Local AWS infra (docker-compose) |
| 4 | ✅ Done | Ingestion: scraper |
| 5 | ✅ Done | Ingestion: chunker + embedder |
| 6 | ✅ Done | Admin console API |
| 7 | ✅ Done | Guardrails (input/output) |
| 8 | ✅ Done | Intent router |
| 9 | ✅ Done | RAG retriever + tool-calling |
| 10 | ✅ Done | Orchestrator + cache + FastAPI |
| 11 | ✅ Done | Widget (React chat UI) |
| 12 | ✅ Done | Admin console (React UI) |
| 13 | ✅ Done | Dockerfile (single image, two entrypoints) |

## Key Design Decisions

- **Hybrid RAG + tool-calling**: stable info via FAISS index, dynamic data (jobs, news) via live tool calls
- **Cost-first**: canned replies, response caching, cheapest model tier (AWS Bedrock Titan)
- **Admin-triggered ingestion**: no scheduled scraping, "Refresh Pages" and "Embed Selected" buttons only
- **Modular by site config**: swap to any new website via `config/sites/{site_id}.json`, zero core code changes
- **Serverless (future)**: AWS Lambda container image + API Gateway + DynamoDB, ready to scale

## Frontend Build

```bash
# Widget (embeddable chat)
cd widget && npm install && npm run build

# Admin console (page selection + embedding)
cd admin && npm install && npm run build
```

See [prompt_plan.md](prompt_plan.md) for the full phase-by-phase breakdown.

---

**Status**: All 13 phases complete. Implementation verified via `pytest tests/`.
