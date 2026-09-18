# Ness Chatbot — Prompt Plan (Phase 0 → Docker Image)

Scope: this plan stops once the single Docker image builds and runs locally (API + ingestion CMD override, against local DynamoDB/MinIO). No real AWS deploy, Terraform apply, or CI/CD in this plan — that's a later plan.

**Stack decisions locked in for this plan:**
- Python 3.14, `pip` + `requirements.txt` (no Poetry).
- Local AWS replacement: `dynamodb-local` (official AWS image) + `MinIO` (S3-compatible) via `docker-compose` — no LocalStack.
- Each phase below is a **self-contained prompt** — feed them to the coding agent one at a time, in order. Don't skip ahead; each phase assumes the previous ones are done and reviewed.

---

## Phase 0 — Repo Scaffolding
**Goal:** Base folder structure, dependency file, env template — nothing functional yet.

**Prompt:**
> Create the base folder structure for the Ness chatbot per architecture.md §7: `config/sites/`, `ingestion/`, `api/tools/`, `api/llm/`, `widget/`, `admin/`, `infra/`. Add a `requirements.txt` (Python 3.14) with: `langchain`, `langchain-openai`, `faiss-cpu`, `beautifulsoup4`, `requests`, `boto3`, `python-dotenv`. Add a `.env.example` with placeholders: `OPENAI_API_KEY`, `LLM_PROVIDER` (default `openai`), `AWS_ENDPOINT_URL` (for local DynamoDB/MinIO), `DYNAMODB_TABLE_CANDIDATES`, `S3_BUCKET_INDEX`. Add a minimal `README.md` stub with setup instructions (venv, pip install). Don't write any business logic yet.

**Deliverables:** folder tree, `requirements.txt`, `.env.example`, `README.md`.
**Check:** `pip install -r requirements.txt` succeeds in a fresh venv.

---

## Phase 1 — Site Config
**Goal:** `config/sites/ness.json` per architecture §4, plus a loader.

**Prompt:**
> Create `config/sites/ness.json` exactly as specified in architecture.md §4 (site_id, base_url, sitemap_seeds excluding dynamic pages, dynamic_pages with trigger_keywords, greeting_keywords, branding, welcome_message, quick_actions). Then create `api/config_loader.py` with a `load_site_config(site_id: str) -> dict` function that reads `config/sites/{site_id}.json`, validates required top-level keys are present (raise `ValueError` naming the missing key), and returns the parsed dict.

**Deliverables:** `config/sites/ness.json`, `api/config_loader.py`.
**Check:** `load_site_config("ness")` returns the dict; missing-key case raises `ValueError`.

---

## Phase 2 — LLM Provider Abstraction
**Goal:** `ILLMProvider` interface + OpenAI implementation (Local provider stubbed, not wired yet).

**Prompt:**
> In `api/llm/base_provider.py`, define an abstract `LLMProvider` class (per architecture.md §5) with abstract methods `generate(prompt: str, tools: list | None = None) -> str` and `embed(texts: list[str]) -> list[list[float]]`. In `api/llm/openai_provider.py`, implement `OpenAIProvider(LLMProvider)` using `langchain_openai.ChatOpenAI` (model from env `OPENAI_CHAT_MODEL`, default `gpt-4o-mini`) for `generate`, and `langchain_openai.OpenAIEmbeddings` (model from env `OPENAI_EMBED_MODEL`, default `text-embedding-3-small`) for `embed`. In `api/llm/local_provider.py`, add a `LocalProvider(LLMProvider)` stub that raises `NotImplementedError` for both methods with a clear message (real implementation deferred). In `api/llm/__init__.py`, add a `get_llm_provider() -> LLMProvider` factory reading `LLM_PROVIDER` env var (`openai` default, `local` for the stub).

**Deliverables:** `api/llm/base_provider.py`, `openai_provider.py`, `local_provider.py`, `__init__.py`.
**Check:** `get_llm_provider().embed(["hello"])` returns a vector when `OPENAI_API_KEY` is set; `LLM_PROVIDER=local` raises `NotImplementedError` clearly.

---

## Phase 3 — Local AWS Infra (docker-compose)
**Goal:** `dynamodb-local` + `MinIO` running locally, before writing any code that depends on them.

**Prompt:**
> Create a `docker-compose.yml` at the repo root with two services: `dynamodb-local` (image `amazon/dynamodb-local`, port 8000, in-memory or volume-backed) and `minio` (image `minio/minio`, ports 9000/9001, default root user/pass from `.env`, command `server /data --console-address ":9001"`). Add a `scripts/create_local_tables.py` that uses `boto3` (endpoint pointed at `AWS_ENDPOINT_URL`) to create the `page_candidates` DynamoDB table (partition key `site_id`, sort key `url`) if it doesn't exist, and a `scripts/create_local_bucket.py` that creates the `S3_BUCKET_INDEX` MinIO bucket if it doesn't exist. Update `README.md` with the local infra startup steps.

**Deliverables:** `docker-compose.yml`, `scripts/create_local_tables.py`, `scripts/create_local_bucket.py`.
**Check:** `docker compose up -d`, then both scripts run without error and are idempotent (safe to re-run).

---

## Phase 4 — Ingestion: Scraper (Discover Phase)
**Goal:** `ingestion/scraper.py` — crawls `sitemap_seeds`, writes to `page_candidates`, no embedding.

**Prompt:**
> Create `ingestion/scraper.py` per architecture.md §5c step 1. Function `discover_pages(site_id: str) -> list[dict]`: load site config, for each URL in `sitemap_seeds`, `requests.get()` it (timeout 10s, raise_for_status), parse with BeautifulSoup, extract `<title>` text and visible body text, then upsert a row into the `page_candidates` DynamoDB table (`site_id`, `url`, `title`, `content` (raw extracted text), `last_scraped` (ISO timestamp), `status` — default `"pending"` on first insert, but if the row already exists and `status == "included"`, only update `content`/`last_scraped` and leave `status` untouched; never overwrite `status` from `included`/`excluded` back to `pending`). Return the list of upserted rows. Also filter `sitemap_seeds` against `dynamic_pages` URLs defensively, as noted in architecture.md §4, even though they shouldn't overlap.

**Deliverables:** `ingestion/scraper.py`.
**Check:** running `discover_pages("ness")` against the local DynamoDB populates `page_candidates` with one row per stable page, all `status="pending"` on first run.

---

## Phase 5 — Ingestion: Chunker + Embedder
**Goal:** `ingestion/chunker.py` + `ingestion/embedder.py` — only process `status="included"` pages, write FAISS index to MinIO.

**Prompt:**
> Create `ingestion/chunker.py` with `chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]` (simple sliding-window word/character chunking — no external chunking library needed). Create `ingestion/embedder.py` with `embed_and_index(site_id: str) -> None`: query `page_candidates` for rows where `status == "included"`, chunk each page's `content`, embed all chunks via `get_llm_provider().embed()`, build a LangChain FAISS index (store `url` + `title` as metadata per chunk for citations), serialize the index locally, then upload it to the `S3_BUCKET_INDEX` MinIO bucket at key `{site_id}/index.faiss` (and the accompanying `.pkl` docstore file). Overwrite any existing index for that site_id.

**Deliverables:** `ingestion/chunker.py`, `ingestion/embedder.py`.
**Check:** after marking a couple of `page_candidates` rows as `included` (manually via a boto3 script/console), `embed_and_index("ness")` uploads index files to MinIO and a fresh `FAISS.load_local()` (pointed at a temp download) can similarity-search them.

---

## Phase 6 — Admin Console API
**Goal:** `api/admin_pages.py` — routes backing the "Refresh Pages" / "Embed Selected" buttons and the page checklist.

**Prompt:**
> Create `api/admin_pages.py` with three functions (plain Python callables for now, not yet wired to a web framework — that happens in Phase 10): `list_candidates(site_id: str) -> list[dict]` (returns all `page_candidates` rows for the site), `set_page_status(site_id: str, url: str, status: Literal["included","excluded","pending"]) -> None` (updates the `status` field), `trigger_refresh(site_id: str) -> list[dict]` (calls `discover_pages` from Phase 4), `trigger_embed(site_id: str) -> None` (calls `embed_and_index` from Phase 5). Add basic input validation (reject unknown `site_id`, unknown `status` value) raising `ValueError`.

**Deliverables:** `api/admin_pages.py`.
**Check:** each function callable directly in a Python shell against local infra performs the expected DynamoDB/MinIO operations.

---

## Phase 7 — Guardrails
**Goal:** `api/guardrails.py` — input (prompt-injection/PII) and output (grounding) checks, per §5a.

**Prompt:**
> Create `api/guardrails.py` with: `check_input(message: str) -> tuple[bool, str | None]` — returns `(False, canned_reply)` if the message matches prompt-injection regex patterns (e.g. "ignore previous instructions", "system prompt", "you are now") or PII patterns (email, phone, credit-card-like digit sequences via regex), else `(True, None)`. `check_output_grounded(answer: str, source_chunks: list[str]) -> bool` — a cheap heuristic check (e.g. reject if `source_chunks` is empty, or answer contains no keyword overlap with the source chunks at all) returning `False` if the answer looks ungrounded. Keep both pure regex/heuristic, no LLM calls, per the cost-first principle in §5a.

**Deliverables:** `api/guardrails.py`.
**Check:** unit-testable pure functions — test a few injection strings, a few PII strings, and a grounded vs ungrounded answer pair.

---

## Phase 8 — Intent Router
**Goal:** `api/intent_router.py` — greeting / dynamic / stable classification, per §5.

**Prompt:**
> Create `api/intent_router.py` with `classify(message: str, site_config: dict) -> dict` implementing the 4-step logic in architecture.md §5: (1) check `greeting_keywords` substring match → `{"type": "greeting"}`; (2) check each `dynamic_pages[*].trigger_keywords` → `{"type": "dynamic", "category": <key>}`; (3) default → `{"type": "stable"}`; (4) leave a clearly marked `# TODO Phase 10` comment for the ambiguous-case LLM fallback (wired later once the orchestrator exists, since it needs the LLM provider). Keep steps 1–3 dependency-free (no LLM calls).

**Deliverables:** `api/intent_router.py`.
**Check:** unit test a greeting string, a "careers" string, a "news" string, and a generic "what services do you offer" string each return the right `type`.

---

## Phase 9 — RAG Retriever + Tool-Calling Layer
**Goal:** `api/rag_retriever.py` (FAISS similarity search + confidence threshold) and `api/tools/` (live fetch functions).

**Prompt:**
> Create `api/rag_retriever.py` with `retrieve(site_id: str, query: str, top_k: int = 4, min_score: float = 0.75) -> list[dict] | None`: downloads/loads the site's FAISS index from MinIO (cache in memory across calls within the same process), embeds the query via `get_llm_provider().embed()`, runs similarity search, and returns the top-k chunks (with `url`, `title`, `text`, `score`) only if the best score meets `min_score` — otherwise returns `None` (triggering the canned fallback per §3 step 4). Then create `api/tools/get_open_positions.py` and `api/tools/get_latest_news.py`, each with a single function that reads the relevant `dynamic_pages` entry from site config, does a live `requests` + `BeautifulSoup` fetch using its `selector`, and returns a list of structured dicts (e.g. `{"title": ..., "location": ..., "url": ...}` for jobs).

**Deliverables:** `api/rag_retriever.py`, `api/tools/get_open_positions.py`, `api/tools/get_latest_news.py`.
**Check:** `retrieve("ness", "what services does ness offer")` returns chunks (assuming Phase 5 embedded relevant pages); each tool function returns a non-empty list against the live site (or a clear empty list if selectors don't match — flag for selector verification against real ness.com HTML).

---

## Phase 10 — Orchestrator + Cache + Web Framework
**Goal:** Wire everything into an HTTP API — `api/orchestrator.py`, `api/cache.py`, plus the FastAPI app tying in Phases 6–9.

**Prompt:**
> Create `api/cache.py` with `get_cached(query_hash: str) -> str | None` and `set_cached(query_hash: str, answer: str, ttl_seconds: int = 86400) -> None` backed by a DynamoDB table `response_cache` (partition key `query_hash`, a `ttl` attribute). Create `api/orchestrator.py` implementing the full request flow from architecture.md §3 as a single `handle_message(site_id: str, message: str) -> dict` function: guardrail input check → cache lookup (skip if hit) → intent classification (Phase 8) → route to greeting (canned) / RAG (Phase 9, with the confidence-threshold fallback) / tool-calling (Phase 9) → LLM generation via `get_llm_provider()` → output guardrail check (Phase 7) → cache write → return `{"reply": str, "quick_replies": list[str]}`. Then create `api/app.py` using **FastAPI** exposing: `POST /session/start` (returns welcome_message + quick_actions from site config, no LLM call), `POST /message` (calls `handle_message`), `GET /admin/pages`, `PUT /admin/pages/{url}`, `POST /admin/refresh`, `POST /admin/embed` (wrapping Phase 6 functions, protected by a simple shared-secret header check via env var `ADMIN_API_KEY` — full Cognito auth deferred to the AWS deploy phase).

**Deliverables:** `api/cache.py`, `api/orchestrator.py`, `api/app.py`.
**Check:** `uvicorn api.app:app --reload` runs locally; `POST /session/start`, `POST /message`, and the `/admin/*` routes all respond correctly against local infra.

---

## Phase 11 — Widget (Minimal Standalone Chat UI)
**Goal:** `widget/` — just enough UI to manually exercise the API end-to-end; not the final polished design.

**Prompt:**
> Create a minimal `widget/standalone.html` + `widget/src/ChatWidget.tsx` (plain React, no build tooling complexity — Vite is fine) that: on load, calls `POST /session/start`, renders the welcome message and quick-action buttons; clicking a button or typing free text calls `POST /message` and appends the reply + new quick-replies to the chat log. Keep styling minimal (functional, not final branding) — this is for wiring verification, full UI/UX polish is a later pass.

**Deliverables:** `widget/` React app scaffold.
**Check:** running the widget dev server against the local FastAPI app lets you click through a full conversation.

---

## Phase 12 — Admin Console (Minimal Static Page)
**Goal:** `admin/` — checklist UI for `page_candidates`, calling Phase 10's `/admin/*` routes.

**Prompt:**
> Create a minimal `admin/src/PageSelector.tsx` (same React/Vite setup as the widget) with: a "Refresh Pages" button (`POST /admin/refresh`), a table of `page_candidates` (from `GET /admin/pages`) with a checkbox per row bound to `status` (`included` = checked) that calls `PUT /admin/pages/{url}` on toggle, and an "Embed Selected" button (`POST /admin/embed`). Prompt for the `ADMIN_API_KEY` once (stored in memory/sessionStorage) and send it as a header on every admin request.

**Deliverables:** `admin/` React app scaffold.
**Check:** can refresh, check a few boxes, and trigger embed from the browser against local infra.

---

## Phase 13 — Dockerfile (Single Image, Two Entrypoints)
**Goal:** One Docker image serving both the API (`api/app.py`) and ingestion (callable via `admin_pages.py`, already reachable through the API — no separate ingestion Lambda invocation needed locally). Matches architecture.md §5b.

**Prompt:**
> Create a single `Dockerfile` (Python 3.14-slim base) that: copies `requirements.txt` and installs dependencies, copies the full repo, and sets `CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8080"]` as the default entrypoint (this serves both API and admin/ingestion-trigger routes, since ingestion is invoked through `/admin/refresh` and `/admin/embed`, not a separate process). Add a `.dockerignore` excluding `node_modules`, `.venv`, `__pycache__`, `.env`. Update `docker-compose.yml` to add an `app` service building from this Dockerfile, depending on `dynamodb-local` and `minio`, with env vars pointed at their container hostnames.

**Deliverables:** `Dockerfile`, `.dockerignore`, updated `docker-compose.yml`.
**Check:** `docker compose up --build` — the `app` container starts, and `POST /session/start` succeeds against it from the host machine.

---

## Stopping Point
At the end of Phase 13 you have: a working FastAPI app + admin console + widget, all running in Docker against local DynamoDB/MinIO, with the full hybrid RAG + tool-calling flow functional end-to-end locally. **Not yet covered** (separate future plan): Terraform for real AWS (Lambda container deploy, real DynamoDB/S3, API Gateway usage plans, Cognito), CI/CD (GitHub Actions), and production auth for the admin console.
